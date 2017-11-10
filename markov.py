from markov_schema import *
from config import *
from sqlalchemy import and_, or_, desc
from sqlalchemy import func, update, delete
from sqlalchemy.sql.functions import coalesce, sum
from sqlalchemy.orm import aliased
from datetime import timedelta
import random
import numpy as np
from reaction_model import AOLReactionModel
from messages import *
import spacy


class BotReplyTracker(object):
    def __init__(self):
        self.replies = {}

    # Creates relevant nodes in reply tracker for server and channel
    def branch_(self, args):
        try:
            server = self.replies[int(args['server'])]
        except KeyError:
            self.replies[int(args['server'])] = {}

        try:
            channel = self.replies[int(args['server'])][str(args['channel'])]
        except KeyError:
            self.replies[int(args['server'])][str(args['channel'])] = {'timestamp': None, 'sentences': [],
                                                                       'fresh': False}

    # Called whenever the bot sends a message in a channel
    def bot_reply(self, output_message):
        self.branch_(output_message.args)
        self.replies[int(output_message.args['server'])][str(output_message.args['channel'])] = {
            'sentences': [output_message.sentences],
            'timestamp': output_message.args['timestamp'], 'fresh': True}

    # Called whenever a human sends a message to a channel
    def human_reply(self, input_msg):
        self.branch_(input_msg.args)
        self.get_reply(input_msg)['fresh'] = False

    # Gets the last bot reply in a channel
    def get_reply(self, input_msg):
        self.branch_(input_msg.args)
        return self.replies[int(input_msg.args['server'])][str(input_msg.args['channel'])]


