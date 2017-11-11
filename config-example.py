CONFIG_DISCORD_TOKEN = "asdASDASDasdaSDasd.aSDASDasD.ASDasdASdASD"
CONFIG_DISCORD_OWNER = "BigBoss#8527"
CONFIG_DISCORD_ME = "FTBot#3537"
CONFIG_DISCORD_MENTION_ME = "<@202194719466455040>"
CONFIG_DISCORD_IGNORE_CHANNELS = ['nsfw']
CONFIG_DISCORD_ALWAYS_REPLY = ['Blah#3861']
CONFIG_DISCORD_CLIENT_ID = 9045670782345898773

CONFIG_DEFAULT_REPLYRATE = 0
CONFIG_COMMAND_TOKEN = "!"

CONFIG_DATABASE_MYSQL = 1
CONFIG_DATABASE_SQLITE = 2

CONFIG_DATABASE = CONFIG_DATABASE_MYSQL

#CONFIG_DATABASE_CONNECT = 'sqlite:///markov.db'
CONFIG_DATABASE_CONNECT = 'mysql+pymysql://root@localhost/markov?charset=utf8mb4'

# Markov configuration settings, don't mess with this unless you know what you are doing
CONFIG_MARKOV_VECTOR_LENGTH = 7
CONFIG_MARKOV_URL_CHANCE = 10
CONFIG_MARKOV_WEIGHT_NEIGHBOR = 50
CONFIG_MARKOV_WEIGHT_RELATION = 20
CONFIG_MARKOV_WEIGHT_WORDCOUNT = 0
CONFIG_MARKOV_GENERATE_LIMIT = 20

# Limits maximum complexity of neighborhood relations to n*n
CONFIG_MARKOV_NEIGHBORHOOD_SENTENCE_SIZE_CHUNK = 8
CONFIG_MARKOV_NEIGHBORHOOD_SENTENCE_POS_ACCEPT = ['NOUN', 'VERB', 'ADJ', 'ADV', 'X', 'EMOJI']

# One of these
CONFIG_MARKOV_TOPIC_SELECTION_POS = ['NOUN', 'VERB', 'X', 'EMOJI']

# Not one of these
CONFIG_MARKOV_TOPIC_SELECTION_FILTER = ['#nick', 'and', 'for', 'what', 'where', 'when', 'how', 'who', 'now', 'be', 'is',
                                        'or',
                                        'the', 'you', 'your', 'we', 'i', 'to', 'too', 'are', 'do', 'don\'t', 'what\'s',
                                        'whats',
                                        'just', 'with', 'its', 'his', 'her', 'it', 'it\'s', 'that', 'thats', 'my']

# Used for one word reaction analysis, is the person responding to our message in a good way?
CONFIG_MARKOV_REACTION_EMOJIS = [':laughing:', ':grinning:', ':smile:', ':satisfied:', ':smiley:', ':sweat_smile:',
                                 ':joy_cat:', ':joy:']
CONFIG_MARKOV_REACTION_CHARS = ['lo', 'wtf', 'lmao', 'ha', 'rekt', 'rofl', 'omg']
CONFIG_MARKOV_REACTION_TIMEDELTA_S = 10
CONFIG_MARKOV_REACTION_SCORE_POS = ['NOUN', 'VERB', 'ADJ', 'ADV', 'X', 'EMOJI']
CONFIG_MARKOV_REACTION_UPRATE_WORD = 1
CONFIG_MARKOV_REACTION_UPRATE_RELATION = 5
CONFIG_MARKOV_REACTION_UPRATE_NEIGHBOR = 1

CONFIG_MESSAGE_WAKEUP = "Yawn"
CONFIG_MESSAGE_SHUTUP = "ZzZzZzZz"