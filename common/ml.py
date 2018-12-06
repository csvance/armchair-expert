import pickle
from typing import Tuple
from spacy.tokens import Doc
import numpy as np
import os


def temp(p, temperature=1.0):
    preds = np.asarray(p).astype('float64')
    preds = np.log(preds) / temperature
    exp_preds = np.exp(preds)
    preds = exp_preds / np.sum(exp_preds)
    probas = np.random.multinomial(1, preds, 1)
    index = np.argmax(probas)
    return index


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
