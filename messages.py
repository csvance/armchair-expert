import random
import re
from typing import Optional
from pos_tree_model import PosTreeModel
import discord
from sqlalchemy import and_
import time

from markov_schema import *


class MessageBase(object):
    def __init__(self, message: discord.Message = None, line: Line = None, text: str = None, people: list = None):
        # Class Data
        self.message = message
        self.line = line
        self.message_raw = None
        self.message_filtered = None
        self.args = {}
        self.tokens = []
        self.people = people
        self.loaded = False
        self.processed = False

        # Create args based on the type of message
        if text:
            self.message_raw = text
            self.args_from_text(text)
        elif line:
            self.message_raw = line.text
            self.args_from_line(line)
        elif message:
            self.message_raw = message.content
            self.args_from_message(message)
        else:
            raise ValueError('text, line, and message cannot be None')

    # noinspection PyUnusedLocal
    def args_from_text(self, text: str) -> None:
        self.args = {'learning': True, 'mentioned': False, 'channel': None, 'server': None, 'author': 'text_loader',
                     'always_reply': False, 'author_mention': None, 'timestamp': datetime.datetime.now()}

    # From line db table. Only called when rebuilding the database
    def args_from_line(self, line: Line) -> None:
        self.args = {'timestamp': line.timestamp, 'channel': line.channel,
                     'server': line.server_id, 'author': line.author, 'always_reply': False,
                     'mentioned': False, 'author_mention': None, 'learning': True}

    # From discord client
    def args_from_message(self, message: discord.Message) -> None:

        # Check for Private Message
        try:
            server = message.channel.server.id
        except AttributeError:
            server = None

        self.args = {'channel': message.channel,
                     'author': str(message.author),
                     'author_mention': "<@%s>" % message.author.id,
                     'server': server,
                     'always_reply': False,
                     'timestamp': message.timestamp}

        # Fill in the rest of the flags based on the raw content
        if message.content.lower().find(CONFIG_DISCORD_ME_SHORT.lower()) != -1:
            self.args['mentioned'] = True
        else:
            self.args['mentioned'] = False

        if str(message.author) == CONFIG_DISCORD_OWNER:
            self.args['is_owner'] = True
        else:
            self.args['is_owner'] = False

        if self.args['author'] in CONFIG_DISCORD_ALWAYS_REPLY:
            self.args['always_reply'] = True

        # Don't learn from private messages or ourself
        if CONFIG_LEARNING_ENABLE and message.server is not None and str(self.args['author']) != CONFIG_DISCORD_ME:
            self.args['learning'] = True
        else:
            self.args['learning'] = False

    def filter(self, raw_message: str) -> str:
        pass

    def process(self, nlp) -> None:

        if not self.processed:

            # Filter
            self.message_filtered = self.filter(self.message_raw)

            # Tokenize
            message_nlp = nlp(self.message_filtered)
            for token in message_nlp:
                self.tokens.append({'nlp': token})

            self.processed = True

    def load_pos(self, session, nlp) -> None:
        for token in self.tokens:

            # TODO: Implement entity dection in spacy
            custom_pos = PosTreeModel.custom_pos_from_word(token['nlp'].text, people=self.people, is_emoji=token['nlp']._.is_emoji)
            pos_text = custom_pos if custom_pos is not None else token['nlp'].pos_

            pos = session.query(Pos).filter(Pos.text == pos_text).first()
            if pos is None:
                pos = Pos(text=pos_text)
                session.add(pos)
                session.flush()
            token['pos'] = pos

    def load_words(self, session) -> None:

        words = []

        word_b = None
        for token_index, token in enumerate(self.tokens):

            if not word_b:
                word_a = session.query(Word).filter(Word.text == token['nlp'].text).first()
                if word_a is None:
                    word_a = Word(text=token['nlp'].text, pos_id=token['pos'].id)
                    session.add(word_a)
                    session.flush()
            else:
                word_a = word_b
            token['word'] = word_a

            # If we are on the last word, there is no word b or a->b relationship
            if token_index >= len(self.tokens) - 1:
                token['word_a->b'] = None
                break

            word_b = session.query(Word).filter(
                Word.text == self.tokens[token_index + 1]['nlp'].text).first()
            if word_b is None:
                word_b = Word(text=self.tokens[token_index + 1]['nlp'].text, pos_id=self.tokens[token_index + 1]['pos'].id)
                session.add(word_b)
                session.flush()
            self.tokens[token_index + 1]['word'] = word_b

            if word_a.id == word_b.id:
                continue

            word_a_b = session.query(WordRelation).filter(
                and_(WordRelation.a_id == word_a.id, WordRelation.b_id == word_b.id)).first()
            if word_a_b is None:
                word_a_b = WordRelation(a_id=word_a.id, b_id=word_b.id)
                session.add(word_a_b)
                session.flush()
            token['word_a->b'] = word_a_b

    def load_neighbors(self, session) -> None:

        for token_index, token in enumerate(self.tokens):

            token['word_neighbors'] = []

            # Filter things that are not relevant to the main information in a sentence
            if token['pos'].text not in CONFIG_MARKOV_NEIGHBORHOOD_POS_ACCEPT:
                continue

            for neighbor_index, potential_neighbor in enumerate(self.tokens):

                # A word cannot be a neighbor with itself either (case == 0)
                # We don't care if a word is right next to another as WordRelation already tracks that (case == 1)
                # We don't care if a word is outside the window (case <= CONFIG_MARKOV_NEIGHBORHOOD_WINDOW_SIZE)
                if abs(token_index - neighbor_index) > 1 and abs(
                                token_index - neighbor_index) <= CONFIG_MARKOV_NEIGHBORHOOD_WINDOW_SIZE:

                    if potential_neighbor['pos'].text \
                            not in CONFIG_MARKOV_NEIGHBORHOOD_POS_ACCEPT:
                        continue

                    if token['word'].id == potential_neighbor['word'].id:
                        continue

                    neighbor = session.query(WordNeighbor). \
                        join(Word, WordNeighbor.b_id == Word.id). \
                        filter(and_(WordNeighbor.a_id == token['word'].id,
                                    Word.id == potential_neighbor['word'].id)).first()

                    if neighbor is None:
                        neighbor = WordNeighbor(a_id=token['word'].id, b_id=potential_neighbor['word'].id)
                        session.add(neighbor)
                        session.flush()

                    token['word_neighbors'].append(neighbor)

    # Called when ORM objects are needed
    def load(self, session, nlp) -> None:
        if not self.loaded:

            self.process(nlp)
            self.load_pos(session, nlp)
            self.load_words(session)
            self.load_neighbors(session)
            session.commit()
            self.loaded = True


