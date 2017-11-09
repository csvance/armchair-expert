from config import *
import pandas as pd
import csv
import string
import re
import pandas as pd
import tensorflow as tf
import tempfile


def file_to_utf8(path):
    b_data = open(path, 'rb').read()
    utf8_data = b_data.decode('utf-8', 'ignore')
    return str(utf8_data)


def aol_letter_ratio(line):
    txt_lower = line.lower()

    max_ratio = 0.0

    signal_sum = 0
    noise_sum = 0

    for one_word in CONFIG_MARKOV_REACTION_CHARS:
        for c in one_word:
            signal_sum += txt_lower.count(c)

        current_ratio = signal_sum / len(txt_lower)

        max_ratio = max_ratio if current_ratio < max_ratio else current_ratio

        signal_sum = 0

    return max_ratio


def upper_lower_ratio(line):
    letter_count = 0.0
    upper_count = 0.0
    lower_count = 0.0

    lower_count = len(re.findall("[a-z]", line))
    upper_count = len(re.findall("[A-Z]", line))

    letter_count = lower_count + upper_count

    if letter_count > 0:
        return upper_count / letter_count
    else:
        return 0.0


def letter_symbol_ratio(line):
    char_count = len(line)
    letter_count = 0.0
    upper_count = 0.0
    lower_count = 0.0

    lower_count = len(re.findall("[a-z]+", line))
    upper_count = len(re.findall("[A-Z]+", line))

    letter_count = lower_count + upper_count

    return letter_count / char_count


def letter_diversity_ratio(line):
    chars = {}

    for c in line:
        try:
            chars[c] += 1
        except KeyError:
            chars[c] = 1

    return len(chars) / len(line)


class AOLReactionModel(object):
    def __init__(self, classifier):
        self.data = []
        self.training_data = None
        self.y_label = None
        self.classifier = classifier

    def reset_training_data(self):
        self.training_data = None

    def training_file_input_fn(self, data_file, num_epochs, shuffle):

        input_data = []
        if self.training_data is None:
            with open(data_file, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row[0] != '':
                        input_data.append({'reaction': int(row[0]), 'text': row[1]})

            self.compute_stats(input_data)

            pd_eval_data = pd.DataFrame.from_dict(input_data)
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

    def eval_data_input_fn(self, data):

        data_rows = []

        for row in data:
            data_rows.append({'text': row})

        data_rows = self.compute_stats(data_rows)

        pd_eval_data = pd.DataFrame.from_dict(data_rows)

        return tf.estimator.inputs.pandas_input_fn(
            x=pd_eval_data,
            num_epochs=1,
            shuffle=False)

    def classify_data(self, data):
        predict_input_fn = self.eval_data_input_fn(data)
        predictions = list(self.classifier.predict(input_fn=predict_input_fn))

        for idx,row in enumerate(data):
            text = row
            c = predictions[idx]['classes'][0]
            print("%s: %s" % (c, text))

    def print_evaluation(self, file_path):
        results = self.classifier.evaluate(
            input_fn=self.training_file_input_fn(file_path, num_epochs=1, shuffle=False),
            steps=None)

        for key in sorted(results):
            print("%s: %s" % (key, results[key]))

    def train(self, file_path, epochs=1):
        self.classifier.train(input_fn=self.training_file_input_fn(file_path, num_epochs=epochs, shuffle=True),
                              steps=None)

    def compute_stats(self, data):

        for line in data:
            # Line Length
            line['length'] = len(line['text'])

            # Whitespace
            line['whitespace'] = line['text'].count(" ")

            line['letter_diversity_ratio'] = letter_diversity_ratio(line['text'])
            line['upper_lower_ratio'] = upper_lower_ratio(line['text'])
            line['letter_symbol_ratio'] = letter_symbol_ratio(line['text'])
            line['aol_letter_ratio'] = aol_letter_ratio(line['text'])

        return data


def create_reaction_model():
    fc_length = tf.feature_column.numeric_column("length")
    fc_whitespace = tf.feature_column.numeric_column("whitespace")
    fc_letter_diversity_ratio = tf.feature_column.numeric_column("letter_diversity_ratio")
    fc_upper_lower_ratio = tf.feature_column.numeric_column("upper_lower_ratio")
    fc_letter_symbol_ratio = tf.feature_column.numeric_column("letter_symbol_ratio")
    fc_aol_letter_ratio = tf.feature_column.numeric_column("aol_letter_ratio")

    base_columns = [fc_length, fc_whitespace, fc_letter_diversity_ratio, fc_upper_lower_ratio, fc_letter_symbol_ratio,
                    fc_aol_letter_ratio]

    model_dir = tempfile.mkdtemp()

    classifier = tf.estimator.LinearClassifier(model_dir=model_dir, feature_columns=base_columns)

    r = AOLReactionModel(classifier)

    return r


data_path = 'learning/markov_line_utf8.csv'
r = create_reaction_model()

r.train(data_path, epochs=100)
r.print_evaluation(data_path)
r.classify_data(['lol', 'haha', 'wtf', 'llOloloLOlo', 'oh hi mark'])