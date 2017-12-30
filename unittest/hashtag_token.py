import unittest
from common.nlp import create_nlp_instance


class TestSpacyHashtagSplit(unittest.TestCase):
    def test_split(self):

        nlp = create_nlp_instance()

        doc = nlp("twitter #hashtag")
        self.assertEqual(len(doc), 2)
        self.assertEqual(doc[0].text, 'twitter')
        self.assertEqual(doc[1].text, '#hashtag')


if __name__ == '__main__':
    unittest.main()
