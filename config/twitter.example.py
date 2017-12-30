class TwitterApiCredentials(object):
    def __init__(self, consumer_key: str, consumer_secret, access_token: str, access_token_secret: str):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret

# --- "User" Stuff Section ---
# ----------------------------

CONSUMER_KEY = ""
CONSUMER_SECRET = ""
ACCESS_TOKEN = ""
ACCESS_TOKEN_SECRET = ""

TWITTER_CREDENTIALS = TwitterApiCredentials(consumer_key=CONSUMER_KEY, consumer_secret=CONSUMER_SECRET,
                                            access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET)

SCREEN_NAME = 'Sundial_o7'

# --- Technical Stuff Section ---
# -------------------------------
