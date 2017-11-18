from ml_common import create_nlp_instance


nlp = create_nlp_instance()

for token in nlp("haha #lmao"):
    print(token.orth_)
    print(token.pos_)