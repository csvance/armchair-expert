from common.nlp import Pos

# --- "User" Stuff Section ---
# ----------------------------

USE_GPU = True

# --- Technical Stuff Section ---
# -------------------------------

# Paths
MARKOV_DB_PATH = 'weights/markov.json.zlib'
REACTION_MODEL_PATH = "weights/aol-reaction-model.h5"
STRUCTURE_MODEL_PATH = "weights/structure-model.h5"

MARKOV_GENERATE_SUBJECT_MAX = 2
# Greatest to least
MARKOV_GENERATE_SUBJECT_POS_PRIORITY = [Pos.HASHTAG, Pos.PROPN, Pos.NOUN, Pos.VERB, Pos.EMOJI, Pos.URL, Pos.ADJ,
                                        Pos.ADV, Pos.NUM, Pos.X, Pos.INTJ]

# Weights for generating replies
MARKOV_GENERATION_WEIGHT_COUNT = 1
MARKOV_GENERATION_WEIGHT_RATING = 10

# bi-gram window function size
MARKOV_WINDOW_SIZE = 4

# These should always be marked as a "compound" word which will always use its original capitalization
CAPITALIZATION_COMPOUND_RULES = ['RT']

# Maximum number of sequences to train the structure model on
STRUCTURE_MODEL_TRAINING_MAX_SIZE = 250000

# Lower values make things more predictable, higher ones more random
STRUCTURE_MODEL_TEMPERATURE = 0.7
MARKOV_MODEL_TEMPERATURE = 0.7
