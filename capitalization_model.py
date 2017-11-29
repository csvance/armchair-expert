import re
from enum import Enum, unique

import numpy as np

from ml_common import MLModelWorker, MLModelScheduler


@unique
class PosEnum(Enum):
    # Universal
    ADJ = 1
    ADP = 2
    ADV = 3
    AUX = 4
    CONJ = 5
    CCONJ = 6
    DET = 7
    INTJ = 8
    NOUN = 9
    NUM = 10
    PART = 11
    PRON = 12
    PROPN = 13
    PUNCT = 14
    SCONJ = 15
    SYM = 16
    VERB = 17
    X = 18
    SPACE = 19

    # Custom
    EMOJI = 20
    HASHTAG = 21

    @staticmethod
    def get_pos_space(id) -> list:

        ret_list = []

        for i in range(1, len(PosEnum) + 1):
            if i != id.value:
                ret_list.append(0)
            else:
                ret_list.append(1)

        return ret_list


@unique
class WordPositions(Enum):
    FIRST = 1
    OTHER = 2

    @staticmethod
    def get_position_space(id):
        ret_list = []

        for i in range(1, len(WordPositions) + 1):
            if i != id.value:
                ret_list.append(0)
            else:
                ret_list.append(1)

        return ret_list


@unique
class CapitalizationMode(Enum):
    UPPER_FIRST = 1
    UPPER_ALL = 2
    LOWER_ALL = 3
    CHAOS = 4

    @staticmethod
    def get_mode_space(id):

        ret_list = []

        for i in range(1, len(CapitalizationMode) + 1):
            if i != id.value:
                ret_list.append(0)
            else:
                ret_list.append(1)

        return ret_list

    @staticmethod
    def transform(mode, word: str, ignore_prefix_regexp=None) -> str:

        if ignore_prefix_regexp is not None:
            if re.match(ignore_prefix_regexp, word):
                return word

        ret_word = word

        if mode == CapitalizationMode.UPPER_FIRST:

            first_upper_flag = False
            ret_list = []
            ret_word = ret_word.lower()

            # Find the first letter
            for c_idx, c in enumerate(ret_word):
                if c.isalpha() and not first_upper_flag:
                    ret_list.append(ret_word[c_idx].upper())
                    first_upper_flag = True
                else:
                    ret_list.append(c)
            ret_word = "".join(ret_list)

        elif mode == CapitalizationMode.UPPER_ALL:
            ret_word = ret_word.upper()
        elif mode == CapitalizationMode.LOWER_ALL:
            ret_word = ret_word.lower()
        elif mode == CapitalizationMode.CHAOS:

            ret_list = []
            for idx, c in enumerate(ret_word):
                if c.isalpha():
                    if idx % 2 == 0:
                        ret_list.append(c.lower())
                    else:
                        ret_list.append(c.upper())
            ret_word = "".join(ret_list)

        return ret_word


class CapitalizationFeatureAnalyzer(object):
    NUM_FEATURES = len(PosEnum) + len(WordPositions)

    @staticmethod
    def analyze(word: str, pos: str, word_position: int = 1) -> list:

        ret_list = []
        ret_list += PosEnum.get_pos_space(CapitalizationFeatureAnalyzer.get_pos(pos))
        ret_list += WordPositions.get_position_space(CapitalizationFeatureAnalyzer.get_word_position(word_position))

        return ret_list

    @staticmethod
    def label(word: str):

        ret_list = CapitalizationMode.get_mode_space(CapitalizationFeatureAnalyzer.get_capitalization_mode(word))
        return ret_list

    @staticmethod
    def features() -> list:
        return list(PosEnum) + list(WordPositions)

    @staticmethod
    def get_word_position(word_position: int) -> WordPositions:
        if word_position == 0:
            return WordPositions.FIRST
        else:
            return WordPositions.OTHER

    @staticmethod
    def get_capitalization_mode(word: str) -> CapitalizationMode:

        first_letter = None

        # Find the first letter
        for c_idx, c in enumerate(word):
            if word[c_idx].isalpha():
                first_letter = c_idx
                break

        if first_letter is not None:
            first_upper = word[first_letter].isupper()
            # Bounds Check
            if len(word) > first_letter + 1:
                second_upper = word[first_letter + 1].isupper()
            else:
                if first_upper:
                    # All alpha characters are capital
                    second_upper = True
                else:
                    second_upper = False

            if not first_upper and not second_upper:
                return CapitalizationMode.LOWER_ALL
            elif first_upper and not second_upper:
                return CapitalizationMode.UPPER_FIRST
            elif first_upper and second_upper:
                return CapitalizationMode.UPPER_ALL
            elif not first_upper and second_upper:
                return CapitalizationMode.CHAOS
        else:
            return CapitalizationMode.LOWER_ALL

    @staticmethod
    def get_pos(pos: str) -> PosEnum:
        return PosEnum[pos]


class CapitalizationModel(object):
    def __init__(self, path: str = None, use_gpu: bool = False):

        import tensorflow as tf
        from tensorflow.contrib.keras.api.keras.models import Sequential
        from tensorflow.contrib.keras.api.keras.layers import Dense
        from tensorflow.contrib.keras.api.keras.backend import set_session

        self.model = Sequential()
        self.model.add(Dense(CapitalizationFeatureAnalyzer.NUM_FEATURES, activation='relu',
                             input_dim=CapitalizationFeatureAnalyzer.NUM_FEATURES))
        self.model.add(Dense(len(CapitalizationMode), activation='softmax'))
        self.model.compile(optimizer='adam',
                           loss='categorical_crossentropy',
                           metrics=['accuracy'])

        if use_gpu:
            config = tf.ConfigProto()
            config.gpu_options.allow_growth = True
            set_session(tf.Session(config=config))

        if path is not None:
            self.load(path)

    def train(self, data, labels, epochs=1):
        self.model.fit(data, labels, epochs=epochs, batch_size=32)

    def predict(self, text: str, pos: str, word_index: int = 1) -> CapitalizationMode:
        features = np.array([CapitalizationFeatureAnalyzer.analyze(text, pos, word_index)])
        prediction = self.model.predict(features)[0]

        prediction_idx = np.random.choice([CapitalizationMode.UPPER_FIRST.value,
                                           CapitalizationMode.UPPER_ALL.value,
                                           CapitalizationMode.LOWER_ALL.value,
                                           CapitalizationMode.CHAOS.value],
                                          p=prediction)

        return CapitalizationMode(prediction_idx)

    def load(self, path):
        self.model.load_weights(path)

    def save(self, path):
        self.model.save_weights(path)


class CapitalizationModelWorker(MLModelWorker):
    def __init__(self, read_queue, write_queue, path: str = None, use_gpu: bool = False):
        MLModelWorker.__init__(self, name='CapitalizationModelWorker', read_queue=read_queue, write_queue=write_queue, path=path, use_gpu=use_gpu)

    def run(self):
        self._model = CapitalizationModel(path=self._path, use_gpu=self._use_gpu)
        MLModelWorker.run(self)

    def predict(self, data):
        return self._model.predict(text=data[0], pos=data[1], word_index=data[2])


class CapitalizationModelScheduler(MLModelScheduler):
    def __init__(self, path, use_gpu: bool = False):
        MLModelScheduler.__init__(self)
        self._worker = CapitalizationModelWorker(read_queue=self._write_queue, write_queue=self._read_queue, path=path,
                                                 use_gpu=use_gpu)

    def predict_capitalization(self, word: str, pos: str, word_index: int = 0):
        return self.predict((word, pos, word_index))
