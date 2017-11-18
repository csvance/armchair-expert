from markov_schema import *

session = Session
session.query(URL).delete()
session.query(WordRelation).delete()
session.query(WordNeighbor).delete()
session.query(Word).delete()
session.query(Pos).delete()
session.commit()