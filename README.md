## About
Armchair Expert is a chatbot inspired by old Markov chain IRC bots like PyBorg. It regurgitates what it learns from you in unintentionally hilarious ways. 

## Features
- Learns from Discord chat and replies randomly or when mentioned, relating what it has learned to your message.
- NLP assisted topic selection. When choosing a subject in a sentence to reply to, undesirable parts of speech such as pronouns and conjunctions are ignored.
- Uses an n-gram markov chain which is positionally aware of the distances between different words
- Analyzes reactions to fuel reinforcement learning, making word combinations that are funny appear more often. Supports both text based "AOL speak" and emoji reactions.
- Learns to imitate capitalization patterns found in training data

## Dependencies
- python 3.6
- spacy 2.0.0+
- spacymoji
- tensorflow 1.4
- sqlalchemy
- discord.py
- numpy
- janus
- zlib

## General Setup
- Make sure you have the spacy 'en' dataset downloaded: 'python -m spacy download en'
- You will need to train armchair-expert with your data before using it (tweets, chatlogs, etc)
- An example of pre-processing input data and using it to train is in the scripts folder
- https://github.com/csvance/armchair-expert/blob/master/scripts/preprocess_data_twitter.py
- https://github.com/csvance/armchair-expert/blob/master/scripts/train_preprocessed_data.py

# Backends
## Twitter
- You will need to create an application on the twitter devleoper site on your bot's twitter account https://apps.twitter.com
- After creating it, assign it permissions to do direct messages (this isn't default)
- Create an access token for your account
- Copy twitter_config.example.py to twitter_config.py
- Fill in the tokens and secrets along with your handle
- python armchair_expert.py

## Discord
- **Not Implemented Yet**
- You will need to register a bot with Discord: https://discordapp.com/developers/applications/me#top
- Once you register it take note of the Client ID, Username, Bot ID, and Token
- Copy discord_config.example.py to discord_config.py and configure it
- python armchair_expert.py
- When the bot starts you should see a message print to the console containing a link which will allow you to join the bot to a server.

