## About
Armchair Expert is a chatbot for Discord inspired by old Markov chain IRC bots like PyBorg. It regurgitates what it learns from you in unintentionally hilarious ways. 

## Features
- Learns from Discord chat and replies randomly or when mentioned, relating what it has learned to your message.
- NLP assisted topic selection. When choosing a subject in a sentence to reply to, undesirable parts of speech such as pronouns and conjunctions are ignored.
- In addition to an A->B word embedding system with a Markov Decision Process, words farther than one away are also embedded using a window function.
- Analyzes reactions to fuel reinforcement learning, making word combinations that are funny appear more often. Supports both text based "AOL speak" and emoji reactions.
- Not only learns from word embeddings, but the sentence structures they imply using a probability tree structure.
- Can train capitalization patterns using machine learning to use when responding
- Can be set to immitate a specific user using MiniMeMode, creating an AI of them
- Writes entire essays with the !essay command

## Dependencies
- python 3.6
- spacy 2.0.0+
- spacymoji
- tensorflow 1.4
- sqlalchemy
- discord.py
- numpy
- pandas
- janus

## Database
Currently supports both MySQL and SQLite as DB backends. I recommend using MySQL as the performance is orders of magnitude better.
In theory you should be able to set it up with any modern RDBMS.
To properly support emoji in MySQL: create database armchairexpert CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

## Configuration
- You will need to register a bot with Discord: https://discordapp.com/developers/applications/me#top
- Once you register it take note of the Client ID, Username, Bot ID, and Token
- Copy config-example.py to config.py and fill in everything above the database connection string
- If using MySQL you will need to manually create the database and enter your connection string.
- Otherwise just select SQLite and use the included connection string for it.
- Make sure you have the spacy 'en' dataset downloaded: 'python -m spacy download en'

## Run It
- python armchair_expert_discord.py
- When the bot starts you should see a message print to the console containing a link which will allow you to join the bot to a server.



