import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, BigInteger
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

Base = declarative_base()


class Line(Base):
    __tablename__ = "line"
    id = Column(Integer, index=True, primary_key=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    source_id = Column(Integer, nullable=False)
    server_id = Column(BigInteger, nullable=True)
    channel = Column(String(32), nullable=True)
    author = Column(String(32), nullable=False)
    text = Column(Text, nullable=False)

    def __repr__(self):
        return self.text


engine = create_engine('sqlite:///lines.db')

Base.metadata.create_all(engine)

session_factory = sessionmaker()
session_factory.configure(bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)
