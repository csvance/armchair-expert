import csv
import re

import pandas as pd
import tensorflow as tf
from tensorflow.contrib.saved_model.python.saved_model import reader
from tensorflow.contrib.saved_model.python.saved_model import signature_def_utils
from tensorflow.python.saved_model import loader

from config import *
from ml_common import *


def export_fn():
    features = {
        'length': tf.placeholder(dtype=tf.int32, shape=[None], name="length"),
        'whitespace': tf.placeholder(dtype=tf.int32, shape=[None], name="whitespace"),
        'letter_diversity_ratio': tf.placeholder(dtype=tf.float32, shape=[None], name="letter_diversity_ratio"),
        'upper_lower_ratio': tf.placeholder(dtype=tf.float32, shape=[None], name="upper_lower_ratio"),
        'aol_letter_ratio': tf.placeholder(dtype=tf.float32, shape=[None], name="aol_letter_ratio"),
        'repeated_letter_ratio': tf.placeholder(dtype=tf.float32, shape=[None], name="repeated_letter_ratio"),
        'funny_emoji_ratio': tf.placeholder(dtype=tf.float32, shape=[None], name="funny_emoji_ratio"),
        'letter_symbol_ratio': tf.placeholder(dtype=tf.float32, shape=[None], name="letter_symbol_ratio")
    }
    return tf.estimator.export.build_raw_serving_input_receiver_fn(features)


class AOLReactionFeatureAnalyzer(MLFeatureAnalyzer):
    def __init__(self, data: list):
        MLFeatureAnalyzer.__init__(self, data)

    def analyze_row(self, line: dict) -> dict:

        line['length'] = len(line['text'])
        line['whitespace'] = line['text'].count(" ")

        line['letter_diversity_ratio'] = AOLReactionFeatureAnalyzer.letter_diversity_ratio(line['text'])
        line['upper_lower_ratio'] = AOLReactionFeatureAnalyzer.upper_lower_ratio(line['text'])
        line['letter_symbol_ratio'] = AOLReactionFeatureAnalyzer.letter_symbol_ratio(line['text'])
        line['aol_letter_ratio'] = AOLReactionFeatureAnalyzer.aol_letter_ratio(line['text'])
        line['repeated_letter_ratio'] = AOLReactionFeatureAnalyzer.repeated_letter_ratio(line['text'])
        line['funny_emoji_ratio'] = AOLReactionFeatureAnalyzer.funny_emoji_ratio(line['text'])

        return line

    @staticmethod
    def funny_emoji_ratio(line: str) -> float:

        emoji_len = 0.

        for emoji in [':laughing:', ':grinning:', ':smile:', ':satisfied:', ':smiley:', ':sweat_smile:',
                      ':joy_cat:', ':joy:']:
            emoji_len += line.count(emoji) * len(emoji)

        return emoji_len / len(line)

    @staticmethod
    def repeated_letter_ratio(line: str) -> float:

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
        lower_count = len(re.findall(r'[a-z]+', line))
        upper_count = len(re.findall(r'[A-Z]+', line))

        letter_count = lower_count + upper_count

        if letter_count > 0:
            return upper_count / letter_count
        else:
            return 0.0

    @staticmethod
    def letter_symbol_ratio(line: str) -> float:
        char_count = len(line)
        letter_count = len(re.findall(r"[a-zA-Z0-9]+", line))

        return letter_count / char_count

    @staticmethod
    def letter_diversity_ratio(line: str) -> float:
        chars = {}

        for c in line:
            try:
                chars[c] += 1
            except KeyError:
                chars[c] = 1

        return len(chars) / len(line)


