from markov_schema import *
from config import *
from sqlalchemy import and_, or_, desc
from sqlalchemy import func, update, delete
from datetime import timedelta
from sqlalchemy.sql.functions import coalesce, sum
import re
import random
import time
import numpy as np
import spacy
from sqlalchemy.orm import aliased


def format_input_line(txt):

    s = txt

    # Strip all URL
    s = re.sub('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
               '', s, flags=re.MULTILINE)

    # Convert everything to lowercase
    s = txt.lower()

    s = re.sub(r',|"|;|\(|\)|\[|\]|{|}|%|@|$|\^|&|\*|_|\\|/', "", s)

    sentences = []
    # Split by lines
    for line in s.split("\n"):
        # Split by sentence
        for sentence in re.split(r'\.|!|\?', line):
            # Split by words
            pre_words = sentence.split(" ")
            post_words = []

            for word in pre_words:
                if word != '':
                    post_words.append(word)

            if len(post_words) >= 1:
                sentences.append(post_words)

    return sentences


def wordify_sentences(sentences):

    session = Session()

    # Return [line][word]
    lines = []

    for sentence in sentences:
        words = []
        for word in sentence:
            find_word = session.query(Word).filter(Word.text == word).first()
            if find_word is None:
                continue
            words.append(find_word)
        lines.append(words)

    return lines


