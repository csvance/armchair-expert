from markov_schema import *
from config import *
from sqlalchemy import and_,or_
from sqlalchemy import func, update, delete
import re
import schedule
import random
import time


class MarkovAI(object):
    ALPHANUMERIC = "abcdefghijklmnopqrstuvqxyz123456789"

    def __init__(self):
        self.rebuilding = False
        self.rebuilding_thread = None

        #Schedule Cleanup Task
        schedule.every().day.do(MarkovAI.clean_db)


    def rebuild_db(self):

        if (self.rebuilding):
            return

        print("Rebuilding DB...")

        self.rebuilding = True
        session = Session()
        session.query(WordRelation).delete()
        session.query(Word).delete()
        session.commit()

        lines = session.query(Line).order_by(Line.timestamp.asc()).all()
        for line in lines:
            self.process_msg(None, line.text, rebuild_db=True)

        self.rebuilding = False

        print("Rebuilding DB Complete!")

    @staticmethod
    def clean_db():

            print("Cleaning DB...")
            session = Session()

            # Subtract Rating by 1
            session.execute(update(WordRelation, values={WordRelation.rating: WordRelation.rating - CONFIG_MARKOV_TICK_RATING_DAILY_REDUCE}))
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


    def filter(self,txt):
        # Convert everything to lowercase
        s = txt.lower()

        s = re.sub(r',|"|;|>|<|\(|\)|\[|\]|{|}|%|@|#|$|\^|&|\*|_|\\|/|:', "", s)

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

                if(len(post_words) >= 1):
                    sentences.append(post_words)

        return sentences

    def learn(self,words):

        session = Session()

        last_b_added = None

        word_index = 0
        for word in words:

            word_a = None
            word_b = None

            #Add word if it doesn't exist
            word_a = session.query(Word).filter(Word.text==word).first()
            if word_a == None:
                word_a = Word(text=word)
                session.add(word_a)
                session.commit()
            elif last_b_added == None or word != last_b_added.text:
                word_a.count += 1

            #Not last word? Lookup / add association
            if word_index != len(words)-1:

                #Word B
                word_b = session.query(Word).filter(Word.text==words[word_index+1]).first()
                if(word_b == None):
                    word_b = Word(text=words[word_index+1])
                    session.add(word_b)
                    session.commit()
                    last_b_added = word_b

                #Add Association
                relation = session.query(WordRelation).filter(and_(WordRelation.a == word_a.id,WordRelation.b == word_b.id)).first()
                if relation == None:
                    session.add(WordRelation(a=word_a.id,b=word_b.id))
                else:
                    relation.count += 1
                    relation.rating += 1

            word_index += 1

        session.commit()

    def cmd_stats(self):
        session = Session()
        words = session.query(Word.id).count()
        lines = session.query(Line.id).count()
        assoc = session.query(WordRelation).count()
        return "I know %d words (%d contexts, %8.2f per word), %d lines." % (words,assoc,float(assoc)/float(words),lines)

    def command(self,txt,args=None,is_owner=False):

        result = None

        if txt.startswith("!words"):
            result = self.cmd_stats()

        if is_owner == False:
            return result

        #Admin Only Commands
        if txt.startswith("!clean"):
            self.clean_db(CONFIG_MARKOV_TICK_RATING_DAILY_REDUCE)

        return result

    def reply(self, words, args):
        session = Session()

        w = []

        # Find the rarest word over 4 chars if we have two or more words.
        if(len(words)>=3):
            w = [word for word in words if len(word) >= CONFIG_MARKOV_RARE_WORD_MIN_LENGTH]
            w = [word for word in w if word not in CONFIG_MARKOV_RARE_FILTER]
        #Otherwise find the longest word
        else:
            longest_word = ""

            for word in words:
                if word not in CONFIG_MARKOV_RARE_FILTER and len(word) > len(longest_word):
                    longest_word = word
            w = [longest_word]


        if len(w) == 0:
            return None

        the_word = session.query(Word.id,Word.text,func.count(WordRelation.id).label('relations')).join(WordRelation, WordRelation.a == Word.id).\
            filter(Word.text.in_(w)).\
            group_by(Word.id,Word.text).\
            order_by(func.count(WordRelation.id).desc()).first()

        if the_word is None:
            return None

        r = None

        #Generate Backwards
        backwards_words = []
        f_id = the_word.id
        back_count = random.randrange(0,CONFIG_MARKOV_VECTOR_LENGTH)
        count = 0
        while(count < back_count):

            results = session.query(WordRelation.a,Word.text).\
                join(Word,WordRelation.a == Word.id).\
                filter(WordRelation.b == f_id).all()

            if len(results) == 0:
                break

            chain_attempts = 0
            while(chain_attempts < CONFIG_MARKOV_CHAIN_ATTEMPTS):
                #Pick a random result
                r = results[random.randrange(0,len(results))]

                if(f_id == r.a):
                    chain_attempts += 1
                    continue

                f_id = r.a
                backwards_words.insert(0,r.text)
                break

            count += 1

        #Generate Forwards
        forward_words = []
        f_id = the_word.id
        forward_count = random.randrange(0,CONFIG_MARKOV_VECTOR_LENGTH)
        count = 0
        while(count < forward_count):

            results = session.query(WordRelation.b,Word.text).\
                join(Word,WordRelation.b == Word.id).\
                filter(WordRelation.a == f_id).all()

            if len(results) == 0:
                break

            chain_attempts = 0
            while (chain_attempts < CONFIG_MARKOV_CHAIN_ATTEMPTS):
                # Pick a random result
                r = results[random.randrange(0, len(results))]

                if (f_id == r.b):
                    chain_attempts += 1
                    continue

                f_id = r.b
                forward_words.insert(0, r.text)
                break

            count += 1

        reply = []

        reply += backwards_words
        reply += [the_word.text]
        reply += forward_words

        reply = [word.replace('nick',args['author_mention']) for word in reply]

        return " ".join(reply)

    def process_msg(self, io_module, txt, replyrate=1, args=None, owner=False, rebuild_db=False):

        #Ignore external I/O while rebuilding
        if self.rebuilding == True and not rebuild_db:
            return

        if(txt.strip() == ''):
            return

        if not rebuild_db:
            session = Session()
            session.add(Line(text=txt,author=args['author'],server_id=args['server'],channel=str(args['channel'])))
            session.commit()

            #Check for command
            if txt.startswith("!"):
                result = self.command(txt, args, owner)
                if result:
                    io_module.output(result,args)
                return

        sentences = self.filter(txt)
        if(len(sentences) == 0):
            return

        sentence_index = 0
        reply_sentence = random.randrange(0,len(sentences))

        for sentence in sentences:
            self.learn(sentence)

            if not rebuild_db:
                if reply_sentence == sentence_index and replyrate > random.randrange(0,100):
                    io_module.output(self.reply(sentence,args),args)

            sentence_index += 1

