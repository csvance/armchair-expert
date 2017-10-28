from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from sqlalchemy import create_engine
import datetime


Base = declarative_base()


class Word(Base):
    __tablename__ = "word"
    id = Column(Integer, primary_key=True)
    text = Column(String(64), nullable=False, unique=True)
    count = Column(Integer, nullable=False, default=1)
    pos = Column(Integer, ForeignKey('pos.id'), nullable=False)

    def __repr__(self):
        return "id: %s text: %s" % (self.id, self.text)

class WordNeighbor(Base):
    __tablename__ = "wordneighbor"
    id = Column(Integer, primary_key=True)
    word = Column(Integer, ForeignKey('word.id'), nullable=False)
    neighbor = Column(Integer, ForeignKey('word.id'), nullable=False)
    count = Column(Integer, nullable=False, default=1)
    rating = Column(Integer, nullable=False, default=1)

class Pos(Base):
    __tablename__ = "pos"
    id = Column(Integer, primary_key=True)
    text = Column(String(16), nullable=False, unique=True)
    count = Column(Integer, nullable=False, default=1)

class PosRelation(Base):
    __tablename__ = "posrelation"
    id = Column(Integer, primary_key=True)
    a = Column(Integer, ForeignKey('pos.id'),nullable=False)
    b = Column(Integer, ForeignKey('pos.id'),nullable=False)
    count = Column(Integer, nullable=False, default=1)
    rating = Column(Integer, nullable=False, default=1)

class WordRelation(Base):
    __tablename__ = "wordrelation"
    id = Column(Integer, primary_key=True)
    a = Column(Integer, ForeignKey('word.id'), nullable=False)
    b = Column(Integer, ForeignKey('word.id'), nullable=False)
    count = Column(Integer, nullable=False, default=1)
    rating = Column(Integer, nullable=False, default=1)


class Line(Base):
    __tablename__ = "line"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    source_id = Column(Integer, nullable=False, default=1)
    server_id = Column(BigInteger, nullable=False)
    channel = Column(String(32), nullable=False)
    author = Column(String(32), nullable=False)
    text = Column(Text, nullable=False)


class URL(Base):
    __tablename__ = "url"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    text = Column(String(256), nullable=False, unique=True)
    count = Column(Integer, nullable=False, default=1)


#engine = create_engine('sqlite:///markov.db')
engine = create_engine('mysql+pymysql://root@localhost/markov?charset=utf8mb4',echo='debug')

Base.metadata.create_all(engine)

session_factory = sessionmaker(autoflush=False)
session_factory.configure(bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)