class MarkovAI(object):
    ALPHANUMERIC = "abcdefghijklmnopqrstuvqxyz123456789"

    def __init__(self):
        self.rebuilding = False
        self.rebuilding_thread = None
        self.nlp = spacy.load('en')
        self.last_reply = {'sentences': [], 'timestamp': None}

    def rebuild_db(self, ignore=[]):

        if self.rebuilding:
            return

        print("Rebuilding DB...")

        self.rebuilding = True
        session = Session()

        if CONFIG_DATABASE == CONFIG_DATABASE_SQLITE:
            session.execute("VACUUM")

        session.query(URL).delete()
        session.query(WordRelation).delete()
        session.query(WordNeighbor).delete()
        session.query(Word).delete()
        session.query(PosRelation).delete()
        session.query(Pos).delete()

        session.commit()

        lines = session.query(Line).order_by(Line.timestamp.asc()).all()
        for line in lines:
            if str(line.channel) in ignore:
                continue
            elif line.server_id == 0:
                continue
            elif line.author == CONFIG_DISCORD_ME:
                self.last_reply = {'sentences': wordify_sentences(format_input_line(line)), 'timestamp': line.timestamp}
                continue

            text = re.sub(r'<@[!]?[0-9]+>', '#nick', line.text)
            print(text)

            self.process_msg(None, text, args={'learning': True}, rebuild_db=True, timestamp=line.timestamp)

        self.rebuilding = False

        if CONFIG_DATABASE == CONFIG_DATABASE_SQLITE:
            session.execute("VACUUM")

        print("Rebuilding DB Complete!")

    def clean_db(self):  # TODO: Update this function to effect WordNeighborhood ratings

        print("Cleaning DB...")
        session = Session()

        # Subtract Rating by 1
        session.execute(update(WordRelation, values={
            WordRelation.rating: WordRelation.rating - CONFIG_MARKOV_TICK_RATING_DAILY_REDUCE}))
        session.commit()

        # Remove all forwards associations with no score
        session.query(WordRelation).filter(WordRelation.rating <= 0).delete()
        session.commit()

        # Check if we have any forward associations left
        results = session.query(Word.id). \
            outerjoin(WordRelation, WordRelation.a == Word.id). \
            group_by(Word.id). \
            having(func.count(WordRelation.id) == 0).all()

        # Go through each word with no forward associations left
        for result in results:
            # First delete all associations backwards from this word to other words
            session.query(WordRelation).filter(WordRelation.b == result.id).delete()
            # Next delete the word
            session.query(Word).filter(Word.id == result.id).delete()

        session.commit()
        session.close()

        print("Cleaning DB Complete!")

    def learn(self, words):

        word_objs = []

        session = Session()

        last_b_added = None

        word_index = 0

        for word in words:

            # TODO: Fix this hack
            if len(word) > 64:
                continue

            # Use NLP
            doc = self.nlp(word)
            word_pos_txt_a = doc[0].pos_

            # Check if pos exists already
            pos_a = session.query(Pos).filter(Pos.text == word_pos_txt_a).first()
            if pos_a is None:
                pos_a = Pos(text=word_pos_txt_a)
                session.add(pos_a)
                session.commit()
            else:
                pos_a.count += 1

            # Add word if it doesn't exist
            word_a = session.query(Word).filter(Word.text == word).first()
            if word_a is None:
                word_a = Word(text=word, pos=pos_a.id)

                session.add(word_a)
                session.commit()

            elif last_b_added is None or word != last_b_added.text:
                word_a.count += 1
                word_a.rating += 1

            word_objs.append(word_a)

            # Not last word? Lookup / add association
            if word_index != len(words) - 1:

                # Use NLP
                doc = self.nlp(words[word_index + 1])
                word_pos_txt_b = doc[0].pos_

                # Check if pos exists already
                pos_b = session.query(Pos).filter(Pos.text == word_pos_txt_b).first()
                if pos_b is None:
                    pos_b = Pos(text=word_pos_txt_b)
                    session.add(pos_b)
                    session.commit()
                else:
                    pos_b.count += 1

                # Word B
                word_b = session.query(Word).filter(Word.text == words[word_index + 1]).first()
                if word_b is None:
                    # Use NLP
                    doc = self.nlp(words[word_index + 1])
                    word_pos_txt_b = doc[0].pos_

                    word_b = Word(text=words[word_index + 1], pos=pos_b.id)

                    session.add(word_b)
                    session.commit()

                    last_b_added = word_b

                # Add NLP POS Association
                pos_relation = session.query(PosRelation).filter(
                    and_(PosRelation.a == pos_a.id, PosRelation.b == pos_b.id)).first()
                if pos_relation is None:
                    session.add(PosRelation(a=pos_a.id, b=pos_b.id))
                else:
                    pos_relation.count += 1
                    pos_relation.rating += 1

                # Add Word Association
                word_relation = session.query(WordRelation).filter(
                    and_(WordRelation.a == word_a.id, WordRelation.b == word_b.id)).first()
                if word_relation is None:
                    session.add(WordRelation(a=word_a.id, b=word_b.id))
                else:
                    word_relation.count += 1
                    word_relation.rating += 1

            word_index += 1

        session.commit()

        def chunks(l, n):
            """Yield successive n-sized chunks from l."""
            for i in range(0, len(l), n):
                yield l[i:i + n]

        chunk_word_objs = chunks(word_objs, CONFIG_MARKOV_NEIGHBORHOOD_SENTENCE_SIZE_CHUNK)

        for chunk in chunk_word_objs:
            for word in chunk:

                # Filter things that are not relevant to the main information in a sentence
                if self.nlp(word.text)[0].pos_ not in CONFIG_MARKOV_NEIGHBORHOOD_SENTENCE_POS_ACCEPT:
                    continue

                for potential_neighbor in chunk:
                    if word.id != potential_neighbor.id:

                        if self.nlp(potential_neighbor.text)[
                            0].pos_ not in CONFIG_MARKOV_NEIGHBORHOOD_SENTENCE_POS_ACCEPT:
                            continue

                        neighbor = session.query(WordNeighbor). \
                            join(Word, WordNeighbor.neighbor == Word.id). \
                            filter(and_(WordNeighbor.word == word.id, Word.id == potential_neighbor.id)).first()

                        if neighbor is None:
                            neighbor = WordNeighbor(word=word.id, neighbor=potential_neighbor.id)
                            session.add(neighbor)
                            session.commit()
                        else:
                            neighbor.count += 1
                            neighbor.rating += 1

        session.commit()

    def cmd_stats(self):
        session = Session()
        words = session.query(Word.id).count()
        lines = session.query(Line.id).filter(Line.author != CONFIG_DISCORD_ME).count()
        assoc = session.query(WordRelation).count()
        neigh = session.query(WordNeighbor).count()
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

    def reply(self, words, args, nourl=False):
        session = Session()

        potential_topics = [x for x in words if x not in CONFIG_MARKOV_TOPIC_SELECTION_FILTER]

        # Attempt to find topic using NLP
        words_string = ' '.join(potential_topics)
        doc = self.nlp(words_string)
        sentence = next(doc.sents)

        for token in sentence:
            if token.pos_ in CONFIG_MARKOV_TOPIC_SELECTION_POS:
                potential_topics.append(token.orth_)

        # TODO: Fix hack
        try:
            potential_topics.remove('#')
        except ValueError:
            pass

        # If we are mentioned, we don't want to use the mention as a subject besides as a fallback
        if args['mentioned']:
            try:
                potential_topics.remove('nick')
            except ValueError:
                pass

        potential_subject = None
        subject_word = None

        # Find potential exact matches, weigh by occurance
        subject_words = session.query(Word.id, Word.text, Word.pos, sum(Word.count).label('rating')).filter(
            Word.text.in_(potential_topics)).order_by(desc('rating')).all()

        if len(subject_words) > 1:
            # -Linear distribution to choose word
            potential_subject = subject_words[np.random.triangular(0.0, 0.0, 1.0) * len(subject_words)]
        elif len(subject_words) == 1:
            potential_subject = subject_words[0]
        else:
            # Fallback!
            potential_subject = session.query(Word).filter(Word.text == '#nick').first()

        # If the word is nick, the subject is person talking
        if potential_subject == 'nick':
            potential_subject = '#nick'
            subject_word = session.query(Word.id, Word.text, Word.pos).filter(Word.text == potential_subject)
        elif potential_subject is None:
            return None
        else:
            subject_word = potential_subject

        if subject_word is None:
            return None

        last_word = subject_word

        # Generate Backwards
        backwards_words = []
        f_id = subject_word.id
        back_count = random.randrange(0, CONFIG_MARKOV_VECTOR_LENGTH)
        count = 0
        while count < back_count:

            choices = session.query(PosRelation, Pos.text). \
                join(Pos, PosRelation.a == Pos.id). \
                filter(PosRelation.b == last_word.pos). \
                order_by(desc(PosRelation.rating)).all()

            if len(choices) == 0:
                return None

            choice = choices[int(np.random.triangular(0.0, 0.0, 1.0) * len(choices))].text

            r_index = None

            # Most Intelligent search for next word (neighbor and pos)
            word_a = aliased(Word)
            word_b = aliased(Word)

            results = session.query(word_a.id, word_a.text, word_a.pos,
                                    (coalesce(sum(word_b.count), 0) * CONFIG_MARKOV_WEIGHT_WORDCOUNT
                                     + coalesce(sum(WordNeighbor.rating), 0) * CONFIG_MARKOV_WEIGHT_NEIGHBOR
                                     + coalesce(sum(WordRelation.rating),
                                                0) * CONFIG_MARKOV_WEIGHT_RELATION).label(
                                        'rating')). \
                join(word_b, word_b.id == f_id). \
                join(Pos, Pos.id == word_a.pos). \
                outerjoin(WordRelation, and_(WordRelation.a == word_a.id, WordRelation.b == word_b.id)). \
                outerjoin(WordNeighbor, and_(word_a.id == WordNeighbor.neighbor, WordNeighbor.word == subject_word.id)). \
                filter(and_(Pos.text == choice, or_(WordNeighbor.rating > 0, WordRelation.rating > 0))). \
                group_by(word_a.id). \
                order_by(desc('rating')). \
                limit(CONFIG_MARKOV_GENERATE_LIMIT).all()

            if len(results) == 0:
                results = session.query(word_a.id, word_a.text, word_a.pos,
                                        (coalesce(sum(word_b.count), 0) * CONFIG_MARKOV_WEIGHT_WORDCOUNT
                                         + coalesce(sum(WordNeighbor.rating), 0) * CONFIG_MARKOV_WEIGHT_NEIGHBOR
                                         + coalesce(sum(WordRelation.rating), 0) * CONFIG_MARKOV_WEIGHT_RELATION).label(
                                            'rating')). \
                    join(word_b, word_b.id == f_id). \
                    outerjoin(WordRelation, and_(WordRelation.a == word_a.id, WordRelation.b == word_b.id)). \
                    outerjoin(WordNeighbor,
                              and_(word_a.id == WordNeighbor.neighbor, WordNeighbor.word == subject_word.id)). \
                    filter(or_(WordNeighbor.rating > 0, WordRelation.rating > 0)). \
                    group_by(word_a.id). \
                    order_by(desc('rating')). \
                    limit(CONFIG_MARKOV_GENERATE_LIMIT).all()

            # Fall back to random
            if len(results) == 0:
                results = session.query(WordRelation.a, Word.text, Word.pos). \
                    join(Word, WordRelation.b == Word.id). \
                    order_by(desc(WordRelation.rating)). \
                    filter(and_(WordRelation.b == f_id, WordRelation.a != WordRelation.b)).all()

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
            choices = session.query(PosRelation, Pos.text). \
                join(Pos, PosRelation.b == Pos.id). \
                filter(PosRelation.a == last_word.pos). \
                order_by(desc(PosRelation.rating)).all()

            if len(choices) == 0:
                return None

            choice = choices[int(np.random.triangular(0.0, 0.0, 1.0) * len(choices))].text

            results = session.query()

            # Most Intelligent search for next word (neighbor and pos)
            word_a = aliased(Word)
            word_b = aliased(Word)

            results = session.query(word_b.id, word_b.text, word_b.pos,
                                    (coalesce(sum(word_b.count), 0) * CONFIG_MARKOV_WEIGHT_WORDCOUNT
                                     + coalesce(sum(WordNeighbor.rating), 0) * CONFIG_MARKOV_WEIGHT_NEIGHBOR
                                     + coalesce(sum(WordRelation.rating), 0) * CONFIG_MARKOV_WEIGHT_RELATION).label(
                                        'rating')). \
                join(word_a, word_a.id == f_id). \
                join(Pos, Pos.id == word_b.pos). \
                outerjoin(WordNeighbor, and_(word_b.id == WordNeighbor.neighbor, WordNeighbor.word == subject_word.id)). \
                outerjoin(WordRelation, and_(WordRelation.a == word_a.id, WordRelation.b == word_b.id)). \
                filter(and_(Pos.text == choice, or_(WordNeighbor.rating > 0, WordRelation.rating > 0))). \
                group_by(word_b.id). \
                order_by(desc('rating')). \
                limit(CONFIG_MARKOV_GENERATE_LIMIT).all()

            if len(results) == 0:
                results = session.query(word_b.id, word_b.text, word_b.pos,
                                        (coalesce(sum(word_b.count), 0) * CONFIG_MARKOV_WEIGHT_WORDCOUNT
                                         + coalesce(sum(WordNeighbor.rating), 0) * CONFIG_MARKOV_WEIGHT_NEIGHBOR
                                         + coalesce(sum(WordRelation.rating), 0) * CONFIG_MARKOV_WEIGHT_RELATION).label(
                                            'rating')). \
                    join(word_a, word_a.id == f_id). \
                    outerjoin(WordRelation, and_(WordRelation.a == word_a.id, WordRelation.b == word_b.id)). \
                    outerjoin(WordNeighbor,
                              and_(word_b.id == WordNeighbor.neighbor, WordNeighbor.word == subject_word.id)). \
                    filter(or_(WordNeighbor.rating > 0, WordRelation.rating > 0)). \
                    group_by(word_b.id). \
                    order_by(desc('rating')). \
                    limit(CONFIG_MARKOV_GENERATE_LIMIT).all()

            # Fall back to random
            if len(results) == 0:
                results = session.query(WordRelation.b, Word.text, Word.pos). \
                    join(Word, WordRelation.b == Word.id). \
                    order_by(desc(WordRelation.rating)). \
                    filter(and_(WordRelation.a == f_id, WordRelation.b != WordRelation.a)).all()

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
        reply = [word.replace('#nick', args['author_mention']) for word in reply]

        if not nourl:
            # Add a random URL
            if random.randrange(0, 100) > (100 - CONFIG_MARKOV_URL_CHANCE):
                url = session.query(URL).order_by(func.random()).first()
                if url is not None:
                    reply.append(url.text)

        return " ".join(reply)

    def check_reaction(self, txt, args):
        signal_sum = 0
        noise_sum = 0

        # Check if we have replied
        if self.last_reply['timestamp'] is None:
            return

        # Only handle reactions from the last CONFIG_MARKOV_REACTION_TIMEDELTA_S seconds
        if args['timestamp'] > self.last_reply['timestamp'] + timedelta(seconds=CONFIG_MARKOV_REACTION_TIMEDELTA_S):
            return

        for one_word in CONFIG_MARKOV_REACTION_CHARS:
            for c in one_word:
                signal_sum += txt.count(c)
            noise_sum = len(txt) - signal_sum

            if signal_sum > noise_sum:
                self.handle_reaction()
                return

            signal_sum = 0
            noise_sum = 0

    def handle_reaction(self):

        session = Session()

        sentence_index = 0
        word_index = 0

        for sentence in self.last_reply['sentences']:
            for word_a in sentence:

                # Use NLP to classify word
                doc = self.nlp(word_a.text)
                word_pos_txt_a = doc[0].pos_

                if word_pos_txt_a in CONFIG_MARKOV_REACTION_SCORE_POS:

                    # Uprate word
                    word_a.rating += CONFIG_MARKOV_REACTION_UPRATE_WORD

                    if word_index != len(sentence) - 1:
                        word_b = sentence[word_index + 1]

                        # Use NLP to classify word
                        doc = self.nlp(word_b.text)
                        word_pos_txt_b = doc[0].pos_

                        if word_pos_txt_b in CONFIG_MARKOV_REACTION_SCORE_POS:

                            word_b.rating += CONFIG_MARKOV_REACTION_UPRATE_WORD

                            a_b_assoc = session.query(WordRelation).filter(
                                and_(WordRelation.a == word_a.id, WordRelation.b == word_b.id)).first()
                            if a_b_assoc is not None:
                                # Uprate rating
                                a_b_assoc.rating += CONFIG_MARKOV_REACTION_UPRATE_RELATION
                            else:
                                a_b_assoc = WordRelation(a=word_a.id, b=word_b.id, rating=1 + 5)
                                session.add(a_b_assoc)
                                session.commit()

                word_index += 1

            word_index = 0
            sentence_index += 1

        session.commit()

    def process_msg(self, io_module, txt, replyrate=1, args=None, owner=False, rebuild_db=False, timestamp=None):

        # No information so we don't need to process
        sentences = format_input_line(txt)
        if len(sentences) == 0:
            return

        # Ignore external I/O while rebuilding
        if self.rebuilding is True and not rebuild_db:
            return

        if txt.strip() == '':
            return

        if not rebuild_db:
            session = Session()
            session.add(
                Line(text=txt, author=args['author'], server_id=int(args['server']), channel=str(args['channel']),
                     timestamp=args['timestamp']))
            session.commit()

            # Check for command
            if txt.startswith("!"):
                result = self.command(txt, args)
                if result:
                    io_module.output(result, args)
                # We don't want to learn from commands
                return

        if args['learning']:
            # Get all URLs
            urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', txt)
            if len(urls) >= 0:
                session = Session()
                for url in urls:

                    the_url = session.query(URL).filter(URL.text == url).first()

                    if the_url is not None:
                        the_url.count += 1
                    else:
                        if timestamp:
                            session.add(URL(text=url, timestamp=timestamp))
                        else:
                            session.add(URL(text=url))

                session.commit()

        sentence_index = 0
        reply_sentence = random.randrange(0, len(sentences))

        for sentence in sentences:
            if args['learning']:

                # Don't learn from ourself
                if str(args['author']) != CONFIG_DISCORD_ME:
                    self.check_reaction(" ".join(sentence), args)
                    self.learn(sentence)

            if not rebuild_db:
                if reply_sentence == sentence_index and (replyrate > random.randrange(0, 100) or args['always_reply']):

                    the_reply = self.reply(sentence, args)

                    if the_reply is not None:
                        # Offset timestamp by one second for database ordering
                        reply_time = args['timestamp'] + timedelta(seconds=1)

                        self.last_reply = {'sentences': wordify_sentences([the_reply.split(" ")]),
                                           'timestamp': reply_time}

                        # Add response to lines
                        session = Session()
                        session.add(Line(text=the_reply, author=CONFIG_DISCORD_ME, server_id=int(args['server']),
                                         channel=str(args['channel']), timestamp=reply_time))
                        session.commit()

                        io_module.output(the_reply, args)

            sentence_index += 1
