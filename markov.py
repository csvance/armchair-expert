from markov_schema import *
from sqlalchemy import and_,or_
import re
import random



class MarkovAI(object):
    ALPHANUMERIC = "abcdefghijklmnopqrstuvqxyz123456789"

    def __init__(self):
        pass

    def filter(self,txt):
        # Convert everything to lowercase
        s = txt.lower()

        s.replace(",","")
        s.replace('"',"")
        s.replace(":","")
        s.replace(">","")
        s.replace("<","")

        sentences = []
        # Split by lines
        for line in txt.split("\n"):
            # Split by sentence
            for sentence in re.split('\.|!|\?', line):
                # Split by words
                pre_words = sentence.split(" ")
                post_words = []

                for word in pre_words:
                    if word != '':
                        post_words.append(word)

                #Sentences contain 2+ words
                if(len(post_words) >= 2):
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
            elif last_b_added == None or word != last_b_added.text:
                word_a.count += 1

            #Not last word? Lookup / add association
            if word_index != len(words)-1:

                #Word B
                word_b = session.query(Word).filter(Word.text==words[word_index+1]).first()
                if(word_b == None):
                    word_b = Word(text=words[word_index+1])
                    session.add(word_b)
                    last_b_added = word_b

                session.commit()

                relation = session.query(WordRelation).filter(and_(WordRelation.a == word_a.id,WordRelation.b == word_b.id)).first()
                if relation == None:
                    session.add(WordRelation(a=word_a.id,b=word_b.id))
                else:
                    relation.count += 1

            word_index += 1

        session.commit()


    def reply(self,words):
        pass

    def process_msg(self,io_module,txt,replyrate=1,args=None,is_owner=False):

        session = Session()
        session.add(Line(text=txt))
        session.commit()

        sentences = self.filter(txt)
        if(len(sentences) == 0):
            return

        sentence_index = 0
        reply_sentence = random.randrange(0,len(sentences))

        for sentence in sentences:
            self.learn(sentence)

            if reply_sentence == sentence_index:
                if replyrate > random.randrange(0,100):
                    io_module.output(self.reply(sentence))

            sentence_index += 1

