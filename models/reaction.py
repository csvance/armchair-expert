import re
from multiprocessing import Queue

import numpy as np

from models.model_common import MLModelScheduler, MLModelWorker


class AOLReactionFeatureAnalyzer(object):
    NUM_FEATURES = 8

    @staticmethod
    def analyze(text: str) -> list:
        return [
            len(text),
            text.count(" "),
            AOLReactionFeatureAnalyzer.letter_diversity_ratio(text),
            AOLReactionFeatureAnalyzer.upper_lower_ratio(text),
            AOLReactionFeatureAnalyzer.letter_symbol_ratio(text),
            AOLReactionFeatureAnalyzer.aol_letter_ratio(text),
            AOLReactionFeatureAnalyzer.repeated_letter_ratio(text),
            AOLReactionFeatureAnalyzer.funny_emoji_ratio(text)
        ]

    @staticmethod
    def features() -> list:
        return [
            'length',
            'whitespace',
            'letter_diversity_ratio',
            'upper_lower_ratio',
            'letter_symbol_ratio',
            'aol_letter_ratio',
            'repeated_letter_ratio',
            'funny_emoji_ratio'
        ]

    @staticmethod
    def funny_emoji_ratio(line: str) -> float:

        if len(line) == 0:
            return 0.

        emoji_len = 0.

        for emoji in ['😂', '😁', '😊', '😁', '😃', '😄',
                      '😹', '🤣']:
            emoji_len += line.count(emoji) * len(emoji)

        return emoji_len / len(line)

    @staticmethod
    def repeated_letter_ratio(line: str) -> float:

        if len(line) == 0:
            return 0.

        repeated_count = 0
        not_repeated_count = 0

        for idx, c in enumerate(line):
            if idx != len(line) - 1:
                if c == line[idx + 1]:
                    repeated_count += 1
                else:
                    not_repeated_count += 1

        total_count = repeated_count + not_repeated_count

        if total_count != 0:
            return repeated_count / float(total_count)
        else:
            return 0.0

    @staticmethod
    def aol_letter_ratio(line: str) -> float:

        if len(line) == 0:
            return 0.

        txt_lower = line.lower()

        max_ratio = 0.0

        signal_sum = 0

        for check_letters in ['lo', 'wtf', 'lmao', 'ha', 'rekt', 'rofl', 'omg']:
            letters_found = {}
            for c in check_letters:
                if c in line:
                    letters_found[c] = True
                signal_sum += txt_lower.count(c)

            found_ratio = len(letters_found) / len(check_letters)

            current_ratio = (found_ratio * signal_sum) / len(txt_lower)

            max_ratio = max_ratio if current_ratio < max_ratio else current_ratio

            signal_sum = 0

        return max_ratio

    @staticmethod
    def upper_lower_ratio(line: str) -> float:

        if len(line) == 0:
            return 0.

        lower_count = len(re.findall(r'[a-z]+', line))
        upper_count = len(re.findall(r'[A-Z]+', line))

        letter_count = lower_count + upper_count

        if letter_count > 0:
            return upper_count / letter_count
        else:
            return 0.

    @staticmethod
    def letter_symbol_ratio(line: str) -> float:

        if len(line) == 0:
            return 0.

        char_count = len(line)
        letter_count = len(re.findall(r"[a-zA-Z0-9]+", line))

        return letter_count / char_count

    @staticmethod
    def letter_diversity_ratio(line: str) -> float:

        if len(line) == 0:
            return 0.

        chars = {}

        for c in line:
            try:
                chars[c] += 1
            except KeyError:
                chars[c] = 1

        return len(chars) / len(line)


class AOLReactionModel(object):
    PREDICT_THRESHOLD = 0.50

    def __init__(self, path: str = None, use_gpu=False):

        import tensorflow as tf
        from keras.models import Sequential
        from keras.layers import Dense
        from keras.backend import set_session

        self.model = Sequential()
        self.model.add(Dense(AOLReactionFeatureAnalyzer.NUM_FEATURES, activation='relu',
                             input_dim=AOLReactionFeatureAnalyzer.NUM_FEATURES))
        self.model.add(Dense(AOLReactionFeatureAnalyzer.NUM_FEATURES - 2, activation='relu'))
        self.model.add(Dense(1, activation='sigmoid'))
        self.model.compile(optimizer='rmsprop',
                           loss='binary_crossentropy',
                           metrics=['accuracy'])

        if use_gpu:
            config = tf.ConfigProto()
            config.gpu_options.allow_growth = True
            set_session(tf.Session(config=config))

    def train(self, data, labels, epochs=1):
        self.model.fit(np.array(data), np.array(labels), epochs=epochs, batch_size=32)

    def predict(self, text: str):
        features = np.array([AOLReactionFeatureAnalyzer.analyze(text)])
        prediction = self.model.predict(features)[0]
        if prediction >= AOLReactionModel.PREDICT_THRESHOLD:
            return True
        else:
            return False

    def load(self, path):
        self.model.load_weights(path)

    def save(self, path):
        self.model.save_weights(path)


class AOLReactionModelWorker(MLModelWorker):
    def __init__(self, read_queue: Queue, write_queue: Queue, use_gpu: bool = False):
        MLModelWorker.__init__(self, name='AOLReactionModelWorker', read_queue=read_queue, write_queue=write_queue,
                               use_gpu=use_gpu)

    def run(self):
        self._model = AOLReactionModel(use_gpu=self._use_gpu)
        MLModelWorker.run(self)

    def predict(self, *data):
        return self._model.predict(text=data[0][0])

    def train(self, *data):
        return self._model.train(data=data[0][0], labels=data[0][1], epochs=data[0][2])

    def save(self, *data):
        return self._model.save(path=data[0][0])

    def load(self, *data):
        return self._model.load(path=data[0][0])


class AOLReactionModelScheduler(MLModelScheduler):
    def __init__(self, path, use_gpu: bool = False):
        MLModelScheduler.__init__(self)
        self._worker = AOLReactionModelWorker(read_queue=self._write_queue, write_queue=self._read_queue,
                                              use_gpu=use_gpu)

    def predict(self, text: str):
        return self._predict(text)

    def train(self, data, labels, epochs=1):
        return self._train(data, labels, epochs)

    def save(self, path):
        return self._save(path)

    def load(self, path):
        return self._load(path)