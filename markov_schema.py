from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
import datetime

Base = declarative_base()


class Word(Base):
    __tablename__ = "word"
    id = Column(Integer,primary_key=True)
    text = Column(String,nullable=False,unique=True)
    count = Column(Integer,nullable=False,default=1)

    def __repr__(self):
        return "id: %s text: %s" % (self.id,self.text)

class WordRelation(Base):
    __tablename__ = "wordrelation"
    id = Column(Integer, primary_key=True)
    a = Column(Integer, ForeignKey('word.id'), nullable=False)
    b = Column(Integer, ForeignKey('word.id'), nullable=False)
    count = Column(Integer, nullable=False, default=1)
    rating = Column(Integer, default=0, nullable=False)


class Line(Base):
    __tablename__ = "line"
    id = Column(Integer,primary_key=True)
    timestamp = Column(DateTime,nullable=False,default=datetime.datetime.utcnow)
    text = Column(String,nullable=False)

engine = create_engine('sqlite:///markov.db')
Base.metadata.create_all(engine)

Session = sessionmaker(autoflush=False)
Session.configure(bind=engine)