# About
Inspired by old IRC bots that created a markov chain from chat text, regurgitating it back in unintentionally hilarious ways.

# Features
- Uses NLP to classify words, allowing for more accurate topic selection
- Uses several factors to when learning to generate output, including markov A->B relationships and whether a word is used together with another in a sentence
- Capable of determining when people react with extreme AOL speak, upranking words and A->B relationships that cause reactions
- Seperate markov chain for POS relationships
- Uses scoring system with linear distribution when selecting choices

# Requirements
- python 3.6

# Dependencies
- sqlalchemy
- discord.py
- googleapiclient
- wand (imagemagick)
- schedule
- numpy
- spacy (Uses 'en' dataset by default, you will need to download this in addition to installing spacy: 'python -m spacy download en')

# Configuration

Copy config-example.py to config.py and fill in the fields. You will need to register with Google Custom Search to get a CX and developer key.
You will need to register a bot with Discord: https://discordapp.com/developers/applications/me#top
Convert the application to a bot account to get your token. After that you will need to join it to your guild using OAuth2
Take the client id of your application and fill in this link to join it: https://discordapp.com/oauth2/authorize?client_id=CLIENT_ID_GOES_HERE&scope=bot&permissions=0

# Run It
python ftbot_discord.py
