from markov_schema import *

c = input("Are you sure you want to delete all lines from the DB? (y/n):")
if c == "y":
    session = Session
    session.query(Line).delete()
    session.commit()
else:
    print("Aborted.")