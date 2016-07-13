from markov_schema import *
from sqlalchemy import and_,or_
from sqlalchemy import func
import re
import random

def run_async(func):
    from threading import Thread
    from functools import wraps

    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target = func, args = args, kwargs = kwargs)
        func_hl.start()
        return func_hl

    return async_func


class MarkovAI(object):
    ALPHANUMERIC = "abcdefghijklmnopqrstuvqxyz123456789"

    def __init__(self):
        self.rebuilding = False
        self.rebuilding_thread = None
        pass

    @run_async
    def rebuild_db(self):

        if (self.rebuilding):
            return

        self.rebuilding = True
        session = Session()
        session.query(WordRelation).delete()
        session.query(Word).delete()
        session.commit()

        lines = session.query(Line).order_by(Line.timestamp.asc()).all()
        for line in lines:
            self.process_msg(None, line.text, rebuild_db=True)

        self.rebuilding = False


    def filter(self,txt):
        # Convert everything to lowercase
        s = txt.lower()

        s = re.sub(r',|"|;|>|<|\(|\)|\[|\]|{|}|%|@|#|$|\^|&|\*|_|\\|/', "", s)

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

                session.commit()

                relation = session.query(WordRelation).filter(and_(WordRelation.a == word_a.id,WordRelation.b == word_b.id)).first()
                if relation == None:
                    session.add(WordRelation(a=word_a.id,b=word_b.id))
                else:
                    relation.count += 1

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
        if txt.startswith("!rebuild"):
            self.rebuild_db()

        return result

    def reply(self,words):
        pass

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
                    io_module.output(self.reply(sentence),args)

            sentence_index += 1

