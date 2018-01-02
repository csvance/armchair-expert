class TwitterApiCredentials(object):
    def __init__(self, consumer_key: str, consumer_secret, access_token: str, access_token_secret: str):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret

# --- "User" Stuff Section ---
# ----------------------------

TWITTER_CONSUMER_KEY = ""
TWITTER_CONSUMER_SECRET = ""
TWITTER_ACCESS_TOKEN = ""
TWITTER_ACCESS_TOKEN_SECRET = ""

TWITTER_CREDENTIALS = TwitterApiCredentials(consumer_key=TWITTER_CONSUMER_KEY, consumer_secret=TWITTER_CONSUMER_SECRET,
                                            access_token=TWITTER_ACCESS_TOKEN,
                                            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET)

TWITTER_SCREEN_NAME = 'Sundial_o7'

# Learn everything in our user timeline
TWITTER_LEARN_TIMELINE = False

# Learn from a specific user
TWITTER_LEARN_FROM_USER = None

# Learn from that users retweets?
TWITTER_LEARN_FROM_USER_RETWEETS = False

# Reply to mentions
TWITTER_REPLY_MENTIONS = True

# Reply to anything on timeline
TWITTER_REPLY_TIMELINE = False


# --- Technical Stuff Section ---
# -------------------------------

# Remove learned URL from replies
TWITTER_REMOVE_URL = True

# Store training data here
TWITTER_TRAINING_DB_PATH = 'db/twitter.db'

# In seconds
TWITTER_SCRAPE_FREQUENCY = 900
