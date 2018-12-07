import argparse
import logging
import signal
import sys
from enum import Enum, unique
from multiprocessing import Event

from common.nlp import create_nlp_instance, SpacyPreprocessor
from config.armchair_expert import ARMCHAIR_EXPERT_LOGLEVEL
from config.ml import USE_GPU, STRUCTURE_MODEL_PATH, MARKOV_DB_PATH, STRUCTURE_MODEL_TRAINING_MAX_SIZE
from markov_engine import MarkovTrieDb, MarkovTrainer, MarkovFilters
from models.structure import StructureModelScheduler, StructurePreprocessor
from storage.armchair_expert import InputTextStatManager
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

    def start(self, retrain_structure: bool = False, retrain_markov: bool = False):

        self._set_status(AEStatus.STARTING_UP)

        # Initialize backends and models
        self._markov_model = MarkovTrieDb()
        if not retrain_markov:
            try:
                self._markov_model.load(MARKOV_DB_PATH)
            except FileNotFoundError:
                retrain_markov = True

        self._structure_scheduler = StructureModelScheduler(USE_GPU)
        self._structure_scheduler.start()
        structure_model_trained = None
        if not retrain_structure is None:
            try:
                open(STRUCTURE_MODEL_PATH, 'rb')
                self._structure_scheduler.load(STRUCTURE_MODEL_PATH)
                structure_model_trained = True
            except FileNotFoundError:
                structure_model_trained = False

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
        if retrain_structure or not structure_model_trained:
            self.train(retrain_structure=True, retrain_markov=retrain_markov)
        else:
            self.train(retrain_structure=False, retrain_markov=retrain_markov)

        # Give the connectors the NLP object and start them
        for connector in self._connectors:
            connector.give_nlp(self._nlp)
            connector.start()
            connector.unmute()

        # Handle events
        self._main()

    def _preprocess_structure_data(self):
        structure_preprocessor = StructurePreprocessor()

        self._logger.info("Training_Preprocessing_Structure(Import)")
        imported_messages = ImportTrainingDataManager().all_training_data(limit=STRUCTURE_MODEL_TRAINING_MAX_SIZE,
                                                                          order_by='id', order='desc')
        for message_idx, message in enumerate(imported_messages):
            # Print Progress
            if message_idx % 100 == 0:
                self._logger.info(
                    "Training_Preprocessing_Structure(Import): %f%%" % (
                            message_idx / min(STRUCTURE_MODEL_TRAINING_MAX_SIZE, len(imported_messages)) * 100))

            doc = self._nlp(MarkovFilters.filter_input(message[0].decode()))
            if not structure_preprocessor.preprocess(doc):
                return structure_preprocessor

        tweets = None
        if self._twitter_connector is not None:
            self._logger.info("Training_Preprocessing_Structure(Twitter)")
            from storage.twitter import TwitterTrainingDataManager

            tweets = TwitterTrainingDataManager().all_training_data(limit=STRUCTURE_MODEL_TRAINING_MAX_SIZE,
                                                                    order_by='timestamp', order='desc')
            for tweet_idx, tweet in enumerate(tweets):
                # Print Progress
                if tweet_idx % 100 == 0:
                    self._logger.info(
                        "Training_Preprocessing_Structure(Twitter): %f%%" % (
                                tweet_idx / min(STRUCTURE_MODEL_TRAINING_MAX_SIZE, len(tweets)) * 100))

                doc = self._nlp(MarkovFilters.filter_input(tweet[0].decode()))
                if not structure_preprocessor.preprocess(doc):
                    return structure_preprocessor

        discord_messages = None
        if self._discord_connector is not None:
            self._logger.info("Training_Preprocessing_Structure(Discord)")
            from storage.discord import DiscordTrainingDataManager

            discord_messages = DiscordTrainingDataManager().all_training_data(limit=STRUCTURE_MODEL_TRAINING_MAX_SIZE,
                                                                              order_by='timestamp', order='desc')
            for message_idx, message in enumerate(discord_messages):
                # Print Progress
                if message_idx % 100 == 0:
                    self._logger.info(
                        "Training_Preprocessing_Structure(Discord): %f%%" % (
                                message_idx / min(STRUCTURE_MODEL_TRAINING_MAX_SIZE, len(discord_messages)) * 100))

                doc = self._nlp(MarkovFilters.filter_input(message[0].decode()))
                if not structure_preprocessor.preprocess(doc):
                    return structure_preprocessor

        return structure_preprocessor

    def _preprocess_markov_data(self, all_training_data: bool = False):
        spacy_preprocessor = SpacyPreprocessor()

        self._logger.info("Training_Preprocessing_Markov(Import)")
        if not all_training_data:
            imported_messages = ImportTrainingDataManager().new_training_data()
        else:
            imported_messages = ImportTrainingDataManager().all_training_data()
        for message_idx, message in enumerate(imported_messages):
            # Print Progress
            if message_idx % 100 == 0:
                self._logger.info(
                    "Training_Preprocessing_Markov(Import): %f%%" % (message_idx / len(imported_messages) * 100))

            doc = self._nlp(MarkovFilters.filter_input(message[0].decode()))
            spacy_preprocessor.preprocess(doc)

        tweets = None
        if self._twitter_connector is not None:
            self._logger.info("Training_Preprocessing_Markov(Twitter)")
            from storage.twitter import TwitterTrainingDataManager

            if not all_training_data:
                tweets = TwitterTrainingDataManager().new_training_data()
            else:
                tweets = TwitterTrainingDataManager().all_training_data()
            for tweet_idx, tweet in enumerate(tweets):
                # Print Progress
                if tweet_idx % 100 == 0:
                    self._logger.info("Training_Preprocessing_Markov(Twitter): %f%%" % (tweet_idx / len(tweets) * 100))

                doc = self._nlp(MarkovFilters.filter_input(tweet[0].decode()))
                spacy_preprocessor.preprocess(doc)

        discord_messages = None
        if self._discord_connector is not None:
            self._logger.info("Training_Preprocessing_Markov(Discord)")
            from storage.discord import DiscordTrainingDataManager

            if not all_training_data:
                discord_messages = DiscordTrainingDataManager().new_training_data()
            else:
                discord_messages = DiscordTrainingDataManager().all_training_data()

            for message_idx, message in enumerate(discord_messages):
                # Print Progress
                if message_idx % 100 == 0:
                    self._logger.info(
                        "Training_Preprocessing_Markov(Discord): %f%%" % (message_idx / len(discord_messages) * 100))

                doc = self._nlp(MarkovFilters.filter_input(message[0].decode()))
                spacy_preprocessor.preprocess(doc)

        return spacy_preprocessor

    def _train_markov(self, retrain: bool = False):

        spacy_preprocessor = self._preprocess_markov_data(all_training_data=retrain)

        self._logger.info("Training(Markov)")
        input_text_stats_manager = InputTextStatManager()
        if retrain:
            # Reset stats if we are retraining
            input_text_stats_manager.reset()

        markov_trainer = MarkovTrainer(self._markov_model)
        docs, _ = spacy_preprocessor.get_preprocessed_data()
        for doc_idx, doc in enumerate(docs):
            # Print Progress
            if doc_idx % 100 == 0:
                self._logger.info("Training(Markov): %f%%" % (doc_idx / len(docs) * 100))

            markov_trainer.learn(doc)

            sents = 0
            for sent in doc.sents:
                sents += 1
            input_text_stats_manager.log_length(length=sents)

        if len(docs) > 0:
            self._markov_model.save(MARKOV_DB_PATH)
            input_text_stats_manager.commit()

    def _train_structure(self, retrain: bool = False):

        if not retrain:
            return

        structure_preprocessor = self._preprocess_structure_data()

        self._logger.info("Training(Structure)")
        structure_data, structure_labels = structure_preprocessor.get_preprocessed_data()
        if len(structure_data) > 0:

            # This works well enough!
            epochs = 60 - int(len(structure_data) / (125000/27))

            # Floor / Ceilling for training
            epochs = max(5, epochs)
            epochs = min(60, epochs)

            self._structure_scheduler.train(structure_data, structure_labels, epochs=epochs)
            self._structure_scheduler.save(STRUCTURE_MODEL_PATH)

    def train(self, retrain_structure: bool = False, retrain_markov: bool = False):

        self._logger.info("Training begin")
        self._train_markov(retrain_markov)
        self._train_structure(retrain_structure)

        # Mark data as trained
        if self._twitter_connector is not None:
            from storage.twitter import TwitterTrainingDataManager
            TwitterTrainingDataManager().mark_trained()
        if self._discord_connector is not None:
            from storage.discord import DiscordTrainingDataManager
            DiscordTrainingDataManager().mark_trained()
        ImportTrainingDataManager().mark_trained()

        self._logger.info("Training end")

    def _main(self):
        self._set_status(AEStatus.RUNNING)

        while True:
            if self._connectors_event.wait(timeout=1):
                self._connectors_event.clear()

            for connector in self._connectors:
                while not connector.empty():
                    message = connector.recv()
                    if message is not None:
                        doc = self._nlp(MarkovFilters.filter_input(message.text))
                        if message.learn:
                            MarkovTrainer(self._markov_model).learn(doc)
                            connector.send(None)
                        if message.reply:
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

    parser = argparse.ArgumentParser()
    parser.add_argument('--retrain-markov', help='Retrain the markov word engine with all training data',
                        action='store_true')
    parser.add_argument('--retrain-structure', help='Retrain the structure RNN with all available training data',
                        action='store_true')
    args = parser.parse_args()

    ae = ArmchairExpert()
    ae.start(retrain_structure=args.retrain_structure, retrain_markov=args.retrain_markov)
