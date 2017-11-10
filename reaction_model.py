from config import *
import csv
import re
import pandas as pd
import tensorflow as tf

def repeated_letter_ratio(line):

    repeated_count = 0
    not_repeated_count = 0

    for idx,c in enumerate(line):
        if idx != len(line)-1:
            if c == line[idx+1]:
                repeated_count += 1
            else:
                not_repeated_count += 1

    total_count = repeated_count + not_repeated_count

    if total_count != 0:
        return repeated_count / float(total_count)
    else:
        return 0.0


def aol_letter_ratio(line):
    txt_lower = line.lower()

    max_ratio = 0.0

    signal_sum = 0
    noise_sum = 0

    for check_letters in CONFIG_MARKOV_REACTION_CHARS:
        letters_found = {}
        for c in check_letters:
            if c in line:
                letters_found[c] = True
            signal_sum += txt_lower.count(c)

        found_ratio = len(letters_found) / len(check_letters)

        current_ratio = (found_ratio*signal_sum) / len(txt_lower)

        max_ratio = max_ratio if current_ratio < max_ratio else current_ratio

        signal_sum = 0

    return max_ratio


def upper_lower_ratio(line):
    letter_count = 0.0
    upper_count = 0.0
    lower_count = 0.0

    lower_count = len(re.findall(r"[a-z]+", line))
    upper_count = len(re.findall(r"[A-Z]+", line))

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

    letter_count = len(re.findall(r"[a-zA-Z0-9]+", line))

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
    def __init__(self, model_dir="models/aol-reaction-model/"):
        self.data = []
        self.training_data = None
        self.y_label = None
        self.model_dir = model_dir
        self.classifier = self.create_tensor()

    def create_tensor(self):
        fc_length = tf.feature_column.numeric_column("length")
        fc_whitespace = tf.feature_column.numeric_column("whitespace")
        fc_letter_diversity_ratio = tf.feature_column.numeric_column("letter_diversity_ratio")
        fc_upper_lower_ratio = tf.feature_column.numeric_column("upper_lower_ratio")
        fc_letter_symbol_ratio = tf.feature_column.numeric_column("letter_symbol_ratio")
        fc_aol_letter_ratio = tf.feature_column.numeric_column("aol_letter_ratio")
        fc_repeated_letter_ratio = tf.feature_column.numeric_column("repeated_letter_ratio")

        base_columns = [fc_length, fc_whitespace, fc_letter_diversity_ratio, fc_upper_lower_ratio,
                        fc_letter_symbol_ratio,
                        fc_aol_letter_ratio,fc_repeated_letter_ratio]

        return tf.estimator.LinearClassifier(model_dir=self.model_dir, feature_columns=base_columns)

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

        classifications = []

        predict_input_fn = self.eval_data_input_fn(data)
        predictions = list(self.classifier.predict(input_fn=predict_input_fn))

        for idx, row in enumerate(data):
            classifications.append(bool(int(predictions[idx]['classes'][0])))

        return classifications

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
            line['repeated_letter_ratio'] = repeated_letter_ratio(line['text'])

        return data