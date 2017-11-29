import unittest

from capitalization_model import CapitalizationMode


class TestCapitalizationTransform(unittest.TestCase):
    def test_transform(self):

        self.assertEqual(CapitalizationMode.transform(CapitalizationMode.CHAOS,"ahahahahahah"),"aHaHaHaHaHaH")
        self.assertEqual(CapitalizationMode.transform(CapitalizationMode.UPPER_ALL,"ahahahahahah"),"AHAHAHAHAHAH")
        self.assertEqual(CapitalizationMode.transform(CapitalizationMode.LOWER_ALL,"ahahahahahah"),"ahahahahahah")
        self.assertEqual(CapitalizationMode.transform(CapitalizationMode.UPPER_FIRST,"ahahahahahah"),"Ahahahahahah")
        self.assertEqual(CapitalizationMode.transform(CapitalizationMode.UPPER_FIRST,"#ahahahahahah"),"#Ahahahahahah")


if __name__ == '__main__':
    unittest.main()
