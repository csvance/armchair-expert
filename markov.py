from datetime import timedelta

import numpy as np
import spacy
from sqlalchemy import func
from sqlalchemy import or_, desc, not_
from sqlalchemy.orm import aliased
from sqlalchemy.sql.functions import coalesce, sum

from messages import *
from reaction_model import AOLReactionModelPredictor


class BotReplyTracker(object):
    def __init__(self):
        self.replies = {}

    # Creates relevant nodes in reply tracker for server and channel
    def branch_(self, args: dict) -> None:
        try:
            self.replies[int(args['server'])]
        except KeyError:
            self.replies[int(args['server'])] = {}

        try:
            self.replies[int(args['server'])][str(args['channel'])]
        except KeyError:
            self.replies[int(args['server'])][str(args['channel'])] = {'timestamp': None, 'sentences': [],
                                                                       'fresh': False}

    # Called whenever the bot sends a message in a channel
    def bot_reply(self, output_message: MessageOutput) -> None:
        self.branch_(output_message.args)
        self.replies[int(output_message.args['server'])][str(output_message.args['channel'])] = {
            'sentences': output_message.sentences,
            'timestamp': output_message.args['timestamp'], 'fresh': True}

    # Called whenever a human sends a message to a channel
    def human_reply(self, input_message: MessageInput) -> None:
        self.branch_(input_message.args)
        self.get_reply(input_message)['fresh'] = False

    # Gets the last bot reply in a channel
    def get_reply(self, input_message: MessageInput) -> dict:
        self.branch_(input_message.args)
        return self.replies[int(input_message.args['server'])][str(input_message.args['channel'])]


