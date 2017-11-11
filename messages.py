import re
from typing import Optional

import discord
import emoji
import numpy as np
from sqlalchemy import and_

from markov_schema import *


class MessageBase(object):
    def __init__(self, message: discord.message.Message = None, line: Line = None, text: str = None):
        # Class Data
        self.message = message
        self.line = line
        self.message_raw = None
        self.message_filtered = None
        self.args = {}
        self.sentences = []

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

        self.process()

    # noinspection PyUnusedLocal
    def args_from_text(self, text: str) -> None:
        self.args = {'learning': True, 'mentioned': False, 'channel': None, 'server': None, 'author': 'text_loader',
                     'always_reply': False, 'author_mention': None, 'timestamp': datetime.datetime.now()}

    # From line db table. Only called when rebuilding the database
    def args_from_line(self, line):
        self.args = {'timestamp': line.timestamp, 'channel': line.channel,
                     'server': line.server_id, 'author': line.author, 'always_reply': False,
                     'mentioned': False, 'author_mention': None, 'learning': True}

    # From discord client
    def args_from_message(self, message: discord.message.Message) -> None:

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
        if message.content.find(CONFIG_DISCORD_MENTION_ME) != -1:
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
        if message.server is not None and str(self.args['author']) != CONFIG_DISCORD_ME:
            self.args['learning'] = True
        else:
            self.args['learning'] = False

    def filter_line(self, raw_message: str) -> str:
        pass

    # noinspection PyMethodMayBeStatic
    def process_word(self, word: str) -> Optional[dict]:

        if word == '':
            return None

        word_dict = {'word_text': word, 'pos': None}

        return word_dict

    def process_sentence(self, sentence) -> Optional[list]:

        filtered_words = []
        for word in sentence.split(" "):
            filtered_word = self.process_word(word)
            if filtered_word is not None:
                filtered_words.append(filtered_word)

        if len(filtered_words) > 0:
            return filtered_words
        else:
            return None

    def process(self) -> None:

        # Filter at line level
        self.message_filtered = self.filter_line(self.message_raw)

        # Split by lines
        for line in self.message_filtered.split("\n"):
            # Split by sentence
            for sentence in re.split(r'[.!?]', line):
                filtered_sentence = self.process_sentence(sentence)
                if filtered_sentence is not None:
                    self.sentences.append(filtered_sentence)

    def nlp_pos_query(self, nlp, word: str) -> str:

        # spacy detects emoji in the format of :happy: as PUNCT, give it its own POS
        if re.match(r"<:[a-z]+:[0-9]+>",word) or re.match(r":[a-z]+:",word):
            pos = 'EMOJI'
        elif word == '#nick':
            pos = 'NOUN'
        else:
            nlp_doc = nlp(word)
            pos = nlp_doc[0].pos_

        return pos

    def load_pos(self, session, nlp) -> None:
        for sentence in self.sentences:

            pos_b = None

            for word_index, word in enumerate(sentence):

                word['pos_text'] = self.nlp_pos_query(nlp, word['word_text'])

                # Check if pos exists already
                if not pos_b:
                    pos_a = session.query(Pos).filter(Pos.text == word['pos_text']).first()
                    if pos_a is None:
                        pos_a = Pos(text=word['pos_text'])
                        session.add(pos_a)
                        session.commit()
                else:
                    pos_a = pos_b

                word['pos'] = pos_a

                if word_index >= len(sentence) - 1:
                    word['pos_a->b'] = None
                    break

                sentence[word_index + 1]['pos_text'] = self.nlp_pos_query(nlp, sentence[word_index + 1]['word_text'])

                # Check if pos exists already
                pos_b = session.query(Pos).filter(Pos.text == sentence[word_index + 1]['pos_text']).first()
                if pos_b is None:
                    pos_b = Pos(text=sentence[word_index + 1]['pos_text'])
                    session.add(pos_b)
                    session.commit()

                pos_a_b = session.query(PosRelation).filter(
                    and_(PosRelation.a_id == pos_a.id, PosRelation.b_id == pos_b.id)).first()
                if pos_a_b is None:
                    pos_a_b = PosRelation(a_id=pos_a.id, b_id=pos_b.id)
                    session.add(pos_a_b)
                    session.commit()
                word['pos_a->b'] = pos_a_b

    def load_words(self, session) -> None:
        for sentence in self.sentences:

            word_b = None

            # Load words and relationships
            for word_index, word in enumerate(sentence):

                if not word_b:
                    word_a = session.query(Word).filter(Word.text == word['word_text']).first()
                    if word_a is None:
                        word_a = Word(text=word['word_text'], pos_id=word['pos'].id)
                        session.add(word_a)
                        session.commit()
                else:
                    word_a = word_b
                word['word'] = word_a

                # If we are on the last word, there is no word b or a->b relationship
                if word_index >= len(sentence) - 1:
                    word['word_a->b'] = None
                    break

                word_b = session.query(Word).filter(
                    Word.text == sentence[word_index + 1]['word_text']).first()
                if word_b is None:
                    word_b = Word(text=sentence[word_index + 1]['word_text'], pos_id=sentence[word_index + 1]['pos'].id)
                    session.add(word_b)
                    session.commit()
                sentence[word_index + 1]['word'] = word_b

                word_a_b = session.query(WordRelation).filter(
                    and_(WordRelation.a_id == word_a.id, WordRelation.b_id == word_b.id)).first()
                if word_a_b is None:
                    word_a_b = WordRelation(a_id=word_a.id, b_id=word_b.id)
                    session.add(word_a_b)
                    session.commit()
                word['word_a->b'] = word_a_b

    def load_neighbors(self, session) -> None:

        for sentence in self.sentences:

            if len(sentence) <= CONFIG_MARKOV_NEIGHBORHOOD_SENTENCE_SIZE_CHUNK:
                num_chunks = 1
            else:
                num_chunks = len(sentence) / float(CONFIG_MARKOV_NEIGHBORHOOD_SENTENCE_SIZE_CHUNK)

            chunks = np.array_split(sentence, num_chunks)

            for chunk in chunks:

                for word in chunk:

                    word['word_neighbors'] = []

                    # Filter things that are not relevant to the main information in a sentence
                    if word['pos'].text not in CONFIG_MARKOV_NEIGHBORHOOD_SENTENCE_POS_ACCEPT:
                        continue

                    for neighbor_index, potential_neighbor in enumerate(chunk):

                        if word['word'].id != potential_neighbor['word'].id:

                            if potential_neighbor['pos'].text \
                                    not in CONFIG_MARKOV_NEIGHBORHOOD_SENTENCE_POS_ACCEPT:
                                continue

                            neighbor = session.query(WordNeighbor). \
                                join(Word, WordNeighbor.b_id == Word.id). \
                                filter(and_(WordNeighbor.a_id == word['word'].id,
                                            Word.id == potential_neighbor['word'].id)).first()

                            if neighbor is None:
                                neighbor = WordNeighbor(a_id=word['word'].id, b_id=potential_neighbor['word'].id)
                                session.add(neighbor)
                                session.commit()

                            word['word_neighbors'].append(neighbor)

    # Called when ORM objects are needed
    def load(self, session, nlp) -> None:
        self.load_pos(session, nlp)
        self.load_words(session)
        self.load_neighbors(session)
        session.commit()