class AOLReactionModelTrainer(object):
    def __init__(self, model_dir: str = CONFIG_MARKOV_REACTION_TRAINING_MODEL_PATH):
        self.data = []
        self.training_data = None
        self.y_label = None
        self.model_dir = model_dir
        self.feature_spec = None
        self.classifier = self.create_tensor()

    def create_tensor(self):
        fc_length = tf.feature_column.numeric_column("length", dtype=tf.int32)
        fc_whitespace = tf.feature_column.numeric_column("whitespace", dtype=tf.int32)
        fc_letter_diversity_ratio = tf.feature_column.numeric_column("letter_diversity_ratio")
        fc_upper_lower_ratio = tf.feature_column.numeric_column("upper_lower_ratio")
        fc_aol_letter_ratio = tf.feature_column.numeric_column("aol_letter_ratio")
        fc_repeated_letter_ratio = tf.feature_column.numeric_column("repeated_letter_ratio")
        fc_funny_emoji_ratio = tf.feature_column.numeric_column("funny_emoji_ratio")
        fc_letter_symbol_ratio = tf.feature_column.numeric_column("letter_symbol_ratio")

        base_columns = [fc_length, fc_whitespace, fc_letter_diversity_ratio, fc_upper_lower_ratio,
                        fc_aol_letter_ratio, fc_repeated_letter_ratio, fc_funny_emoji_ratio, fc_letter_symbol_ratio]

        # TODO: Use this for export the model, but TF API seems broken
        # self.feature_spec = feature_spec = tf.feature_column.make_parse_example_spec(base_columns)

        return tf.estimator.LinearClassifier(model_dir=self.model_dir, feature_columns=base_columns)

    def reset_training_data(self):
        self.training_data = None

    def training_file_input_fn(self, data_file: str, num_epochs: int, shuffle: bool):

        input_data = []
        if self.training_data is None:

            csv_rows = CSVFileDataFetcher(data_file).get_data()

            for row in csv_rows:
                if row[0] != '':
                    input_data.append({'reaction': int(row[0]), 'text': row[1]})

            analyzer = AOLReactionFeatureAnalyzer(input_data)
            input_data = analyzer.analyze()

            pd_eval_data = pd.DataFrame.from_records(input_data)
            pd_eval_data = pd_eval_data.dropna(how="any", axis=0)

            self.training_data = pd_eval_data
            self.y_label = pd_eval_data['reaction'].astype(int)

        return tf.estimator.inputs.pandas_input_fn(
            x=self.training_data,
            y=self.y_label,
            batch_size=100,
            num_epochs=num_epochs,
            shuffle=shuffle,
            num_threads=4)

    # noinspection PyMethodMayBeStatic
    def eval_data_input_fn(self, data: list):

        data_rows = []

        for row in data:
            data_rows.append({'text': row})

        analyzer = AOLReactionFeatureAnalyzer(data_rows)
        data_rows = analyzer.analyze()

        pd_eval_data = pd.DataFrame.from_records(data_rows)

        return tf.estimator.inputs.pandas_input_fn(
            x=pd_eval_data,
            num_epochs=1,
            shuffle=False)

    def classify_data(self, data: list) -> list:

        classifications = []

        predict_input_fn = self.eval_data_input_fn(data)
        predictions = list(self.classifier.predict(input_fn=predict_input_fn))

        for idx, row in enumerate(data):
            classifications.append(bool(int(predictions[idx]['classes'][0])))

        return classifications

    def print_evaluation(self, file_path: str) -> None:
        results = self.classifier.evaluate(
            input_fn=self.training_file_input_fn(file_path, num_epochs=1, shuffle=False),
            steps=None)

        for key in sorted(results):
            print("%s: %s" % (key, results[key]))

    def train(self, file_path: str, epochs: int = 1):
        self.classifier.train(input_fn=self.training_file_input_fn(file_path, num_epochs=epochs, shuffle=True),
                              steps=None)


class AOLReactionModelPredictor(object):
    def __init__(self, saved_model_dir: str = CONFIG_MARKOV_REACTION_PREDICT_MODEL_PATH):
        self.model = reader.read_saved_model(saved_model_dir=saved_model_dir)
        self.meta_graph = None
        for meta_graph_def in self.model.meta_graphs:
            if 'serve' in meta_graph_def.meta_info_def.tags:
                self.meta_graph = meta_graph_def
        self.signature_def = signature_def_utils.get_signature_def_by_key(self.meta_graph, "predict")
        self.output_tensor = self.signature_def.outputs['classes'].name

        self.sess = tf.Session()
        loader.load(self.sess, ['serve'], saved_model_dir)

    def predict(self, sentence: str) -> list:
        reaction_analyer = AOLReactionFeatureAnalyzer([{'text': sentence}])

        keys = reaction_analyer.analyze()[0]
        inputs_feed_dict = {
            self.signature_def.inputs['length'].name: [keys['length']],
            self.signature_def.inputs['whitespace'].name: [keys['whitespace']],
            self.signature_def.inputs['letter_diversity_ratio'].name: [keys['letter_diversity_ratio']],
            self.signature_def.inputs['upper_lower_ratio'].name: [keys['upper_lower_ratio']],
            self.signature_def.inputs['aol_letter_ratio'].name: [keys['aol_letter_ratio']],
            self.signature_def.inputs['repeated_letter_ratio'].name: [keys['repeated_letter_ratio']],
            self.signature_def.inputs['funny_emoji_ratio'].name: [keys['funny_emoji_ratio']],
            self.signature_def.inputs['letter_symbol_ratio'].name: [keys['letter_symbol_ratio']]
        }

        outputs = self.sess.run(self.output_tensor, feed_dict=inputs_feed_dict)
        return outputs
