from reaction_model import *
from config import *

classify = ['roflcopter', 'wat', 'lol', 'haha', 'llooolololo', 'oh hi mark', 'llllll', 'oooooo', 'wwwwtttt',
            ':laughing:', '😂', '😁', '😊', '😁', '😃', '😄', '😹', '🤣']

predictor = AOLReactionModel(path=CONFIG_MARKOV_REACTION_PREDICT_MODEL_PATH)
for idx, word in enumerate(classify):
    target = classify[idx]
    prediction = predictor.predict(word)
    print("%s - %s" % (prediction, target))
