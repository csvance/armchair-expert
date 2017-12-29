import argparse
import sys
from multiprocessing import Process

from spacy.tokens import Doc

from markov_engine import MarkovTrainer, MarkovTrieDb
from ml_common import pickle_load
from config.ml_config import MARKOV_DB_PATH, STRUCTURE_MODEL_PATH, USE_GPU
from nlp_common import create_nlp_instance
from models.structure import StructureModelScheduler


def train_structure(*arg):
    epochs = arg[0]

    print("Training Sentence Structure...")
    structure_scheduler = StructureModelScheduler(use_gpu=USE_GPU)
    structure_scheduler.start()

    capitalization_data = pickle_load('structure_data')
    capitalization_labels = pickle_load('structure_labels')

    structure_scheduler.train(capitalization_data, capitalization_labels, epochs=epochs)
    structure_scheduler.save(STRUCTURE_MODEL_PATH)
    structure_scheduler.shutdown()

    print("Sentence Structure Training Done.")


def train_words():
    print("Training Words...")

    markov_db = MarkovTrieDb()
    markov_trainer = MarkovTrainer(markov_db)

    nlp = create_nlp_instance()

    docs = pickle_load('word_docs')

    for doc_bytes in docs:
        doc = Doc(nlp.vocab)
        markov_trainer.learn(doc.from_bytes(doc_bytes))

    markov_db.save(MARKOV_DB_PATH)
    print("Word Training Done")


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--words', help='train words', action='store_true')
    parser.add_argument('--structure', help='train sentence structure', action='store_true')
    parser.add_argument('--structure-epochs', help='number of sentence structure training epochs', type=int, default=1)
    args = parser.parse_args()

    if not (args.words or args.structure):
        print("Error: must preprocess something.")
        print("Set one or more flags")
        sys.exit(-1)

    processes = []
    if args.words:
        word_process = Process(target=train_words)
        word_process.start()
        processes.append(word_process)

    if args.structure:
        structure_process = Process(target=train_structure, args=(args.structure_epochs,))
        structure_process.start()
        processes.append(structure_process)

    for process in processes:
        process.join()

    print("Training All Done!")
