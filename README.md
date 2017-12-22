# Warning
This branch is a complete refactoring of armchair-expert and is in no way complete or stable!

## About
Armchair Expert is a chatbot for Discord inspired by old Markov chain IRC bots like PyBorg. It regurgitates what it learns from you in unintentionally hilarious ways. 

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

# Backends
## Discord
- You will need to register a bot with Discord: https://discordapp.com/developers/applications/me#top
- Once you register it take note of the Client ID, Username, Bot ID, and Token
- Copy discord-config.example.py to discord-config.py and configure it
- python armchair_expert.py
- When the bot starts you should see a message print to the console containing a link which will allow you to join the bot to a server.
