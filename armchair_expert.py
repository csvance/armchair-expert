import signal
from enum import Enum, unique
from multiprocessing import Event
import sys

from capitalization_model import CapitalizationModelScheduler
from frontend_twitter import TwitterFrontend, TwitterReplyGenerator
from markov_engine import MarkovTrieDb
from ml_config import *
from nlp_common import create_nlp_instance
from pos_tree_model import PosTreeModel
from twitter_config import TWITTER_CREDENTIALS


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
        self._capitalization_model = None
        self._postree_model = None
        self._nlp = None
        self._status = None
        self._frontends = []
        self._frontends_event = Event()

    def _set_status(self, status: AEStatus):
        self._status = status
        print("armchair-expert status: %s" % str(self._status).split(".")[1])

    def start(self):
        self._set_status(AEStatus.STARTING_UP)

        # Initialize backends and models
        self._markov_model = MarkovTrieDb()
        self._markov_model.load(MARKOV_DB_PATH)

        self._postree_model = PosTreeModel()
        self._postree_model.load(POSTREE_DB_PATH)

        self._capitalization_model = CapitalizationModelScheduler(use_gpu=USE_GPU)
        self._capitalization_model.load(CAPITALIZATION_MODEL_PATH)
        self._capitalization_model.start()

        # Initialize frontends
        self._twitter_frontend = None
        try:
            import twitter_config
            twitter_reply_generator = TwitterReplyGenerator(markov_model=self._markov_model,
                                                            postree_model=self._postree_model,
                                                            capitalization_model=self._capitalization_model)
            self._twitter_frontend = TwitterFrontend(reply_generator=twitter_reply_generator,
                                                     frontend_events=self._frontends_event, credentials=TWITTER_CREDENTIALS)
            self._twitter_frontend.start()
            self._frontends.append(self._twitter_frontend)
        except ModuleNotFoundError:
            pass

        # Non forking initializations
        self._nlp = create_nlp_instance()

        for frontend in self._frontends:
            frontend.give_nlp(self._nlp)

        # Handle events
        self._main()

    def _main(self):
        self._set_status(AEStatus.RUNNING)
        while True:
            if self._frontends_event.wait(timeout=0.2):
                self._frontends_event.clear()

                for frontend in self._frontends:
                    message = frontend.recv()
                    if message is not None:
                        reply = frontend.generate(message)
                        frontend.send(reply)
                    else:
                        frontend.send(None)

            if self._status == AEStatus.SHUTTING_DOWN:
                self.shutdown()
                self._set_status(AEStatus.SHUTDOWN)
                sys.exit(0)

    def shutdown(self):

        # Shutdown frontends
        for frontend in self._frontends:
            frontend.shutdown()

        # Save Models
        # self._markov_model.save(MARKOV_DB_PATH)
        # self._postree_model.save(POSTREE_DB_PATH)
        # self._capitalization_model.save(CAPITALIZATION_MODEL_PATH)

        # Shutdown Models
        self._capitalization_model.shutdown()


    def handle_shutdown(self):
        # Shutdown main()
        self._set_status(AEStatus.SHUTTING_DOWN)


def signal_handler(sig, frame):
    if sig == signal.SIGINT:
        ae.handle_shutdown()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)

    ae = ArmchairExpert()
    ae.start()
