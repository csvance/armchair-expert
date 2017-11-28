import re
import numpy as np

import tensorflow as tf
from tensorflow.contrib.keras.api.keras.models import Sequential, load_model
from tensorflow.contrib.keras.api.keras.layers import Dense, Activation
from tensorflow.contrib.keras.api.keras.backend import set_session


class AOLReactionFeatureAnalyzer(object):

    @staticmethod
    def analyze(text: str) -> np.array:
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
    NUM_FEATURES = 8
    PREDICT_THRESHOLD = 0.50

    def __init__(self, path: str=None, use_gpu=False):

        self.model = Sequential()
        self.model.add(Dense(AOLReactionModel.NUM_FEATURES, activation='relu', input_dim=AOLReactionModel.NUM_FEATURES))
        self.model.add(Dense(1, activation='sigmoid'))
        self.model.compile(optimizer='rmsprop',
              loss='binary_crossentropy',
              metrics=['accuracy'])

        if use_gpu:
            config = tf.ConfigProto()
            config.gpu_options.allow_growth = True
            set_session(tf.Session(config=config))

        if path is not None:
            self.load(path)

    def train(self, data, labels, epochs=1):
         self.model.fit(data, labels, epochs=epochs, batch_size=32)

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