class MarkovAI(object):
    def __init__(self):
        self.rebuilding = False
        print("Loading NLP DB...")
        self.nlp = spacy.load('en')
        self.reply_tracker = BotReplyTracker()
        print("Loading ML model...")
        self.reaction_model = AOLReactionModel()

        self.session = Session()

    def rebuild_db(self, ignore=[]):

        if self.rebuilding:
            return

        print("Rebuilding DB...")

        self.rebuilding = True

        if CONFIG_DATABASE == CONFIG_DATABASE_SQLITE:
            self.session.execute("VACUUM")

        self.session.query(URL).delete()
        self.session.query(WordRelation).delete()
        self.session.query(WordNeighbor).delete()
        self.session.query(Word).delete()
        self.session.query(PosRelation).delete()
        self.session.query(Pos).delete()

        self.session.commit()

        lines = self.session.query(Line).order_by(Line.timestamp.asc()).all()
        for line in lines:

            input_message = MessageInput(line=line)

            print(input_message.message_filtered)

            if str(line.channel) in ignore:
                continue
            elif line.server_id == 0:
                continue

            self.process_msg(None, input_message, rebuild_db=True)

        self.rebuilding = False

        if CONFIG_DATABASE == CONFIG_DATABASE_SQLITE:
            self.session.execute("VACUUM")

        print("Rebuilding DB Complete!")

    def clean_db(self):  # TODO: Update this function to effect WordNeighborhood ratings

        print("Cleaning DB...")


        # Subtract Rating by 1
        self.session.execute(update(WordRelation, values={
            WordRelation.rating: WordRelation.rating - CONFIG_MARKOV_TICK_RATING_DAILY_REDUCE}))
        self.session.commit()

        # Remove all forwards associations with no score
        self.session.query(WordRelation).filter(WordRelation.rating <= 0).delete()
        self.session.commit()

        # Check if we have any forward associations left
        results = self.session.query(Word.id). \
            outerjoin(WordRelation, WordRelation.a == Word.id). \
            group_by(Word.id). \
            having(func.count(WordRelation.id) == 0).all()

        # Go through each word with no forward associations left
        for result in results:
            # First delete all associations backwards from this word to other words
            self.session.query(WordRelation).filter(WordRelation.b == result.id).delete()
            # Next delete the word
            self.session.query(Word).filter(Word.id == result.id).delete()

        self.session.commit()


        print("Cleaning DB Complete!")

    def learn(self, input_message):

        for sentence in input_message.sentences:
            for word_index, word in enumerate(sentence):

                # Uprate Words
                word['word'].count += 1

                # Uprate Word Relations
                if word_index < len(sentence) - 1:
                    word['word_a->b'].count += 1
                    word['word_a->b'].rating += 1

                # Uprate POS
                word['pos'].count += 1

                # Uprate POS Relations
                if word_index < len(sentence) - 1:
                    word['pos_a->b'].count += 1
                    word['pos_a->b'].rating += 1

                # Uprate Word Neighbors
                for neighbor in word['word_neighbors']:
                    neighbor.count += 1
                    neighbor.rating += 1

        self.session.commit()

    def cmd_stats(self):
        words = self.session.query(Word.id).count()
        lines = self.session.query(Line.id).filter(Line.author != CONFIG_DISCORD_ME).count()
        assoc = self.session.query(WordRelation).count()
        neigh = self.session.query(WordNeighbor).count()
        return "I know %d words (%d associations, %8.2f per word, %d neighbors, %8.2f per word), %d lines." % (
            words, assoc, float(assoc) / float(words), neigh, float(neigh) / float(words), lines)

    def command(self, txt, args=None):

        result = None

        if txt.startswith("!words"):
            result = self.cmd_stats()

        if txt.startswith("!essay"):
            result = self.essay(txt.split(" ")[1], args)

        if args['is_owner'] is False:
            return result

        # Admin Only Commands
        if txt.startswith("!clean"):
            self.clean_db()

        return result

    def essay(self, subject, args):

        def random_punct():
            return [".", "!", "?"][random.randrange(0, 3)]

        s = subject.lower()
        txt = ""

        for p in range(0, 5):

            # Lead In
            reply = self.reply([s], args, nourl=True)
            if reply is None:
                txt = "I don't know that word well enough!"
                break
            txt += "\t" + reply + random_punct() + " "

            # Body sentences
            for i in range(0, 3):
                reply = self.reply(reply.split(" "), args, nourl=True)
                if reply is None:
                    txt = "I don't know that word well enough!"
                    break
                txt += reply + random_punct() + " "
            reply = self.reply([s], args, nourl=True)

            # Lead Out
            if reply is None:
                txt = "I don't know that word well enough!"
                break
            txt += reply + random_punct() + " "
            txt += "\n"

        return txt

    def reply(self, input_message, sentence_index):

        selected_topics = []
        potential_topics = [x for x in input_message.sentences[sentence_index] if
                            x['word_text'] not in CONFIG_MARKOV_TOPIC_SELECTION_FILTER]

        for word in potential_topics:

            potential_subject_pos = word['pos_text']

            if potential_subject_pos in CONFIG_MARKOV_TOPIC_SELECTION_POS:
                selected_topics.append(word)

        # If we are mentioned, we don't want to use the mention as a subject besides as a fallback
        if input_message.args['mentioned']:
            for word in selected_topics:
                if word['word_text'] == '#nick':
                    try:
                        selected_topics.remove(word)
                    except ValueError:
                        pass

        if len(selected_topics) == 0:
            selected_topics = input_message.sentences[sentence_index]

        selected_topic_id = []
        selected_topic_text = []

        for topic in selected_topics:
            selected_topic_id.append(topic['word'].id)
            selected_topic_text.append(topic['word_text'])

        potential_subject = None
        subject_word = None

        # Find potential exact matches, weigh by occurance
        subject_words = self.session.query(Word.id, Word.text, Word.pos_id, sum(Word.count).label('rating')).filter(
            Word.id.in_(selected_topic_id)).order_by(desc('rating')).all()

        if len(subject_words) > 1:
            # Linear distribution to choose word
            potential_subject = subject_words[np.random.triangular(0.0, 0.0, 1.0) * len(subject_words)]
        elif len(subject_words) == 1:
            potential_subject = subject_words[0]
        else:
            # Fallback to #nick
            potential_subject = self.session.query(Word.id, Word.text, Word.pos.id).filter(Word.text == '#nick')

        if potential_subject is None:
            return None
        else:
            subject_word = potential_subject

        # TODO: Figure out why this is needed
        if subject_word is None:
            return None

        last_word = subject_word

        # Generate Backwards
        backwards_words = []
        f_id = subject_word.id

        back_count = random.randrange(0, CONFIG_MARKOV_VECTOR_LENGTH)
        count = 0
        while count < back_count:

            choices = self.session.query(PosRelation, Pos.text). \
                join(Pos, PosRelation.a_id == Pos.id). \
                filter(PosRelation.b_id == last_word.pos_id). \
                order_by(desc(PosRelation.rating)).all()

            if len(choices) == 0:
                return None

            choice = choices[int(np.random.triangular(0.0, 0.0, 1.0) * len(choices))].text

            r_index = None

            # Most Intelligent search for next word (neighbor and pos)
            word_a = aliased(Word)
            word_b = aliased(Word)

            results = self.session.query(word_a.id, word_a.text, word_a.pos_id,
                                    (coalesce(sum(word_b.count), 0) * CONFIG_MARKOV_WEIGHT_WORDCOUNT
                                     + coalesce(sum(WordNeighbor.rating), 0) * CONFIG_MARKOV_WEIGHT_NEIGHBOR
                                     + coalesce(sum(WordRelation.rating),
                                                0) * CONFIG_MARKOV_WEIGHT_RELATION).label(
                                        'rating')). \
                join(word_b, word_b.id == f_id). \
                join(Pos, Pos.id == word_a.pos_id). \
                outerjoin(WordRelation, and_(WordRelation.a_id == word_a.id, WordRelation.b_id == word_b.id)). \
                outerjoin(WordNeighbor, and_(word_a.id == WordNeighbor.b_id, WordNeighbor.a_id == subject_word.id)). \
                filter(and_(Pos.text == choice, or_(WordNeighbor.rating > 0, WordRelation.rating > 0))). \
                group_by(word_a.id). \
                order_by(desc('rating')). \
                limit(CONFIG_MARKOV_GENERATE_LIMIT).all()

            if len(results) == 0:
                results = self.session.query(word_a.id, word_a.text, word_a.pos_id,
                                        (coalesce(sum(word_b.count), 0) * CONFIG_MARKOV_WEIGHT_WORDCOUNT
                                         + coalesce(sum(WordNeighbor.rating), 0) * CONFIG_MARKOV_WEIGHT_NEIGHBOR
                                         + coalesce(sum(WordRelation.rating), 0) * CONFIG_MARKOV_WEIGHT_RELATION).label(
                                            'rating')). \
                    join(word_b, word_b.id == f_id). \
                    outerjoin(WordRelation, and_(WordRelation.a_id == word_a.id, WordRelation.b_id == word_b.id)). \
                    outerjoin(WordNeighbor,
                              and_(word_a.id == WordNeighbor.b_id, WordNeighbor.a_id == subject_word.id)). \
                    filter(or_(WordNeighbor.rating > 0, WordRelation.rating > 0)). \
                    group_by(word_a.id). \
                    order_by(desc('rating')). \
                    limit(CONFIG_MARKOV_GENERATE_LIMIT).all()

            # Fall back to random
            if len(results) == 0:
                results = self.session.query(WordRelation.a_id, Word.text, Word.pos_id). \
                    join(Word, WordRelation.b_id == Word.id). \
                    order_by(desc(WordRelation.rating)). \
                    filter(and_(WordRelation.b_id == f_id, WordRelation.a_id != WordRelation.b_id)).all()

            if len(results) == 0:
                break

            r_index = int(np.random.triangular(0.0, 0.0, 1.0) * len(results))

            r = results[r_index]
            last_word = r

            f_id = r.id

            backwards_words.insert(0, r.text)

            count += 1

        # Generate Forwards
        forward_words = []
        f_id = subject_word.id
        forward_count = random.randrange(0, CONFIG_MARKOV_VECTOR_LENGTH)

        count = 0
        while count < forward_count:
            choices = self.session.query(PosRelation, Pos.text). \
                join(Pos, PosRelation.b_id == Pos.id). \
                filter(PosRelation.a_id == last_word.pos_id). \
                order_by(desc(PosRelation.rating)).all()

            if len(choices) == 0:
                return None

            choice = choices[int(np.random.triangular(0.0, 0.0, 1.0) * len(choices))].text

            results = self.session.query()

            # Most Intelligent search for next word (neighbor and pos)
            word_a = aliased(Word)
            word_b = aliased(Word)

            results = self.session.query(word_b.id, word_b.text, word_b.pos_id,
                                    (coalesce(sum(word_b.count), 0) * CONFIG_MARKOV_WEIGHT_WORDCOUNT
                                     + coalesce(sum(WordNeighbor.rating), 0) * CONFIG_MARKOV_WEIGHT_NEIGHBOR
                                     + coalesce(sum(WordRelation.rating), 0) * CONFIG_MARKOV_WEIGHT_RELATION).label(
                                        'rating')). \
                join(word_a, word_a.id == f_id). \
                join(Pos, Pos.id == word_b.pos_id). \
                outerjoin(WordNeighbor, and_(word_b.id == WordNeighbor.b_id, WordNeighbor.a_id == subject_word.id)). \
                outerjoin(WordRelation, and_(WordRelation.a_id == word_a.id, WordRelation.b_id == word_b.id)). \
                filter(and_(Pos.text == choice, or_(WordNeighbor.rating > 0, WordRelation.rating > 0))). \
                group_by(word_b.id). \
                order_by(desc('rating')). \
                limit(CONFIG_MARKOV_GENERATE_LIMIT).all()

            if len(results) == 0:
                results = self.session.query(word_b.id, word_b.text, word_b.pos_id,
                                        (coalesce(sum(word_b.count), 0) * CONFIG_MARKOV_WEIGHT_WORDCOUNT
                                         + coalesce(sum(WordNeighbor.rating), 0) * CONFIG_MARKOV_WEIGHT_NEIGHBOR
                                         + coalesce(sum(WordRelation.rating), 0) * CONFIG_MARKOV_WEIGHT_RELATION).label(
                                            'rating')). \
                    join(word_a, word_a.id == f_id). \
                    outerjoin(WordRelation, and_(WordRelation.a_id == word_a.id, WordRelation.b_id == word_b.id)). \
                    outerjoin(WordNeighbor,
                              and_(word_b.id == WordNeighbor.b_id, WordNeighbor.a_id == subject_word.id)). \
                    filter(or_(WordNeighbor.rating > 0, WordRelation.rating > 0)). \
                    group_by(word_b.id). \
                    order_by(desc('rating')). \
                    limit(CONFIG_MARKOV_GENERATE_LIMIT).all()

            # Fall back to random
            if len(results) == 0:
                results = self.session.query(WordRelation.b_id, Word.text, Word.pos_id). \
                    join(Word, WordRelation.b_id == Word.id). \
                    order_by(desc(WordRelation.rating)). \
                    filter(and_(WordRelation.a_id == f_id, WordRelation.b_id != WordRelation.a_id)).all()

            if len(results) == 0:
                break

            r_index = int(np.random.triangular(0.0, 0.0, 1.0) * len(results))

            r = results[r_index]

            last_word = r

            f_id = r.id

            forward_words.append(r.text)

            count += 1

        reply = []

        reply += backwards_words
        reply += [subject_word.text]
        reply += forward_words

        # Replace any mention in response with a mention to the name of the message we are responding too
        reply = [word.replace('#nick', input_message.args['author_mention']) for word in reply]

        # Add a random URL
        if random.randrange(0, 100) > (100 - CONFIG_MARKOV_URL_CHANCE):
            url = self.session.query(URL).order_by(func.random()).first()
            if url is not None:
                reply.append(url.text)

        return " ".join(reply)

    def check_reaction(self, input_msg):

        bot_reply = self.reply_tracker.get_reply(input_msg)

        # Check if reply exists
        if bot_reply['timestamp'] is None:
            return

        # Only handle reactions from the last CONFIG_MARKOV_REACTION_TIMEDELTA_S seconds or if the message is fresh
        elif bot_reply['fresh'] is not True and input_msg.args['timestamp'] > bot_reply['timestamp'] + \
                timedelta(seconds=CONFIG_MARKOV_REACTION_TIMEDELTA_S):
            return

        if self.reaction_model.classify_data([input_msg.message_filtered])[0]:
            self.handle_reaction(input_msg)
            return

        # If this wasn't a reaction, end the chain
        self.reply_tracker.human_reply(input_msg)

    def handle_reaction(self, input_msg):

        server_last_replies = self.reply_tracker.get_reply(input_msg)

        # Uprate words and relations
        for sentence_index,sentence in enumerate(server_last_replies['sentences']):
            for word_index,word in enumerate(sentence):
                word_a = word['word']
                if word_a.pos.text in CONFIG_MARKOV_REACTION_SCORE_POS:
                    word_a.rating += CONFIG_MARKOV_REACTION_UPRATE_WORD
                    if word_index != len(sentence) - 1:
                        word_b = word['word_a->b'].b
                        if word_b.pos.text in CONFIG_MARKOV_REACTION_SCORE_POS:
                            word_b.rating += CONFIG_MARKOV_REACTION_UPRATE_WORD
                            a_b_assoc = word['word_a->b']
                            a_b_assoc.rating += CONFIG_MARKOV_REACTION_UPRATE_RELATION

        # Uprate neighborhood
        for sentence in server_last_replies['sentences']:
            for word in sentence:

                # Filter things that are not relevant to the main information in a sentence
                if word['word'].pos.text not in CONFIG_MARKOV_NEIGHBORHOOD_SENTENCE_POS_ACCEPT:
                    continue

                for neighbor in word['word_neighbors']:
                    # Filter things that are not relevant to the main information in a sentence
                    if neighbor.b.pos.text not in CONFIG_MARKOV_NEIGHBORHOOD_SENTENCE_POS_ACCEPT:
                        continue

                    neighbor.count += 1
                    neighbor.rating += CONFIG_MARKOV_REACTION_UPRATE_NEIGHBOR

        self.session.commit()

    def learn_url(self, input_msg):

        for url in input_msg.args['url']:

            the_url = self.session.query(URL).filter(URL.text == url).first()

            if the_url is not None:
                the_url.count += 1
            else:
                self.session.add(URL(text=url, timestamp=input_msg.args['timestamp']))

            self.session.commit()

    def process_msg(self, io_module, input_msg, replyrate=1, owner=False, rebuild_db=False):

        # Ignore external I/O while rebuilding
        if self.rebuilding is True and not rebuild_db:
            return

        # Learn URLs
        self.learn_url(input_msg)

        # Log this line only if we are not rebuilding the database
        if not rebuild_db:
            self.session.add(
                Line(text=input_msg.message_raw, author=input_msg.args['author'],
                     server_id=int(input_msg.args['server']), channel=str(input_msg.args['channel']),
                     timestamp=input_msg.args['timestamp']))
            self.session.commit()

        # Populate ORM and NLP POS data
        input_msg.load(self.session, self.nlp)

        # Decide on a sentence in which to potentially reply
        reply_sentence = random.randrange(0, len(input_msg.sentences))

        for sentence_index, sentence in enumerate(input_msg.sentences):

            # Don't learn from ourself
            if input_msg.args['learning'] and not input_msg.args['author'] == CONFIG_DISCORD_ME:
                self.check_reaction(input_msg)
                self.learn(input_msg)

            # Don't reply when rebuilding the database
            if not rebuild_db and reply_sentence == sentence_index and (
                            replyrate > random.randrange(0, 100) or input_msg.args['always_reply']):

                reply = self.reply(input_msg, sentence_index)

                if reply is None:
                    continue

                # Add response to lines
                # Offset timestamp by one second for database ordering
                reply_time_db = input_msg.args['timestamp'] + timedelta(seconds=1)


                line = Line(text=reply, author=CONFIG_DISCORD_ME, server_id=int(input_msg.args['server']),
                                 channel=str(input_msg.args['channel']), timestamp=reply_time_db)
                self.session.add(line)
                self.session.commit()

                output_message = MessageOutput(line=line)

                # We want the discord channel object to respond to and the original timestamp
                output_message.args['channel'] = input_msg.args['channel']
                output_message.args['timestamp'] = input_msg.args['timestamp']

                self.reply_tracker.bot_reply(output_message)

                io_module.output(output_message)

            # If the author is us while we are rebuilding the DB, update the reply tracker
            elif rebuild_db and input_msg.args['author'] == CONFIG_DISCORD_ME:
                self.reply_tracker.bot_reply(output_message)