# About
armchair-expert is a chatbot inspired by old Markov chain IRC bots like PyBorg. It regurgitates what it learns from you in unintentionally hilarious ways.

## Features
- Uses NLP to select the most optimal subjects for which to generate a response
- Learns new words in realtime like a typical Markov chain, but uses an RNN to structure and capitalize the output
- Uses an n-gram markov chain which is positionally aware of the distances between different words, creating a more coherent sentence

## Requirements
- python 3.6+
- keras (Tensorflow backend)
- spaCy 2.0.0+
- spacymoji
- numpy
- tweepy
- discord.py
- sqlalchemy

## Setup & Training
- Copy config/armchair_expert.example.py to config/armchair_expert.py
- Copy config/ml.example.py to config/ml.py
- Make sure you have the spacy 'en' dataset downloaded: 'python -m spacy download en'
- I would suggest import some data for training before starting the bot. Here is one example: https://github.com/csvance/armchair-expert/blob/master/scripts/import_text_file.py
- Every time the bot starts it will train on all new data it acquired since it started up last

# Connectors
## Twitter
- You will need to create an application on the twitter devleoper site on your bot's twitter account https://apps.twitter.com
- After creating it, assign it permissions to do direct messages (this isn't default)
- Create an access token for your account
- Copy twitter.example.py to twitter.py
- Fill in the tokens and secrets along with your handle
- python armchair_expert.py

## Discord
- You will need to register a bot with Discord: https://discordapp.com/developers/applications/me#top
- Once you register it take note of the Client ID, Username, and Token
- Copy discord.example.py to discord.py and fill in the relevant fields
- python armchair_expert.py
- When the bot starts you should see a message print to the console containing a link which will allow you to join the bot to a server.
