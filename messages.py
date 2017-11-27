import re

import discord
from sqlalchemy import and_

from markov_schema import *
from pos_tree_model import PosTreeModel


class MessageArguments(object):
    def __init__(self, line=None, message=None, text=None):

        # Booleans
        self.always_reply = False
        self.is_owner = False
        self.mentioned = False
        self.author = None
        self.author_mention = None
        self.channel = None
        self.channel_str = None
        self.server = None
        self.server_id = None
        self.source = None
        self.learning = None
        self.timestamp = None

        if line:
            self.args_from_line(line)
        elif message:
            self.args_from_message(message)
        elif text:
            self.args_from_text(text)

    # noinspection PyUnusedLocal
    def args_from_text(self, text: str) -> None:
        self.learning = True
        self.mentioned = False
        self.channel = None
        self.channel_str = None
        self.server = None
        self.server_id = None
        self.author = 'text_loader'
        self.always_reply = False
        self.author_mention = None
        self.timestamp = datetime.datetime.now()

    # From line db table. Only called when rebuilding the database
    def args_from_line(self, line: Line) -> None:
        self.learning = True
        self.mentioned = False
        self.channel = None
        self.channel_str = line.channel
        self.server = None
        self.server_id = None
        if line.server_id is not None:
            self.server_id = int(line.server_id)
        self.author = line.author
        self.always_reply = False
        self.author_mention = None
        self.timestamp = datetime.datetime.now()

    # From discord client
    def args_from_message(self, message: discord.Message) -> None:

        # Check for Private Message
        try:
            server = message.channel.server
        except AttributeError:
            server = None

        self.channel = message.channel
        self.channel_str = str(message.channel)
        self.author = str(message.author)
        self.author_mention = "<@%s>" % message.author.id
        self.server = server
        self.server_id = server.id
        self.always_reply = False
        self.timestamp = message.timestamp

        # Fill in the rest of the flags based on the raw content
        if message.content.lower().find(CONFIG_DISCORD_ME_SHORT.lower()) != -1:
            self.mentioned = True
        else:
            self.mentioned = False

        if str(message.author) == CONFIG_DISCORD_OWNER:
            self.is_owner = True
        else:
            self.is_owner = False

        if self.author in CONFIG_DISCORD_ALWAYS_REPLY:
            self.always_reply = True

        # Don't learn from private messages or ourself
        if CONFIG_LEARNING_ENABLE and message.server is not None and str(self.author) != CONFIG_DISCORD_ME:
            self.learning = True
        else:
            self.learning = False


class MessageBase(object):
    def __init__(self, message: discord.Message = None, line: Line = None, text: str = None, people: list = None):
        # Class Data
        self.message = message
        self.line = line
        self.message_raw = None
        self.message_filtered = None
        self.tokens = []
        self.people = people
        self.loaded = False
        self.processed = False
        self.urls = []

        # Create args based on the type of message
        if text:
            self.message_raw = text
        elif line:
            self.message_raw = line.text
        elif message:
            self.message_raw = message.content
        else:
            raise ValueError('text, line, and message cannot be None')

        self.args = MessageArguments(message=message, line=line, text=text)

    def filter(self, raw_message: str) -> str:

        message = raw_message

        # Extract URLs
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                          message)

        # Validate URLs
        for url in urls:
            if len(url) <= MAX_URL_LENGTH:
                self.urls.append(url)

        # Remove URLs
        message = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '',
                         message)

        return message

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
        for token_idx, token in enumerate(self.tokens):

            # TODO: Implement entity dection in spacy
            custom_pos = PosTreeModel.custom_pos_from_word(token['nlp'].text, people=self.people,
                                                           is_emoji=token['nlp']._.is_emoji)
            pos_text = custom_pos if custom_pos is not None else token['nlp'].pos_

            pos = session.query(Pos).filter(Pos.text == pos_text).first()
            if pos is None:
                pos = Pos(text=pos_text)
                session.add(pos)
                session.flush()
            token['pos'] = pos

    def load_words(self, session) -> None:

        # Sanitizes word text input
        def token_text(t):
            if len(t['nlp'].text) > MAX_WORD_LENGTH:
                return t['nlp'].text[0:MAX_WORD_LENGTH]
            return t['nlp'].text

        words = []

        word_b = None
        for token_index, token in enumerate(self.tokens):

            if not word_b:
                word_a = session.query(Word).filter(Word.text == token_text(token)).first()
                if word_a is None:
                    word_a = Word(text=token_text(token), pos_id=token['pos'].id)
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
                Word.text == token_text(self.tokens[token_index + 1])).first()
            if word_b is None:
                word_b = Word(text=token_text(self.tokens[token_index + 1]),
                              pos_id=self.tokens[token_index + 1]['pos'].id)
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
        message = MessageBase.filter(self, raw_message)
        message = re.sub(' ([,.!?:;"“\'])', r'\1', message)
        message = re.sub('([#@“"\']) ', r'\1', message)
        message = re.sub(' ([-–_]) ', r'\1', message)

        return message


# A message received from discord, loaded from the database line table, or from raw text
class MessageInput(MessageBase):
    # message is a discord message object
    # line is a orm object for the line table
    def __init__(self, message: discord.Message = None, line: Line = None, text: str = None, people: list = None):
        MessageBase.__init__(self, message=message, line=line, text=text, people=people)

    def filter(self, raw_message: str) -> str:
        message = MessageBase.filter(self, raw_message)

        # Convert everything to lowercase
        if not CONFIG_MARKOV_PRESERVE_CASE:
            message = message.lower()

        # Strip out characters which pollute the database with useless information for our purposes
        message = re.sub(CONFIG_MARKOV_SYMBOL_STRIP, "", message)

        return message


class MessageInputCommand(MessageInput):
    def __init__(self, message: discord.Message = None, line=None, text=None, people: list = None):
        MessageInput.__init__(self, message=message, line=line, text=text, people=people)
