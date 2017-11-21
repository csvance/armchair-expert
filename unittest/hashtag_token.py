from ml_common import create_spacy_instance
import unittest


class TestSpacyHashtagSplit(unittest.TestCase):
    def test_split(self):

        nlp = create_spacy_instance()

        doc = nlp("twitter #hashtag")
        self.assertEqual(len(doc), 2)
        self.assertEqual(doc[0].text, 'twitter')
        self.assertEqual(doc[1].text, '#hashtag')