class MarkovAI(object):
    def __init__(self):
        self.rebuilding = False
        print("Loading NLP DB...")
        self.nlp = spacy.load('en')
        self.reply_tracker = BotReplyTracker()
        print("Loading ML models...")
        self.reaction_model = AOLReactionModelPredictor()
        self.pos_tree_model = PosTreeModel(nlp=self.nlp)

        self.session = Session()

    def rebuild_db(self, ignore: Optional[list] = None, author: Optional[list] = None) -> None:

        if ignore is None:
            ignore = []
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
        self.session.query(Pos).delete()

        self.session.commit()

        if author is None:
            lines = self.session.query(Line).filter(or_(not_(Line.channel.in_(ignore)), Line.channel == None)).order_by(
                Line.timestamp.asc()).all()
        else:
            lines = self.session.query(Line).filter(
                and_(or_(not_(Line.channel.in_(ignore)), Line.channel == None), Line.author.in_(author))).order_by(
                Line.timestamp.asc()).all()

        for line in lines:

            input_message = MessageInput(line=line)

            print(input_message.message_filtered)

            if line.server_id == 0:
                continue

            self.process_msg(None, input_message, rebuild_db=True)

            self.rebuilding = False

        if CONFIG_DATABASE == CONFIG_DATABASE_SQLITE:
            self.session.execute("VACUUM")
        elif CONFIG_DATABASE == CONFIG_DATABASE_MYSQL:
            self.session.execute("OPTIMIZE TABLE WORD")
            self.session.execute("OPTIMIZE TABLE POS")
            self.session.execute("OPTIMIZE TABLE WORDRELATION")
            self.session.execute("OPTIMIZE TABLE WORDNEIGHBOR")
            self.session.execute("OPTIMIZE TABLE URL")

        print("Rebuilding DB Complete!")

    def learn(self, input_message: MessageInput) -> None:
        for sentence in input_message.sentences:
            for word_index, word in enumerate(sentence):

                # Uprate Words
                word['word'].count += 1
                word['word'].rating += 1

                # Uprate Word Relations
                if word_index < len(sentence) - 1:
                    word['word_a->b'].count += 1
                    word['word_a->b'].rating += 1

                # Uprate POS
                word['pos'].count += 1

                # Uprate Word Neighbors
                for neighbor in word['word_neighbors']:
                    neighbor.count += 1
                    neighbor.rating += 1

        self.session.commit()

    def cmd_stats(self) -> str:
        words = self.session.query(Word.id).count()
        lines = self.session.query(Line.id).filter(Line.author != CONFIG_DISCORD_ME).count()
        assoc = self.session.query(WordRelation).count()
        neigh = self.session.query(WordNeighbor).count()
        return "I know %d words (%d associations, %8.2f per word, %d neighbors, %8.2f per word), %d lines." % (
            words, assoc, float(assoc) / float(words), neigh, float(neigh) / float(words), lines)

    def command(self, command_message: MessageInputCommand) -> str:
        result = None

        if command_message.message_raw.startswith(CONFIG_COMMAND_TOKEN + "stats"):
            result = self.cmd_stats()

        if command_message.message_raw.startswith(CONFIG_COMMAND_TOKEN + "essay"):
            result = self.essay(command_message)

        return result

    def essay(self, command_message: MessageInputCommand) -> str:
        command_message.load(self.session, self.nlp)

        def random_punct():
            return [".", "!", "?"][random.randrange(0, 3)]

        txt = ""

        for p in range(0, 5):

            # Lead In
            reply = self.reply(command_message, 0, no_url=True)
            if reply is None:
                txt = "I don't know that word well enough!"
                break
            txt += "\t" + reply + random_punct() + " "

            # Body sentences
            for i in range(0, 3):

                feedback_reply_output = MessageOutput(text=reply)
                feedback_reply_output.args['author_mention'] = command_message.args['author_mention']

                feedback_reply_output.load(self.session, self.nlp)

                # noinspection PyTypeChecker
                reply = self.reply(feedback_reply_output, 0, no_url=True)
                if reply is None:
                    txt = "I don't know that word well enough!"
                    break
                txt += reply + random_punct() + " "

            reply = self.reply(command_message, 0, no_url=True)

            # Lead Out
            if reply is None:
                txt = "I don't know that word well enough!"
                break
            txt += reply + random_punct() + " "
            txt += "\n"

        return txt

    def reply(self, input_message: MessageInput, sentence_index: int, no_url=False) -> Optional[str]:
        selected_topics = []
        potential_topics = [x for x in input_message.sentences[sentence_index] if
                            x['word_text'] not in CONFIG_MARKOV_TOPIC_SELECTION_FILTER]

        # If we are mentioned, we don't want things to be about us
        if input_message.args['mentioned']:
            potential_topics = [x for x in potential_topics if x['word_text'] != CONFIG_DISCORD_ME_SHORT.lower()]

        potential_subject = None

        # TODO: Fix hack
        if type(input_message) == MessageInputCommand:
            potential_topics = [x for x in input_message.sentences[sentence_index] if
                                "essay" not in x['word_text']]

        for word in potential_topics:

            potential_subject_pos = word['pos_text']

            if potential_subject_pos in CONFIG_MARKOV_TOPIC_SELECTION_POS:
                selected_topics.append(word)

        if len(selected_topics) == 0:
            selected_topics = input_message.sentences[sentence_index]

        selected_topic_id = []
        selected_topic_text = []

        for topic in selected_topics:
            selected_topic_id.append(topic['word'].id)
            selected_topic_text.append(topic['word_text'])

        # Find potential exact matches, weigh by occurance
        subject_words = self.session.query(Word.id, Word.text, Word.pos_id, Pos.text.label('pos_text'),
                                           Word.count.label('rating')).filter(
            and_(Word.id.in_(selected_topic_id), Word.pos_id == Pos.id)).order_by(desc('rating')).all()

        if len(subject_words) > 1:
            # Linear distribution to choose word
            potential_subject = subject_words[int(np.random.triangular(0.0, 0.0, 1.0) * len(subject_words))]
        elif len(subject_words) == 1:
            potential_subject = subject_words[0]

        if potential_subject is None:
            subject_word = self.session.query(Word.id, Word.text, Word.pos_id, Pos.text.label('pos_text')).join(Pos,
                                                                                                                Pos.id == Word.pos_id).filter(
                Word.text == CONFIG_DISCORD_ME_SHORT.lower()).first()
        else:
            subject_word = potential_subject

        last_word = subject_word

        if CONFIG_MARKOV_DEBUG:
            print("Subject: %s Pos: %s" % (potential_subject.text, potential_subject.pos_text))

        # TODO: Optimize this, give preference to the POS we are looking for when generating the sentence structure in PosTreeModel.generate_sentence
        loops = 0
        sentence_structure = []
        while potential_subject.pos_text not in sentence_structure and loops < 100:
            sentence_structure = self.pos_tree_model.generate_sentence(words=[])
            loops += 1

        pos_index = None

        for p_idx, pos in enumerate(sentence_structure):
            if pos == potential_subject.pos_text:
                pos_index = p_idx
                break

        if pos_index is None:
            return None

        if CONFIG_MARKOV_DEBUG:
            print("Sentence Structure: %s" % str(sentence_structure))

        pos_index_forward = pos_index
        pos_index_backward = pos_index

        if len(sentence_structure) != 1:
            forward_count = len(sentence_structure) - (pos_index + 1)
            backward_count = pos_index + 1
        else:
            forward_count = 0
            backward_count = 0

        # Generate Backwards
        backwards_words = []
        f_id = subject_word.id
        count = 0
        while count < backward_count:
            pos_index_backward -= 1
            choice = sentence_structure[pos_index_backward]

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
                                              + coalesce(sum(WordRelation.rating),
                                                         0) * CONFIG_MARKOV_WEIGHT_RELATION).label(
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
                results = self.session.query(WordRelation.a_id.label('id'), Word.text, Word.pos_id). \
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

        count = 0
        while count < forward_count:

            pos_index += 1
            choice = sentence_structure[pos_index_forward]

            # Most Intelligent search for next word (neighbor and pos)
            word_a = aliased(Word)
            word_b = aliased(Word)

            results = self.session.query(word_b.id, word_b.text, word_b.pos_id,
                                         (coalesce(sum(word_b.count), 0) * CONFIG_MARKOV_WEIGHT_WORDCOUNT
                                          + coalesce(sum(WordNeighbor.rating), 0) * CONFIG_MARKOV_WEIGHT_NEIGHBOR
                                          + coalesce(sum(WordRelation.rating),
                                                     0) * CONFIG_MARKOV_WEIGHT_RELATION).label(
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
                                              + coalesce(sum(WordRelation.rating),
                                                         0) * CONFIG_MARKOV_WEIGHT_RELATION).label(
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
                results = self.session.query(WordRelation.b_id.label('id'), Word.text, Word.pos_id). \
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
        if not no_url and random.randrange(0, 100) > (100 - CONFIG_MARKOV_URL_CHANCE):
            url = self.session.query(URL).order_by(func.random()).first()
            if url is not None:
                reply.append(url.text)

        return " ".join(reply)

    def check_reaction(self, input_message: MessageInput) -> None:
        bot_reply = self.reply_tracker.get_reply(input_message)

        # Check if reply exists
        if bot_reply['timestamp'] is None:
            return

        # Only handle reactions from the last CONFIG_MARKOV_REACTION_TIMEDELTA_S seconds or if the message is fresh
        elif bot_reply['fresh'] is not True and input_message.args['timestamp'] > bot_reply['timestamp'] + \
                timedelta(seconds=CONFIG_MARKOV_REACTION_TIMEDELTA_S):
            return

        if self.reaction_model.predict(input_message.message_filtered)[0]:
            self.handle_reaction(input_message)
            return

        # If this wasn't a reaction, end the chain
        self.reply_tracker.human_reply(input_message)

    def handle_reaction(self, input_message: MessageInput) -> None:
        server_last_replies = self.reply_tracker.get_reply(input_message)

        # Uprate words and relations
        for sentence_index, sentence in enumerate(server_last_replies['sentences']):
            for word_index, word in enumerate(sentence):

                word_a = word['word']

                if word_a.pos.text in CONFIG_MARKOV_REACTION_SCORE_POS:
                    word_a.rating += CONFIG_MARKOV_REACTION_UPRATE_WORD

                    if word_index >= len(sentence) - 1:
                        continue

                    word_b = word['word_a->b'].b
                    if word_b.pos.text in CONFIG_MARKOV_REACTION_SCORE_POS:
                        word_b.rating += CONFIG_MARKOV_REACTION_UPRATE_WORD
                        a_b_assoc = word['word_a->b']
                        a_b_assoc.rating += CONFIG_MARKOV_REACTION_UPRATE_RELATION

        # Uprate neighborhood
        for sentence in server_last_replies['sentences']:
            for word in sentence:

                # Filter things that are not relevant to the main information in a sentence
                if word['word'].pos.text not in CONFIG_MARKOV_NEIGHBORHOOD_POS_ACCEPT:
                    continue

                for neighbor in word['word_neighbors']:
                    # Filter things that are not relevant to the main information in a sentence
                    if neighbor.b.pos.text not in CONFIG_MARKOV_NEIGHBORHOOD_POS_ACCEPT:
                        continue

                    neighbor.count += 1
                    neighbor.rating += CONFIG_MARKOV_REACTION_UPRATE_NEIGHBOR

        self.session.commit()

    def learn_url(self, input_message: MessageInput) -> None:
        for url in input_message.args['url']:

            the_url = self.session.query(URL).filter(URL.text == url).first()

            if the_url is not None:
                the_url.count += 1
            else:
                self.session.add(URL(text=url, timestamp=input_message.args['timestamp']))

            self.session.commit()

    def process_msg(self, io_module, input_message: MessageInput, replyrate: int = 0,
                    rebuild_db: bool = False) -> None:
        if len(input_message.sentences) == 0:
            return

        # Ignore external I/O while rebuilding
        elif self.rebuilding is True and not rebuild_db:
            return

        # Command message?
        if type(input_message) == MessageInputCommand:
            # noinspection PyTypeChecker
            reply = self.command(input_message)
            if reply:
                output_message = MessageOutput(text=reply)
                output_message.args['channel'] = input_message.args['channel']
                output_message.args['timestamp'] = input_message.args['timestamp']

                io_module.output(output_message)
            return

        # Learn URLs
        self.learn_url(input_message)

        # Keep pos_tree_model up to date with names of people for PoS detection
        if input_message.people is not None:
            self.pos_tree_model.update_people(input_message.people)

        # Log this line only if we are not rebuilding the database
        if not rebuild_db:

            # Sometimes server_id and channel can be none
            server_id = None
            if input_message.args['server'] is not None:
                # noinspection PyUnusedLocal
                server_id = server_id = int(input_message.args['server'])

            channel = None
            if input_message.args['channel'] is not None:
                channel = str(input_message.args['channel'])

            self.session.add(
                Line(text=input_message.message_raw, author=input_message.args['author'],
                     server_id=server_id, channel=channel,
                     timestamp=input_message.args['timestamp']))
            self.session.commit()

        # Populate ORM and NLP POS data
        input_message.load(self.session, self.nlp)

        # Decide on a sentence in which to potentially reply
        reply_sentence = random.randrange(0, len(input_message.sentences))

        for sentence_index, sentence in enumerate(input_message.sentences):

            # Don't learn from ourself
            if input_message.args['learning'] and not input_message.args['author'] == CONFIG_DISCORD_ME:

                # Only want to check reaction when message on a server
                if input_message.args['server'] is not None:
                    self.check_reaction(input_message)

                self.learn(input_message)
                self.pos_tree_model.process_sentence(input_message.message_filtered)

            # Don't reply when rebuilding the database
            if not rebuild_db and reply_sentence == sentence_index and (
                            replyrate > random.randrange(0, 100) or input_message.args['always_reply']):

                reply = self.reply(input_message, sentence_index)

                if reply is None:
                    continue

                # Add response to lines
                # Offset timestamp by one second for database ordering
                reply_time_db = input_message.args['timestamp'] + timedelta(seconds=1)

                line = Line(text=reply, author=CONFIG_DISCORD_ME, server_id=int(input_message.args['server']),
                            channel=str(input_message.args['channel']), timestamp=reply_time_db)
                self.session.add(line)
                self.session.commit()

                output_message = MessageOutput(line=line)

                # We want the discord channel object to respond to and the original timestamp
                output_message.args['channel'] = input_message.args['channel']
                output_message.args['timestamp'] = input_message.args['timestamp']

                # Load the reply database objects for reaction tracking
                output_message.load(self.session, self.nlp)

                self.reply_tracker.bot_reply(output_message)

                io_module.output(output_message)

            # If the author is us while we are rebuilding the DB, update the reply tracker
            elif rebuild_db and input_message.args['author'] == CONFIG_DISCORD_ME:
                # noinspection PyTypeChecker
                self.reply_tracker.bot_reply(input_message)