# A message from the bot
class MessageOutput(MessageBase):
    # message is just a string, not a discord message object
    def __init__(self, line: Line = None, text: str = None):
        MessageBase.__init__(self, line=line, text=text)

    def filter(self, raw_message: str) -> str:

        message = raw_message
        message = re.sub(' ([,.!?:;"“\'])', r'\1', message)
        message = re.sub('([#@“"\']) ', r'\1', message)
        message = re.sub(' ([-_]) ', r'\1', message)

        return message


# A message received from discord, loaded from the database line table, or from raw text
class MessageInput(MessageBase):
    # message is a discord message object
    # line is a orm object for the line table
    def __init__(self, message: discord.Message = None, line: Line = None, text: str = None, people: list = None):
        MessageBase.__init__(self, message=message, line=line, text=text, people=people)

    def filter(self, raw_message: str) -> str:
        message = raw_message

        # Extract URLs
        self.args['url'] = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                                      message)

        # Remove URLs
        message = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '',
                         message)

        # Convert everything to lowercase
        if not CONFIG_MARKOV_PRESERVE_CASE:
            message = message.lower()

        # Replace HTML symbols
        message = message.replace('&amp;','&')

        # Strip out characters which pollute the database with useless information for our purposes
        message = re.sub(CONFIG_MARKOV_SYMBOL_STRIP, "", message)

        return message


class MessageInputCommand(MessageInput):
    def __init__(self, message: discord.Message = None, line=None, text=None, people: list = None):
        MessageInput.__init__(self, message=message, line=line, text=text, people=people)
