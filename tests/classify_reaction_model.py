from reaction_model import *
from config import *

classify = ['roflcopter', 'wat', 'lol', 'haha', 'llooolololo', 'oh hi mark', 'llllll', 'oooooo', 'wwwwtttt',
            ':laughing:', '😂', '😁', '😊', '😁', '😃', '😄', '😹', '🤣']

predictor = AOLReactionModelPredictor(saved_model_dir=CONFIG_MARKOV_REACTION_PREDICT_MODEL_PATH)
for idx, word in enumerate(classify):
    print("%s - %s" % (int(predictor.predict(word)[0][0]), classify[idx]))