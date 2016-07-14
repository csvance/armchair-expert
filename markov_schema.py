from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from sqlalchemy import create_engine
import datetime

Base = declarative_base()


class Word(Base):
    __tablename__ = "word"
    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False, unique=True)
    count = Column(Integer, nullable=False, default=1)

    def __repr__(self):
        return "id: %s text: %s" % (self.id, self.text)


class WordRelation(Base):
    __tablename__ = "wordrelation"
    id = Column(Integer, primary_key=True)
    a = Column(Integer, ForeignKey('word.id'), nullable=False)
    b = Column(Integer, ForeignKey('word.id'), nullable=False)
    count = Column(Integer, nullable=False, default=1)
    rating = Column(Integer, default=7, nullable=False)


class Line(Base):
    __tablename__ = "line"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    source_id = Column(Integer, nullable=False, default=1)
    server_id = Column(Integer, nullable=False)
    channel = Column(String, nullable=False)
    author = Column(String, nullable=False)
    text = Column(String, nullable=False)


engine = create_engine('sqlite:///markov.db')
Base.metadata.create_all(engine)

session_factory = sessionmaker(autoflush=False)
session_factory.configure(bind=engine)
Session = scoped_session(session_factory)
