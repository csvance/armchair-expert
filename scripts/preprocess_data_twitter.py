import argparse
import json
import sys

import numpy as np
from keras.preprocessing.sequence import pad_sequences
from keras.utils import np_utils

from markov_engine import MarkovTrainer, MarkovTrieDb, MarkovFilters
from ml_common import pickle_save
from nlp_common import create_nlp_instance, Pos, CapitalizationMode
from structure_model import StructureFeatureAnalyzer
from structure_model import StructureModel, PoSCapitalizationMode

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('datafile')
    parser.add_argument('--words', help='preproccess words', action='store_true')
    parser.add_argument('--structure', help='preprocess structure', action='store_true')

    args = parser.parse_args()

    if not (args.words or args.structure):
        print("Error: must preprocess something.")
        print("Set one or more flags")
        sys.exit(-1)

    # Setup models / databases for training
    if args.words:
        word_docs = []
        markov_db = MarkovTrieDb()
        markov_trainer = MarkovTrainer(markov_db)

    if args.structure:
        structure_data = []
        structure_labels = []
        structure_shifted = []

    # Create spacy instance
    nlp = create_nlp_instance()

    # Open and read datafile
    tweet_data = open(args.datafile, 'r').read()
    tweets = json.loads(tweet_data)

    # Stats
    tweet_length_sum = 0
    tweet_count = 0

    doc_sum = 0
    sentence_sum = 0

    for tweet_idx, tweet in enumerate(tweets):

        # We don't want retweets
        if not tweet['is_retweet']:

            # Print Progress
            if tweet_idx % 100 == 0:
                print("%f%%" % (tweet_idx / len(tweets) * 100))

            filtered_tweet = MarkovFilters.filter_input(tweet['text'])

            doc = nlp(filtered_tweet)

            # Calculate some stats
            doc_sum += 1
            tweet_count += 1
            tweet_length_sum += len(doc)
            for sent in doc.sents:
                sentence_sum += 1
                tweet_length_sum += 1

            if args.words:
                word_docs.append(doc.to_bytes())

            if args.structure:
                sequence = []

                for sentence_idx, sentence in enumerate(doc.sents):
                    for token_idx, token in enumerate(sentence):
                        item = StructureFeatureAnalyzer.analyze(token, CapitalizationMode.from_token(token))
                        label = item

                        if len(sequence) == 0:
                            # Offset data by one, making label point to the next data item
                            sequence.append(PoSCapitalizationMode(Pos.NONE, CapitalizationMode.NONE).to_embedding())
                        else:
                            sequence.append(previous_item)

                        # We only want the latest SEQUENCE_LENGTH items
                        sequence = sequence[-StructureModel.SEQUENCE_LENGTH:]

                        structure_data.append(sequence.copy())
                        structure_labels.append(label)

                        previous_item = item

                    # Handle EOS after each sentence
                    item = PoSCapitalizationMode(Pos.EOS, CapitalizationMode.NONE).to_embedding()
                    label = item

                    sequence.append(previous_item)

                    # We only want the latest SEQUENCE_LENGTH items
                    sequence = sequence[-StructureModel.SEQUENCE_LENGTH:]

                    structure_data.append(sequence.copy())
                    structure_labels.append(label)

                    previous_item = item

    # Stats
    print("Average PoS per tweet: %f" % (tweet_length_sum / tweet_count))
    print("Average sentences per doc: %f" % (sentence_sum / doc_sum))

    if args.words:
        pickle_save('word_docs', word_docs)

    # Finish training capitalization data
    if args.structure:
        structure_data = pad_sequences(structure_data, StructureModel.SEQUENCE_LENGTH, padding='post')
        structure_labels = np_utils.to_categorical(structure_labels,
                                                   num_classes=StructureFeatureAnalyzer.NUM_FEATURES)

        pickle_save('structure_data', np.array(structure_data))
        pickle_save('structure_labels', structure_labels)

    print("%f%%" % 100.)
    print("Done.")
