from nlp_common import PosEnum

# --- "User" Stuff Section ---
# ----------------------------

USE_GPU = True

# --- Technical Stuff Section ---
# -------------------------------

# Paths
MARKOV_DB_PATH = 'models/markov.json.zlib'
POSTREE_DB_PATH = 'models/pos-tree.json.zlib'
REACTION_MODEL_PATH = "models/aol-reaction-model.h5"
CAPITALIZATION_MODEL_PATH = "models/capitalization-model.h5"

MARKOV_GENERATE_SUBJECT_MAX = 2
# Greatest to least
MARKOV_GENERATE_SUBJECT_POS_PRIORITY = [PosEnum.HASHTAG, PosEnum.PROPN, PosEnum.NOUN, PosEnum.VERB, PosEnum.EMOJI, PosEnum.URL, PosEnum.ADJ, PosEnum.ADV]

# Weights for generating replies
MARKOV_GENERATION_WEIGHT_COUNT = 1
MARKOV_GENERATION_WEIGHT_RATING = 10

# bi-gram window function size
MARKOV_WINDOW_SIZE = 4

