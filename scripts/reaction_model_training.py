from reaction_model import *
from config import *
from ml_common import *
import numpy as np

if __name__ == '__main__':

    reaction_model = AOLReactionModel()

    csv_fetcher = CSVFileDataFetcher('training/markov_line_utf8.csv')

    rows = csv_fetcher.get_data()

    rows_filtered = []
    for row in rows:
        if row[0] != '':
            rows_filtered.append(row)

    data = np.zeros((len(rows_filtered), AOLReactionModel.NUM_FEATURES))
    labels = np.zeros((len(rows_filtered), 1))

    row_count = 0
    for row_idx, row in enumerate(rows_filtered):

        labels[row_idx] = int(row[0])
        data[row_idx] = np.array(AOLReactionFeatureAnalyzer.analyze(row[1]))

        row_count += 1

    reaction_model.train(data, labels, epochs=10)
    reaction_model.save(CONFIG_MARKOV_REACTION_PREDICT_MODEL_PATH)








