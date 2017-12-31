import pickle
from typing import Tuple
from spacy.tokens import Doc


def pickle_save(key, data):
    pickle.dump(data, open('cache/' + key + '.p', 'wb'))


def pickle_load(key):
    return pickle.load(open('cache/' + key + '.p', 'rb'))


def one_hot(idx: int, size: int):
    ret = [0]*size
    ret[idx] = 1
    return ret


class MLDataPreprocessor(object):
    def __init__(self):
        self.data = []
        self.labels = []

    def get_preprocessed_data(self) -> Tuple:
        pass

    def preprocess(self, doc: Doc):
        pass
