import argparse
import json
import sys

from markov_engine import MarkovTrainer, MarkovTrieDb, MarkovFilters
from capitalization_model import CapitalizationModelScheduler, CapitalizationFeatureAnalyzer
from ml_config import MARKOV_DB_PATH, POSTREE_DB_PATH, CAPITALIZATION_MODEL_PATH, USE_GPU
from nlp_common import create_nlp_instance, Pos
from pos_tree_model import PosTreeModel

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('datafile')
    parser.add_argument('--train-words', help='train words', action='store_true')
    parser.add_argument('--train-pos', help='train parts of speech', action='store_true')
    parser.add_argument('--train-capitalization', help='train capitalization', action='store_true')
    args = parser.parse_args()

    if not (args.train_words or args.train_pos or args.train_capitalization):
        print("Error: must train something.")
        print("Set one or more training flags")
        sys.exit(-1)

    # Setup models / databases for training
    if args.train_words:
        markov_db = MarkovTrieDb()
        markov_trainer = MarkovTrainer(markov_db)

    if args.train_pos:
        postree_db = PosTreeModel()

    if args.train_capitalization:
        capitalization_model = CapitalizationModelScheduler(use_gpu=USE_GPU)
        capitalization_model.start()
        capitalization_data = []
        capitalization_labels = []

    # Create spacy instance
    nlp = create_nlp_instance()

    # Open and read datafile
    tweet_data = open(args.datafile, 'r').read()
    tweets = json.loads(tweet_data)

    for tweet_idx, tweet in enumerate(tweets):

        # We don't want retweets
        if not tweet['is_retweet']:

            # Print Progress
            if tweet_idx % 100 == 0:
                print("%f%%" % (tweet_idx/len(tweets) * 100))

            filtered_tweet = MarkovFilters.filter_input(tweet['text'])

            doc = nlp(filtered_tweet)

            if args.train_words:
                markov_trainer.learn(doc)
            if args.train_pos:
                postree_db.learn(doc)
            if args.train_capitalization:
                for sent in doc.sents:
                    for token_idx, token in enumerate(sent):
                        capitalization_data.append(CapitalizationFeatureAnalyzer.analyze(Pos.from_token(token), word_position=token_idx))
                        capitalization_labels.append(CapitalizationFeatureAnalyzer.label(token.text))

                if tweet_idx % 1000 == 0 and tweet_idx != 0:
                    capitalization_model.train(capitalization_data, capitalization_labels, epochs=1)
                    capitalization_data = []
                    capitalization_labels = []

    # Finish training capitalization data
    if args.train_capitalization:
        if len(capitalization_data) > 0:
            capitalization_model.train(capitalization_data, capitalization_labels, epochs=1)

    print("%f%%" % 100.)

    print("Saving Models...")
    if args.train_words:
        markov_db.save(MARKOV_DB_PATH)
    if args.train_capitalization:
        capitalization_model.save(CAPITALIZATION_MODEL_PATH)
    if args.train_pos:
        postree_db.update_probabilities()
        postree_db.save(POSTREE_DB_PATH)

    print("Done.")

