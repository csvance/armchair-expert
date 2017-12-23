from markov_engine import MarkovTrieDb, MarkovGenerator, MarkovFilters
from ml_config import MARKOV_DB_PATH, POSTREE_DB_PATH, CAPITALIZATION_MODEL_PATH, USE_GPU
from capitalization_model import CapitalizationModelScheduler, CapitalizationModeEnum
from pos_tree_model import PosTreeModel
import numpy as np
import time

np.random.seed(int(time.time()))

markov_db = MarkovTrieDb(MARKOV_DB_PATH)
postree = PosTreeModel()
postree.load(POSTREE_DB_PATH)

capitalization_model = CapitalizationModelScheduler(use_gpu=USE_GPU)
capitalization_model.load(CAPITALIZATION_MODEL_PATH)
capitalization_model.start()

subjects = []
for word in ['Hillary','Great','#MAGA','🇺🇸']:
    select_word = markov_db.select(word)
    if select_word is not None:
        subjects.append(select_word)
    else:
        print("Couldn't select %s" % word)

for i in range(0, 1000):
    w = []
    structure = postree.generate_sentence(words=w)
    markov_generator = MarkovGenerator(structure,subjects)

    words = []
    sentences = markov_generator.generate(markov_db)
    if sentences is None:
        continue

    for sentence in sentences:
        for word_idx, word in enumerate(sentence):
            mode = capitalization_model.predict(word.text, word.pos, word_idx)
            text = CapitalizationModeEnum.transform(mode, word.text, ignore_prefix_regexp=r'[#@]')
            words.append(text)

    message = " ".join(words)
    message = MarkovFilters.smooth_output(message)

    print(message)


