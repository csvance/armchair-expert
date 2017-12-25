import re
from enum import Enum, unique

import numpy as np

from ml_common import MLModelWorker, MLModelScheduler
from nlp_common import Pos
from multiprocessing import Queue


@unique
class WordPositionEnum(Enum):
    FIRST = 1
    OTHER = 2

    @staticmethod
    def get_position_space(position: 'WordPositionEnum'):
        ret_list = []

        for i in range(1, len(WordPositionEnum) + 1):
            if i != position.value:
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
    def get_mode_space(mode: 'CapitalizationMode'):

        ret_list = []

        for i in range(1, len(CapitalizationMode) + 1):
            if i != mode.value:
                ret_list.append(0)
            else:
                ret_list.append(1)

        return ret_list

    @staticmethod
    def transform(mode: 'CapitalizationMode', word: str, ignore_prefix_regexp=None) -> str:

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
    NUM_FEATURES = len(Pos) + len(WordPositionEnum)

    @staticmethod
    def analyze(pos: Pos, word_position: int = 1) -> list:

        ret_list = []
        ret_list += Pos.one_hot(pos)
        ret_list += WordPositionEnum.get_position_space(CapitalizationFeatureAnalyzer.get_word_position(word_position))

        return ret_list

    @staticmethod
    def label(word: str):

        mode = CapitalizationFeatureAnalyzer.get_capitalization_mode(word)
        ret_list = CapitalizationMode.get_mode_space(mode)
        return ret_list

    @staticmethod
    def features() -> list:
        return list(Pos) + list(WordPositionEnum)

    @staticmethod
    def get_word_position(word_position: int) -> WordPositionEnum:
        if word_position == 0:
            return WordPositionEnum.FIRST
        else:
            return WordPositionEnum.OTHER

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
    def get_pos(pos: str) -> Pos:
        return Pos[pos]


class CapitalizationModel(object):
    def __init__(self, use_gpu: bool = False):

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

    def train(self, data, labels, epochs=1):
        self.model.fit(np.array(data), np.array(labels), epochs=epochs, batch_size=32)

    def predict(self, text: str, pos: Pos, word_index: int = 1) -> CapitalizationMode:
        features = np.array([CapitalizationFeatureAnalyzer.analyze(pos, word_index)])
        prediction = self.model.predict(features)[0]

        prediction_idx = np.random.choice([CapitalizationMode.UPPER_FIRST.value,
                                           CapitalizationMode.UPPER_ALL.value,
                                           CapitalizationMode.LOWER_ALL.value,
                                           CapitalizationMode.CHAOS.value],
                                          p=prediction)

        mode = CapitalizationMode(prediction_idx)
        return mode

    def load(self, path):
        self.model.load_weights(path)

    def save(self, path):
        self.model.save_weights(path)


class CapitalizationModelWorker(MLModelWorker):
    def __init__(self, read_queue: Queue, write_queue : Queue, use_gpu: bool = False):
        MLModelWorker.__init__(self, name='CapitalizationModelWorker', read_queue=read_queue, write_queue=write_queue, use_gpu=use_gpu)

    def run(self):
        self._model = CapitalizationModel(use_gpu=self._use_gpu)
        MLModelWorker.run(self)

    def predict(self, *data):
        return self._model.predict(text=data[0][0], pos=data[0][1], word_index=data[0][2])

    def train(self, *data):
        return self._model.train(data=data[0][0], labels=data[0][1], epochs=data[0][2])

    def save(self, *data):
        return self._model.save(path=data[0][0])

    def load(self, *data):
        return self._model.load(path=data[0][0])


class CapitalizationModelScheduler(MLModelScheduler):
    def __init__(self, use_gpu: bool = False):
        MLModelScheduler.__init__(self)
        self._worker = CapitalizationModelWorker(read_queue=self._write_queue, write_queue=self._read_queue,
                                                 use_gpu=use_gpu)

    def predict(self, word: str, pos: Pos, word_index: int = 0):
        return self._predict(word, pos, word_index)

    def train(self, data, labels, epochs=1):
        return self._train(data, labels, epochs)

    def save(self, path):
        return self._save(path)

    def load(self, path):
        return self._load(path)