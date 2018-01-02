import pickle
from typing import Tuple
from spacy.tokens import Doc
import os


def one_hot(idx: int, size: int):
    ret = [0]*size
    ret[idx] = 1
    return ret


class MLDataPreprocessor(object):
    def __init__(self, name: str):
        self.name = name
        self.data = []
        self.labels = []

    def get_preprocessed_data(self) -> Tuple:
        pass

    def preprocess(self, doc: Doc) -> bool:
        pass
