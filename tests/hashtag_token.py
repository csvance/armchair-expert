from ml_common import create_nlp_instance


nlp = create_nlp_instance()

doc = nlp("twitter #hashtag")
assert len(doc) == 2
assert doc[0].text == 'twitter'
assert doc[1].text == '#hashtag'
