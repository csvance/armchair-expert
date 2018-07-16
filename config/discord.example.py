class DiscordApiCredentials(object):
    def __init__(self, token: str):
        self.token = token


# --- "User" Stuff Section ---
# ----------------------------

DISCORD_CLIENT_ID = 12345678901234567890
DISCORD_TOKEN = ''

DISCORD_CREDENTIALS = DiscordApiCredentials(token=DISCORD_TOKEN)

DISCORD_USERNAME = 'SomeBot#1234'

# Learn from all servers and channels
DISCORD_LEARN_FROM_ALL = False

# Don't learn from any of these channels
DISCORD_LEARN_CHANNEL_EXCEPTIONS = []

# Learn from direct messages
DISCORD_LEARN_FROM_DIRECT_MESSAGE = False

# Always learn from a specific user no matter what other flags are set
# This should be set to a string containing a username like "SomeGuy#1234"
DISCORD_LEARN_FROM_USER = None

# --- Technical Stuff Section ---
# -------------------------------

DISCORD_REMOVE_URL = True

# Store training data here
DISCORD_TRAINING_DB_PATH = 'db/discord.db'
