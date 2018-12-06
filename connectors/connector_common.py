from markov_engine import MarkovTrieDb, MarkovFilters, MarkovGenerator
from models.structure import StructureModelScheduler
from common.nlp import CapitalizationMode
from typing import Optional, List
from multiprocessing import Process, Queue, Event
from threading import Thread
from queue import Empty
from spacy.tokens import Doc
from storage.armchair_expert import InputTextStatManager
import numpy as np


class ConnectorRecvMessage(object):
    def __init__(self, text: str, learn: bool=False, reply=True):
        self.text = text
        self.learn = learn
        self.reply = reply


class ConnectorReplyGenerator(object):
    def __init__(self, markov_model: MarkovTrieDb,
                 structure_scheduler: StructureModelScheduler):
        self._markov_model = markov_model
        self._structure_scheduler = structure_scheduler
        self._nlp = None

    def give_nlp(self, nlp):
        self._nlp = nlp

    def generate(self, message: str, doc: Doc = None, ignore_topics: List[str] = []) -> Optional[str]:

        if doc is None:
            filtered_message = MarkovFilters.filter_input(message)
            doc = self._nlp(filtered_message)

        subjects = []
        for token in doc:
            if(token.text in ignore_topics):
                continue
            markov_word = self._markov_model.select(token.text)
            if markov_word is not None:
                subjects.append(markov_word)
        if len(subjects) == 0:
            return "I wasn't trained on that!"

        def structure_generator():
            sentence_stats_manager = InputTextStatManager()
            while True:
                choices, p_values = sentence_stats_manager.probabilities()
                if len(choices) > 0:
                    num_sentences = np.random.choice(choices, p=p_values)
                else:
                    num_sentences = np.random.randint(1, 5)
                yield self._structure_scheduler.predict(num_sentences=num_sentences)

        generator = MarkovGenerator(structure_generator=structure_generator(), subjects=subjects)

        reply_words = []
        sentences = generator.generate(db=self._markov_model)
        if sentences is None:
            return "Huh?"
        for sentence in sentences:
            for word_idx, word in enumerate(sentence):
                if not word.compound:
                    text = CapitalizationMode.transform(word.mode, word.text)
                else:
                    text = word.text
                reply_words.append(text)

        reply = " ".join(reply_words)
        filtered_reply = MarkovFilters.smooth_output(reply)

        return filtered_reply


class ConnectorWorker(Process):
    def __init__(self, name, read_queue: Queue, write_queue: Queue, shutdown_event: Event):
        Process.__init__(self, name=name)
        self._read_queue = read_queue
        self._write_queue = write_queue
        self._shutdown_event = shutdown_event
        self._frontend = None

    def send(self, message: ConnectorRecvMessage):
        return self._write_queue.put(message)

    def recv(self) -> Optional[str]:
        return self._read_queue.get()

    def run(self):
        pass


class ConnectorScheduler(object):
    def __init__(self, shutdown_event: Event):
        self._read_queue = Queue()
        self._write_queue = Queue()
        self._shutdown_event = shutdown_event
        self._worker = None

    def recv(self, timeout: Optional[float]) -> Optional[ConnectorRecvMessage]:
        try:
            return self._read_queue.get(timeout=timeout)
        except Empty:
            return None

    def send(self, message: str):
        self._write_queue.put(message)

    def start(self):
        self._worker.start()

    def shutdown(self):
        self._worker.join()


class Connector(object):
    def __init__(self, reply_generator: ConnectorReplyGenerator, connectors_event: Event):
        self._reply_generator = reply_generator
        self._scheduler = None
        self._thread = Thread(target=self.run)
        self._write_queue = Queue()
        self._read_queue = Queue()
        self._frontends_event = connectors_event
        self._shutdown_event = Event()
        self._muted = True

    def give_nlp(self, nlp):
        self._reply_generator.give_nlp(nlp)

    def start(self):
        self._scheduler.start()
        self._thread.start()

    def run(self):
        while not self._shutdown_event.is_set():
            message = self._scheduler.recv(timeout=0.2)
            if self._muted:
                self._scheduler.send(None)
            elif message is not None:
                # Receive the message and put it in a queue
                self._read_queue.put(message)
                # Notify main program to wakeup and check for messages
                self._frontends_event.set()
                # Send the reply
                reply = self._write_queue.get()
                self._scheduler.send(reply)

    def send(self, message: str):
        self._write_queue.put(message)

    def recv(self) -> Optional[ConnectorRecvMessage]:
        if not self._read_queue.empty():
            return self._read_queue.get()
        return None

    def shutdown(self):
        # Shutdown event signals both our thread and process to shutdown
        self._shutdown_event.set()
        self._scheduler.shutdown()
        self._thread.join()

    def generate(self, message: str, doc: Doc=None) -> str:
        return self._reply_generator.generate(message, doc)

    def mute(self):
        self._muted = True

    def unmute(self):
        self._muted = False

    def empty(self):
        return self._read_queue.empty()
