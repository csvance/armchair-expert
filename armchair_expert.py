import signal
import sys
from enum import Enum, unique
from multiprocessing import Event
import logging

from storage.discord import DiscordTrainingDataManager
from common.nlp import create_nlp_instance, SpacyPreprocessor
from config.ml import *
from config.armchair_expert import ARMCHAIR_EXPERT_LOGLEVEL
from markov_engine import MarkovTrieDb, MarkovTrainer, MarkovFilters
from models.structure import StructureModelScheduler, StructurePreprocessor
from storage.twitter import TwitterTrainingDataManager
from storage.imported import ImportTrainingDataManager


@unique
class AEStatus(Enum):
    STARTING_UP = 1
    RUNNING = 2
    SHUTTING_DOWN = 3
    SHUTDOWN = 4


class ArmchairExpert(object):
    def __init__(self):
        # Placeholders
        self._markov_model = None
        self._nlp = None
        self._status = None
        self._structure_scheduler = None
        self._connectors = []
        self._connectors_event = Event()
        self._twitter_connector = None
        self._discord_connector = None
        self._logger = logging.getLogger(self.__class__.__name__)

    def _set_status(self, status: AEStatus):
        self._status = status
        self._logger.info("Status: %s" % str(self._status).split(".")[1])

    def start(self):

        self._set_status(AEStatus.STARTING_UP)

        # Initialize backends and models
        self._markov_model = MarkovTrieDb()
        try:
            self._markov_model.load(MARKOV_DB_PATH)
        except FileNotFoundError:
            pass

        self._structure_scheduler = StructureModelScheduler(USE_GPU)
        self._structure_scheduler.start()
        try:
            open(STRUCTURE_MODEL_PATH, 'rb')
            self._structure_scheduler.load(STRUCTURE_MODEL_PATH)
        except FileNotFoundError:
            pass

        # Initialize connectors
        try:
            from config.twitter import TWITTER_CREDENTIALS
            from connectors.twitter import TwitterFrontend, TwitterReplyGenerator
            twitter_reply_generator = TwitterReplyGenerator(markov_model=self._markov_model,
                                                            structure_scheduler=self._structure_scheduler)
            self._twitter_connector = TwitterFrontend(reply_generator=twitter_reply_generator,
                                                      connectors_event=self._connectors_event,
                                                      credentials=TWITTER_CREDENTIALS)
            self._connectors.append(self._twitter_connector)
            self._logger.info("Loaded Twitter Connector.")
        except ImportError:
            pass

        try:
            from config.discord import DISCORD_CREDENTIALS
            from connectors.discord import DiscordFrontend, DiscordReplyGenerator
            discord_reply_generator = DiscordReplyGenerator(markov_model=self._markov_model,
                                                            structure_scheduler=self._structure_scheduler)
            self._discord_connector = DiscordFrontend(reply_generator=discord_reply_generator,
                                                      connectors_event=self._connectors_event,
                                                      credentials=DISCORD_CREDENTIALS)
            self._connectors.append(self._discord_connector)
            self._logger.info("Loaded Discord Connector.")
        except ImportError:
            pass

        # Non forking initializations
        self._logger.info("Loading spaCy model")
        self._nlp = create_nlp_instance()

        # Catch up on training now that everything is initialized but not yet started
        self.train()

        # Give the connectors the NLP object and start them
        for connector in self._connectors:
            connector.give_nlp(self._nlp)
            connector.start()
            connector.unmute()

        # Handle events
        self._main()

    def train(self):

        self._logger.info("Training new data.")
        structure_preprocessor = StructurePreprocessor()
        spacy_preprocessor = SpacyPreprocessor()

        self._logger.info("Training_Preprocessing(Import)")
        imported_messages = ImportTrainingDataManager().new_training_data()
        for message_idx, message in enumerate(imported_messages):
            # Print Progress
            if message_idx % 100 == 0:
                self._logger.info("Training_Preprocessing(Import): %f%%" % (message_idx / len(imported_messages) * 100))

            doc = self._nlp(message[0].decode())
            structure_preprocessor.preprocess(doc)
            spacy_preprocessor.preprocess(doc)

        tweets = None
        if self._twitter_connector is not None:
            self._logger.info("Training_Preprocessing(Twitter)")
            tweets = TwitterTrainingDataManager().new_training_data()
            for tweet_idx, tweet in enumerate(tweets):
                # Print Progress
                if tweet_idx % 100 == 0:
                    self._logger.info("Training Preprocessing(Twitter): %f%%" % (tweet_idx / len(tweets) * 100))

                doc = self._nlp(tweet[0].decode())
                structure_preprocessor.preprocess(doc)
                spacy_preprocessor.preprocess(doc)

        discord_messages = None
        if self._discord_connector is not None:
            self._logger.info("Training_Preprocessing(Discord)")
            discord_messages = DiscordTrainingDataManager().new_training_data()
            for message_idx, message in enumerate(discord_messages):
                # Print Progress
                if message_idx % 100 == 0:
                    self._logger.info(
                        "Training_Preprocessing(Discord): %f%%" % (message_idx / len(discord_messages) * 100))

                doc = self._nlp(message[0].decode())
                structure_preprocessor.preprocess(doc)
                spacy_preprocessor.preprocess(doc)

        self._logger.info("Training(Markov)")
        markov_trainer = MarkovTrainer(self._markov_model)
        docs = spacy_preprocessor.get_preprocessed_data()
        for doc_idx, doc in enumerate(docs):
            # Print Progress
            if doc_idx % 100 == 0:
                self._logger.info("Training(Markov): %f%%" % (doc_idx / len(docs) * 100))

            markov_trainer.learn(doc)
        if len(docs) > 0:
            self._markov_model.save(MARKOV_DB_PATH)

        self._logger.info("Training(Structure)")
        structure_data, structure_labels = structure_preprocessor.get_preprocessed_data()
        if len(structure_data) > 0:
            epochs = min(int(len(structure_data) * (10 / 30000)), 1)
            self._logger.info("Training(Structure): %d epochs" % epochs)

            self._structure_scheduler.train(structure_data, structure_labels, epochs=epochs)
            self._structure_scheduler.save(STRUCTURE_MODEL_PATH)

        if tweets is not None:
            TwitterTrainingDataManager().mark_trained()
        if discord_messages is not None:
            DiscordTrainingDataManager().mark_trained()
        if len(imported_messages) > 0:
            ImportTrainingDataManager().mark_trained()

        self._logger.info("Training done.")

    def _main(self):
        self._set_status(AEStatus.RUNNING)

        while True:
            if self._connectors_event.wait(timeout=1):
                self._connectors_event.clear()

            for connector in self._connectors:
                while not connector.empty():
                    message = connector.recv()
                    if message is not None:
                        # Reply
                        doc = self._nlp(MarkovFilters.filter_input(message))
                        reply = connector.generate(message, doc=doc)
                        connector.send(reply)
                    else:
                        connector.send(None)

            if self._status == AEStatus.SHUTTING_DOWN:
                self.shutdown()
                self._set_status(AEStatus.SHUTDOWN)
                sys.exit(0)

    def shutdown(self):

        # Shutdown connectors
        for connector in self._connectors:
            connector.shutdown()

        # Shutdown models
        self._structure_scheduler.shutdown()

    def handle_shutdown(self):
        # Shutdown main()
        self._set_status(AEStatus.SHUTTING_DOWN)


def signal_handler(sig, frame):
    if sig == signal.SIGINT:
        ae.handle_shutdown()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    logging.basicConfig(level=ARMCHAIR_EXPERT_LOGLEVEL)

    ae = ArmchairExpert()
    ae.start()
