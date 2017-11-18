CONFIG_DISCORD_TOKEN = "asdASDASDasdaSDasd.aSDASDasD.ASDasdASdASD"
CONFIG_DISCORD_OWNER = "BigBoss#8527"
CONFIG_DISCORD_ME = "ArmchairExpert#3953"
CONFIG_DISCORD_ME_SHORT = CONFIG_DISCORD_ME.split("#")[0]
CONFIG_DISCORD_BOTID = 378934517299413004
CONFIG_DISCORD_IGNORE_CHANNELS = ['nsfw']
CONFIG_DISCORD_ALWAYS_REPLY = ['Blah#3861']

# Mini Me Mode. Set this to someones nick in the format of ['User#1344'] to only learn from that user.
CONFIG_DISCORD_MINI_ME = None

CONFIG_DEFAULT_REPLYRATE = 0
CONFIG_COMMAND_TOKEN = "!"
CONFIG_LEARNING_ENABLE = True
CONFIG_USE_GPU = False

CONFIG_DATABASE_MYSQL = 1
CONFIG_DATABASE_SQLITE = 2

CONFIG_DATABASE = CONFIG_DATABASE_MYSQL

if CONFIG_DATABASE == CONFIG_DATABASE_MYSQL:
    CONFIG_DATABASE_CONNECT = 'mysql+pymysql://root@localhost/markov?charset=utf8mb4'
else:
    CONFIG_DATABASE_CONNECT = 'sqlite:///markov.db'

CONFIG_MESSAGE_WAKEUP = "Yawn"
CONFIG_MESSAGE_SHUTUP = "ZzZzZzZz"

# List of users on all servers. Used for enhanced PoS detection.
CONFIG_DISCORD_MEMBERS = []

# If this is true, don't care about word relationships to continue a sentence if non are available
CONFIG_MARKOV_FALLBACK_RANDOM = False

# Markov configuration settings, don't mess with this unless you know what you are doing
CONFIG_MARKOV_DEBUG = False
CONFIG_DATABASE_DEBUG = False

CONFIG_MARKOV_URL_CHANCE = 10
CONFIG_MARKOV_WEIGHT_NEIGHBOR = 50
CONFIG_MARKOV_WEIGHT_RELATION = 20
CONFIG_MARKOV_WEIGHT_WORDCOUNT = 0
CONFIG_MARKOV_GENERATE_LIMIT = 20

CONFIG_MARKOV_SENTENCE_GROUP_SPLIT = r'[;.!?]'
CONFIG_MARKOV_SYMBOL_STRIP = r'\'|“|"\(|\)|\[|\]|{|}|%|\^|&|\*|\\|/'

CONFIG_MARKOV_NEIGHBORHOOD_WINDOW_SIZE = 4
CONFIG_MARKOV_PRESERVE_CASE = True

CONFIG_MARKOV_NEIGHBORHOOD_POS_ACCEPT = ['NOUN', 'VERB', 'ADJ', 'ADP' 'ADV', 'X', 'EMOJI']

# One of these
CONFIG_MARKOV_TOPIC_SELECTION_POS = ['NOUN', 'VERB', 'X', 'EMOJI']

# Not one of these
CONFIG_MARKOV_TOPIC_SELECTION_FILTER = ['#nick', 'and', 'for', 'what', 'where', 'when', 'how', 'who', 'now', 'be', 'is',
                                        'or',
                                        'the', 'you', 'your', 'we', 'i', 'to', 'too', 'are', 'do', 'don\'t', 'what\'s',
                                        'whats',
                                        'just', 'with', 'its', 'his', 'her', 'it', 'it\'s', 'that', 'thats', 'my']


CONFIG_MARKOV_REACTION_TIMEDELTA_S = 10
CONFIG_MARKOV_REACTION_SCORE_POS = ['NOUN', 'VERB', 'ADJ', 'ADV', 'X', 'EMOJI']
CONFIG_MARKOV_REACTION_UPRATE_WORD = 1
CONFIG_MARKOV_REACTION_UPRATE_RELATION = 5
CONFIG_MARKOV_REACTION_UPRATE_NEIGHBOR = 1
CONFIG_MARKOV_REACTION_TRAINING_MODEL_PATH = "models/aol-reaction-model/"
CONFIG_MARKOV_REACTION_PREDICT_MODEL_PATH = "models/aol-reaction-model/1510966239"

CONFIG_POS_TREE_CONFIG_PATH = "models/pos-tree-model.json"