# A message from the bot
class MessageOutput(MessageBase):
    # message is just a string, not a discord message object
    def __init__(self, line: Line = None, text: str = None):
        MessageBase.__init__(self, line=line, text=text)

    def filter_line(self, raw_message: str) -> str:
        return emoji.emojize(raw_message)


# A message received from discord, loaded from the database line table, or from raw text
class MessageInput(MessageBase):
    # message is a discord message object
    # line is a orm object for the line table
    def __init__(self, message: discord.message.Message = None, line: Line = None, text: str = None):
        MessageBase.__init__(self, message=message, line=line, text=text)

    def filter_line(self, raw_message: str) -> str:
        message = raw_message

        # Replace mention with nick
        message = re.sub(r'<@[!]?[0-9]+>', '#nick', message)

        # Extract URLs
        self.args['url'] = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                                      message)

        # Remove URLs
        message = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '',
                         message)

        # Convert everything to lowercase
        message = message.lower()

        # Strip out undesirable characters to reduce entropy
        message = re.sub(r',|"|;|\(|\)|\[|\]|{|}|%|@|$|\^|&|\*|_|\\|/', "", message)

        # Demojify
        message = emoji.demojize(message)

        return message


class MessageInputCommand(MessageInput):
    def __init__(self, message: discord.message.Message = None, line=None, text=None):
        MessageInput.__init__(self, message=message, line=line, text=text)
