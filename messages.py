from sqlalchemy import and_, or_, desc
from sqlalchemy import func, update, delete
from sqlalchemy.sql.functions import coalesce, sum
from sqlalchemy.orm import aliased
from config import *
import emoji
import re
from markov_schema import *


class MessageBase(object):
    def __init__(self,message=None,line=None):
        # Class Data
        self.message = message
        self.line = line
        self.message_raw = None
        self.message_filtered = None
        self.args = {}
        self.sentences = []

        # Used to keep track of the sentences[] being handled
        self.sentence_index = 0

        # Helpers
        self.re_emoji_emojify = re.compile(r":[a-z]+:")
        self.re_emoji_custom = re.compile(r"<:[a-z]+:[0-9]+>")

    # From line db table. Only called when rebuilding the database
    def args_from_line(self, line):
        self.args = {'timestamp': line.timestamp, 'channel': line.channel,
                     'server': line.server_id, 'author': line.author, 'always_reply': False,
                     'mentioned': False, 'author_mention': None, 'learning': True}

    def filter_line(self,raw_message):
        pass

    def process_word(self, word):

        if word == '':
            return None

        word_dict = {'word_text': word, 'pos': None}

        return word_dict

    def process_sentence(self, sentence):

        filtered_words = []
        for word in sentence.split(" "):
            filtered_word = self.process_word(word)
            if filtered_word is not None:
                filtered_words.append(filtered_word)

        if len(filtered_words) > 0:
            return filtered_words
        else:
            return None



    def process(self, raw_message):

        # Filter at line level
        self.message_filtered = self.filter_line(raw_message)

        # Split by lines
        for line in self.message_filtered.split("\n"):
            # Split by sentence
            for sentence in re.split(r'\.|!|\?', line):
                filtered_sentence = self.process_sentence(sentence)
                if filtered_sentence is not None:
                    self.sentences.append(filtered_sentence)

    def nlp_pos_query(self, nlp, word):

        pos = None

        # spacy detects emoji in the format of :happy: as PUNCT, give it its own POS
        if self.re_emoji_custom.match(word) or self.re_emoji_emojify.match(word):
            pos = 'EMOJI'
        elif word == '#nick':
            pos = 'NOUN'
        else:
            nlp_doc = nlp(word)
            pos = nlp_doc[0].pos_

        return pos

    # Called when ORM objects are needed
    def load(self, session, nlp):

        for sentence in self.sentences:

            # First, load POS
            for word_index, word in enumerate(sentence):

                word['pos_text'] = self.nlp_pos_query(nlp, word['word_text'])

                # Check if pos exists already
                pos_a = session.query(Pos).filter(Pos.text == word['pos_text']).first()
                if pos_a is None:
                    pos_a = Pos(text=word['pos_text'])
                    session.add(pos_a)
                    session.commit()
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

            # Used to break up words into reasonable neighborhood sizes (num_words^2 complexity)
            word_objs = []
            backref_objs = []

            # Load words and relationships
            for word_index, word in enumerate(sentence):

                word_a = session.query(Word).filter(Word.text == word['word_text']).first()
                if word_a is None:
                    word_a = Word(text=word['word_text'])
                    session.add(word_a)
                    session.commit()
                word['word'] = word_a

                # Store the word, and align add a backreference to the word in the sentence
                word_objs.append(word_a)
                backref_objs.append(word)

                # If we are on the last word, there is no word b or a->b relationship
                if word_index >= len(sentence) - 1:
                    word['word_a->b'] = None
                    break

                word_b = session.query(Word).filter(
                    Word.text == sentence[word_index + 1]['word_text']).first()
                if word_b is None:
                    word_b = Word(text=word['word_text'])
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

            # Used to break up words into reasonable neighborhood sizes (num_words^2 complexity)
            def chunks(l, n):
                """Yield successive n-sized chunks from l."""
                for i in range(0, len(l), n):
                    yield l[i:i + n]

            backref_iterator = iter(backref_objs)

            # Load neighbors
            chunk_word_objs = chunks(word_objs, CONFIG_MARKOV_NEIGHBORHOOD_SENTENCE_SIZE_CHUNK)

            for chunk in chunk_word_objs:

                for word in chunk:

                    # Load the backreference to the word in which we are loading neighbors for
                    word_backref = backref_iterator.__next__()

                    # Filter things that are not relevant to the main information in a sentence
                    if word.pos.text not in CONFIG_MARKOV_NEIGHBORHOOD_SENTENCE_POS_ACCEPT:
                        continue

                    for potential_neighbor in chunk:
                        if word.id != potential_neighbor.id:

                            if potential_neighbor.pos.text \
                                    not in CONFIG_MARKOV_NEIGHBORHOOD_SENTENCE_POS_ACCEPT:
                                continue

                            neighbor = session.query(WordNeighbor). \
                                join(Word, WordNeighbor.b_id == Word.id). \
                                filter(and_(WordNeighbor.a_id == word.id,
                                            Word.id == potential_neighbor.id)).first()

                            if neighbor is None:
                                neighbor = WordNeighbor(a_id=word.id, b_id=potential_neighbor.id)
                                session.add(neighbor)
                                session.commit()

                            try:
                                word_backref['word_neighbors'].append(neighbor)
                            except KeyError:
                                word_backref['word_neighbors'] = []
                                word_backref['word_neighbors'].append(neighbor)

            session.commit()


# A message from the bot
class MessageOutput(MessageBase):

    # message is just a string, not a discord message object
    def __init__(self, line=None, text=None, channel=None):
        MessageBase.__init__(self, line=line)

        if text is None and line is None:
            raise ValueError('text and line cannot both be None!')
        elif text is not None:
            self.args['channel'] = channel
            self.message_raw = text
        elif line is not None:
            self.message_raw = line.text
            self.args_from_line(line)

        self.process(self.message_raw)

    def filter_line(self,raw_message):
        return emoji.emojize(raw_message)



# A message received from discord or loaded from the database line table
class MessageInput(MessageBase):

    # message is a discord message object
    # line is a orm object for the line table
    def __init__(self, message=None, line=None):

        MessageBase.__init__(self, message, line)

        if message is None and line is None:
            raise ValueError('message and line cannot both be None!')
        elif message is not None:
            self.message_raw = message.content
            self.args_from_message(message)
        elif line is not None:
            self.message_raw = line.text
            self.args_from_line(line)

        self.process(self.message_raw)

    # From discord client
    def args_from_message(self, message):

        # Check for Private Message
        server = None
        try:
            server = message.channel.server.id
        except AttributeError:
            server = 0

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

    def filter_line(self, raw_message):

        message = raw_message

        # Replace mention with nick
        message = re.sub(r'<@[!]?[0-9]+>', '#nick', message)

        # Extract URLs
        self.args['url'] = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                              message)

        # Remove URLs
        message = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '',
                         message)

        # Demojify
        message = emoji.demojize(message)

        # Convert everything to lowercase
        message = message.lower()

        # Strip out undesirable characters to reduce entropy
        message = re.sub(r',|"|;|\(|\)|\[|\]|{|}|%|@|$|\^|&|\*|_|\\|/', "", message)

        return message

