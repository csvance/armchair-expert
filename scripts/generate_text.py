import time

import numpy as np
from markov_engine import MarkovTrieDb, MarkovGenerator, MarkovFilters
from config.ml import MARKOV_DB_PATH, STRUCTURE_MODEL_PATH, USE_GPU
from models.structure import StructureModelScheduler
from common.nlp import CapitalizationMode


def main():
    np.random.seed(int(time.time()))

    markov_db = MarkovTrieDb(MARKOV_DB_PATH)

    structure_model = StructureModelScheduler(use_gpu=USE_GPU)
    structure_model.start()
    structure_model.load(STRUCTURE_MODEL_PATH)

    subjects = []
    for word in ['Some', 'Words', 'Here']:
        select_word = markov_db.select(word)
        if select_word is not None:
            subjects.append(select_word)
        else:
            print("Couldn't select %s" % word)

    for i in range(0, 1000):

        def structure_generator():
            while True:
                yield structure_model.predict(num_sentences=1)

        markov_generator = MarkovGenerator(structure_generator(), subjects)

        words = []
        sentences = markov_generator.generate(markov_db)
        if sentences is None:
            continue

        for sentence_idx, sentence in enumerate(sentences):
            pos_list = [word.pos for word in sentence]
            for word_idx, word in enumerate(sentence):
                if not word.compound:
                    text = CapitalizationMode.transform(word.mode, sentences[sentence_idx][word_idx].text, )
                else:
                    text = word.text
                words.append(text)

        message = " ".join(words)
        message = MarkovFilters.smooth_output(message)

        print(message)


if __name__ == "__main__":
    main()
