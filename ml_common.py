from multiprocessing import Process, Queue
from enum import Enum, unique


def one_hot(idx: int, size: int):
    ret = [0]*size
    ret[idx] = 1
    return ret


@unique
class MLModelCommands(Enum):
    SHUTDOWN = 0
    TRAIN = 1
    PREDICT = 2
    SAVE = 3
    LOAD = 4


class MLModelWorker(Process):
    def __init__(self, name, read_queue: Queue, write_queue: Queue, use_gpu: bool):
        Process.__init__(self, name=name)
        self._read_queue = read_queue
        self._write_queue = write_queue
        self._use_gpu = use_gpu
        self._model = None

    def run(self):
        while True:
            command, data = self._read_queue.get()
            if command == MLModelCommands.SHUTDOWN:
                return
            elif command == MLModelCommands.PREDICT:
                self._write_queue.put(self.predict(data))
            elif command == MLModelCommands.TRAIN:
                self._write_queue.put(self.train(data))
            elif command == MLModelCommands.SAVE:
                self._write_queue.put(self.save(data))

    def predict(self, *data):
        pass

    def train(self, *data):
        pass

    def save(self, *data):
        pass

    def load(self, *data):
        pass


class MLModelScheduler(object):
    def __init__(self):
        self._read_queue = Queue()
        self._write_queue = Queue()
        self._worker = None

    def start(self):
        self._worker.start()

    def shutdown(self):
        self._write_queue.put([MLModelCommands.SHUTDOWN, None])

    def _predict(self, *data):
        self._write_queue.put([MLModelCommands.PREDICT, data])
        return self._read_queue.get()

    def _train(self, *data):
        self._write_queue.put([MLModelCommands.TRAIN, data])
        return self._read_queue.get()

    def _save(self, *data):
        self._write_queue.put([MLModelCommands.SAVE, data])

    def _load(self, *data):
        self._write_queue.put([MLModelCommands.LOAD, data])

