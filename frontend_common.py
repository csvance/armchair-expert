from markov_engine import MarkovTrieDb, MarkovFilters, MarkovGenerator
from pos_tree_model import PosTreeModel
from capitalization_model import CapitalizationModelScheduler, CapitalizationMode
from typing import Optional
from multiprocessing import Process, Queue, Event
from threading import Thread


class FrontendReplyGenerator(object):
    def __init__(self, markov_model: MarkovTrieDb, postree_model: PosTreeModel,
                 capitalization_model: CapitalizationModelScheduler, nlp):
        self._markov_model = markov_model
        self._postree_model = postree_model
        self._capitalization_model = capitalization_model
        self._nlp = nlp

    def generate(self, message: str) -> Optional[str]:

        filtered_message = MarkovFilters.filter_input(message)
        doc = self._nlp(filtered_message)
        subjects = []
        for token in doc:
            markov_word = self._markov_model.select(token.text)
            if markov_word is not None:
                subjects.append(markov_word)
        if len(subjects) == 0:
            return None
        structure = self._postree_model.generate_sentence()
        generator = MarkovGenerator(structure=structure, subjects=subjects)

        reply_words = []
        sentences = generator.generate(db=self._markov_model)
        for sentence in sentences:
            for word_idx, word in enumerate(sentence):
                mode = self._capitalization_model.predict(word.text, word.pos, word_idx)
                text = CapitalizationMode.transform(mode, word.text, ignore_prefix_regexp=r'[#@]')
                reply_words.append(text)

        reply = " ".join(reply_words)
        filtered_reply = MarkovFilters.smooth_output(reply)

        return filtered_reply


class FrontendWorker(Process):
    def __init__(self, name, read_queue: Queue, write_queue: Queue):
        Process.__init__(self, name=name)
        self._read_queue = read_queue
        self._write_queue = write_queue
        self._frontend = None

    def run(self):
        pass


class FrontendScheduler(object):
    def __init__(self):
        self._read_queue = Queue()
        self._write_queue = Queue()
        self._worker = None

    def recv(self) -> str:
        return self._read_queue.get()

    def send(self, message: str):
        self._write_queue.put(message)

    def start(self):
        self._worker.start()

    def shutdown(self):
        self._worker.terminate()


class Frontend(object):
    def __init__(self, reply_generator: FrontendReplyGenerator, event: Event):
        self._reply_generator = reply_generator
        self._scheduler = None
        self._thread = Thread(target=self.run)
        self._write_queue = Queue()
        self._read_queue = Queue()
        self._event = event
        self._shutdown_flag = False

    def start(self):
        self._scheduler.start()
        self._thread.start()

    def run(self):
        while not self._shutdown_flag:
            # Receive the message and put it in a queue
            self._read_queue.put(self._scheduler.recv())
            # Notify main program to wakeup and check for messages
            self._event.set()
            # Send the reply
            reply = self._write_queue.get()
            if reply is not None:
                self._scheduler.send(reply)

    def send(self, message: str):
        self._write_queue.put(message)

    def recv(self) -> Optional[str]:
        if not self._read_queue.empty():
            return self._read_queue.get()
        return None

    def shutdown(self):
        self._scheduler.shutdown()
        self._shutdown_flag = True

    def generate(self, message: str) -> str:
        return self._reply_generator.generate(message)