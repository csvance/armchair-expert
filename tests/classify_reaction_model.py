from reaction_model import *

classify = ['roflcopter', 'wat', 'lol', 'haha', 'llooolololo', 'oh hi mark', 'llllll', 'oooooo', 'wwwwtttt',
            ':laughing:', ':grinning:', ':smile:', ':satisfied:', ':smiley:', ':sweat_smile:',
            ':joy_cat:', ':joy:']

predictor = AOLReactionModelPredictor(saved_model_dir='models/aol-reaction-model/1510632114')
for idx, word in enumerate(classify):
    print("%s - %s" % (predictor.predict(word)[0] ,classify[idx]))