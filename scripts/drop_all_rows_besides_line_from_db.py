from markov_schema import *

c = input("Are you sure you want to delete all rows besides lines from the DB? (y/n):")
if c == "y":
    session = Session
    session.query(URL).delete()
    session.query(WordRelation).delete()
    session.query(WordNeighbor).delete()
    session.query(Word).delete()
    session.query(Pos).delete()
    session.commit()
else:
    print("Aborted.")

