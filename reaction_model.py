from config import *
import pandas as pd
import csv
import string
import re
import pandas as pd
import tensorflow as tf
import tempfile


def file_to_utf8(path):
    data = open(path,'rb').read()
    utf8_data = data.decode('utf-8','ignore')
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

class Reaction(object):
    def __init__(self):
        self.stats = {}
        self.data = []
        self.pd_data = None

    def input_fn(self,data_file, num_epochs, shuffle):
        with open(data_file, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row[0] != '':
                    self.data.append({'reaction': int(row[0]),'text': row[1]})

        self.compute_stats()

        df_data = pd.DataFrame.from_dict(self.data)
        df_data = df_data.dropna(how="any", axis=0)

        self.pd_data = df_data

        labels = df_data['reaction'].astype(int)

        return  tf.estimator.inputs.pandas_input_fn(
            x=df_data,
            y=labels,
            batch_size=100,
            num_epochs=num_epochs,
            shuffle=shuffle,
            num_threads=4)


    def compute_stats(self):

        self.stats['length'] = 0
        self.stats['whitespace'] = 0
        self.stats['lines'] = 0

        for line in self.data:

            # Line Length
            line['length'] = len(line['text'])
            self.stats['length'] += line['length']

            # Whitespace
            line['whitespace'] = line['text'].count(" ")
            self.stats['length'] += line['whitespace']

            line['letter_diversity_ratio'] = letter_diversity_ratio(line['text'])
            line['upper_lower_ratio'] = upper_lower_ratio(line['text'])
            line['letter_symbol_ratio'] = letter_symbol_ratio(line['text'])
            line['aol_letter_ratio'] = aol_letter_ratio(line['text'])

            self.stats['lines'] += 1


def print_classifications(classifier, data):
    predict_input_fn = tf.estimator.inputs.pandas_input_fn(x=data, num_epochs=1, shuffle=False)

    predictions = list(classifier.predict(input_fn=predict_input_fn))

    for index, row in data.iterrows():
        text = row['text']
        c = predictions[index]['classes'][0]
        if int(c) == 1:
            print("%s: %s" % (c, text))


def print_evaluation(model):
    results = model.evaluate(
        input_fn=r.input_fn(data_file_path, num_epochs=1, shuffle=False),
        steps=None)

    for key in sorted(results):
        print("%s: %s" % (key, results[key]))

# Make sure the file is UTF-8
data_file_path = 'learning/markov_line_utf8.csv'
data = file_to_utf8(data_file_path)
open(data_file_path,'w').write(data)

r = Reaction()

fc_length = tf.feature_column.numeric_column("length")
fc_whitespace = tf.feature_column.numeric_column("whitespace")
fc_letter_diversity_ratio = tf.feature_column.numeric_column("letter_diversity_ratio")
fc_upper_lower_ratio = tf.feature_column.numeric_column("upper_lower_ratio")
fc_letter_symbol_ratio = tf.feature_column.numeric_column("letter_symbol_ratio")
fc_aol_letter_ratio = tf.feature_column.numeric_column("aol_letter_ratio")

base_columns = [fc_length,fc_whitespace,fc_letter_diversity_ratio,fc_upper_lower_ratio,fc_letter_symbol_ratio,fc_aol_letter_ratio]

model_dir = tempfile.mkdtemp()

m = tf.estimator.LinearClassifier(model_dir=model_dir, feature_columns=base_columns)
m.train(input_fn=r.input_fn(data_file_path, num_epochs=1, shuffle=True), steps=None)


print_evaluation(m)
#print_classifications(m,r.pd_data)


