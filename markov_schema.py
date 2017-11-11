import datetime
from config import *
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text, BigInteger, Index
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm import relationship

Base = declarative_base()


class Word(Base):
    __tablename__ = "word"
    id = Column(Integer, index=True, primary_key=True)
    text = Column(String(256), index=True, nullable=False, unique=True)
    count = Column(Integer, nullable=False, default=1)
    pos_id = Column(Integer, ForeignKey('pos.id'), nullable=False)
    pos = relationship("Pos")
    rating = Column(Integer, nullable=False, default=1)

    def __repr__(self):
        return self.text


class WordNeighbor(Base):
    __tablename__ = "wordneighbor"
    id = Column(Integer, index=True, primary_key=True)
    a_id = Column(Integer, ForeignKey('word.id'), index=True, nullable=False)
    b_id = Column(Integer, ForeignKey('word.id'), index=True, nullable=False)
    a = relationship("Word",foreign_keys=[a_id])
    b = relationship("Word",foreign_keys=[b_id])
    count = Column(Integer, nullable=False, default=0)
    rating = Column(Integer, nullable=False, default=0)
    idx_wordneighbor_a_b = Index('idx_wordneighbor_a_b','a_id','b_id',unique=True)


class Pos(Base):
    __tablename__ = "pos"
    id = Column(Integer, index=True, primary_key=True)
    text = Column(String(16), index=True, nullable=False, unique=True)
    count = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return self.text


class PosRelation(Base):
    __tablename__ = "posrelation"
    id = Column(Integer, index=True, primary_key=True)
    a_id = Column(Integer, ForeignKey('pos.id'), index=True, nullable=False)
    b_id = Column(Integer, ForeignKey('pos.id'), index=True, nullable=False)
    a = relationship("Pos",foreign_keys=[a_id])
    b = relationship("Pos",foreign_keys=[b_id])
    count = Column(Integer, nullable=False, default=0)
    rating = Column(Integer, nullable=False, default=0)
    idx_posrelation_a_b = Index('idx_posrelation_a_b','a_id','b_id',unique=True)


class WordRelation(Base):
    __tablename__ = "wordrelation"
    id = Column(Integer, index=True, primary_key=True)
    a_id = Column(Integer, ForeignKey('word.id'), index=True, nullable=False)
    b_id = Column(Integer, ForeignKey('word.id'), index=True, nullable=False)
    a = relationship("Word",foreign_keys=[a_id])
    b = relationship("Word",foreign_keys=[a_id])
    count = Column(Integer, nullable=False, default=0)
    rating = Column(Integer, nullable=False, default=0)
    idx_wordrelation_a_b = Index('idx_wordrelation_a_b','a_id','b_id',unique=True)


class Line(Base):
    __tablename__ = "line"
    id = Column(Integer, index=True, primary_key=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    server_id = Column(BigInteger, nullable=True)
    channel = Column(String(32), nullable=True)
    author = Column(String(32), nullable=False)
    text = Column(Text, nullable=False)

    def __repr__(self):
        return self.text


class URL(Base):
    __tablename__ = "url"
    id = Column(Integer, index=True, primary_key=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    text = Column(String(512), index=True, nullable=False, unique=True)
    count = Column(Integer, nullable=False, default=1)


    def __repr__(self):
        return self.text


engine = create_engine(CONFIG_DATABASE_CONNECT)

Base.metadata.create_all(engine)

session_factory = sessionmaker(autoflush=False)
session_factory.configure(bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)
