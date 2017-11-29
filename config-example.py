CONFIG_DISCORD_TOKEN = "asdASDASDasdaSDasd.aSDASDasD.ASDasdASdASD"
CONFIG_DISCORD_OWNER = "BigBoss#8527"
CONFIG_DISCORD_ME = "ArmchairExpert#3953"
CONFIG_DISCORD_ME_SHORT = CONFIG_DISCORD_ME.split("#")[0]
CONFIG_DISCORD_BOTID = 378934517299413004

# Ignore all text from these channels
CONFIG_DISCORD_IGNORE_CHANNELS = ['nsfw']

# Set this to someones nick in the format of ['User#1344'] to always reply to them
CONFIG_DISCORD_ALWAYS_REPLY = []

# Prefix for all commands, such as !wakeup, !shutup, !essay, etc
CONFIG_COMMAND_TOKEN = "!"

# Mini Me Mode. Set this to someones nick in the format of ['User#1344'] to only learn from those users
CONFIG_DISCORD_MINI_ME = None

# How often to randomly reply to messages
CONFIG_DEFAULT_REPLYRATE = 1

# !wakeup acknowledgement
CONFIG_MESSAGE_WAKEUP = "Yawn"
# !shutup acknowledgement
CONFIG_MESSAGE_SHUTUP = "ZzZzZzZz"

# Whether the bot continuosly learns or not.
# Regardless of this setting, the bot will record lines in the database
CONFIG_LEARNING_ENABLE = True

CONFIG_DATABASE_MYSQL = 1
CONFIG_DATABASE_SQLITE = 2

CONFIG_DATABASE = CONFIG_DATABASE_MYSQL

if CONFIG_DATABASE == CONFIG_DATABASE_MYSQL:
    CONFIG_DATABASE_CONNECT = 'mysql+pymysql://root@localhost/markov?charset=utf8mb4'
else:
    CONFIG_DATABASE_CONNECT = 'sqlite:///markov.db'

# Only enable this if you built TensorFlow with GPU support
CONFIG_USE_GPU = False

# List of users on all servers. Used for enhanced PoS detection.
CONFIG_DISCORD_MEMBERS = []

# If this is true, don't care about word relationships to continue a sentence if non are available
CONFIG_MARKOV_FALLBACK_RANDOM = False

# Markov configuration settings, don't mess with this unless you know what you are doing
CONFIG_MARKOV_DEBUG = False
CONFIG_DATABASE_DEBUG = False

# Chance to reply with a random URL
CONFIG_MARKOV_URL_CHANCE = 10

# Reply generation weights.
# Weigh neighbor higher for more topical replies
# Weigh relation higher for more random ones
CONFIG_MARKOV_WEIGHT_NEIGHBOR = 50
CONFIG_MARKOV_WEIGHT_RELATION = 20
CONFIG_MARKOV_WEIGHT_WORDCOUNT = 0

# Max number of rows to return when looking for next word in reply chain
CONFIG_MARKOV_GENERATE_LIMIT = 20

# Filter these symbols from sentences
CONFIG_MARKOV_SYMBOL_STRIP = r'\'|“|"\(|\)|\[|\]|{|}|%|\^|&|\*|\\|/|&amp;'

# Preserve case of input text
# This means the first occurance of a word will freeze its capitalization for all future usages
CONFIG_MARKOV_PRESERVE_CASE = True

CONFIG_MARKOV_NEIGHBORHOOD_WINDOW_SIZE = 4

# Only include words of these types in the window
CONFIG_MARKOV_NEIGHBORHOOD_POS_ACCEPT = ['NOUN', 'VERB', 'ADJ', 'ADP' 'ADV', 'X', 'EMOJI', 'HASHTAG']

# Prioritize these PoS for the topic selection of replies
CONFIG_MARKOV_TOPIC_SELECTION_POS = ['NOUN', 'VERB', 'X', 'EMOJI', 'HASHTAG']

# User Reaction Options
CONFIG_MARKOV_REACTION_TIMEDELTA_S = 10
CONFIG_MARKOV_REACTION_SCORE_POS = ['NOUN', 'VERB', 'ADJ', 'ADV', 'X', 'EMOJI']
CONFIG_MARKOV_REACTION_UPRATE_WORD = 1
CONFIG_MARKOV_REACTION_UPRATE_RELATION = 5
CONFIG_MARKOV_REACTION_UPRATE_NEIGHBOR = 1
CONFIG_MARKOV_REACTION_PREDICT_MODEL_PATH = "models/aol-reaction-model.h5"

CONFIG_POS_TREE_PATH = "models/pos-tree-model.json"

CONFIG_CAPITALIZATION_MODEL_PATH = "models/capitalization-model.h5"
CONFIG_CAPITALIZATION_TRANSFORM_IGNORE_PREFIX = r'^(@|#)'
