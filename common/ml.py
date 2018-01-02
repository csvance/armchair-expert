import pickle
from typing import Tuple
from spacy.tokens import Doc
import os

def pickle_save(key, data):
    pickle.dump(data, open('cache/' + key + '.p', 'wb'))


def pickle_load(key):
    return pickle.load(open('cache/' + key + '.p', 'rb'))


def one_hot(idx: int, size: int):
    ret = [0]*size
    ret[idx] = 1
    return ret


class MLDataPreprocessor(object):
    def __init__(self, name: str):
        self.name = name
        self.data = []
        self.labels = []

    def save_cache(self, path: str):
        pickle.dump(self.data, open(path + self.name + '_data.p', 'wb'))
        pickle.dump(self.labels, open(path + self.name + '_labels.p', 'wb'))

    def load_cache(self, path: str):
        self.data = pickle.load(open(path + self.name + '_data.p', 'rb'))
        self.labels = pickle.load(open(path + self.name + '_labels.p', 'rb'))

    def wipe_cache(self, path: str):
        os.unlink(path + self.name + '_data.p')
        os.unlink(path + self.name + '_labels.p')

    def get_preprocessed_data(self) -> Tuple:
        pass

    def preprocess(self, doc: Doc) -> bool:
        pass
