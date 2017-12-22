import unittest

from capitalization_model import CapitalizationModeEnum


class TestCapitalizationTransform(unittest.TestCase):
    def test_transform(self):

        self.assertEqual(CapitalizationModeEnum.transform(CapitalizationModeEnum.CHAOS, "ahahahahahah"), "aHaHaHaHaHaH")
        self.assertEqual(CapitalizationModeEnum.transform(CapitalizationModeEnum.UPPER_ALL, "ahahahahahah"), "AHAHAHAHAHAH")
        self.assertEqual(CapitalizationModeEnum.transform(CapitalizationModeEnum.LOWER_ALL, "ahahahahahah"), "ahahahahahah")
        self.assertEqual(CapitalizationModeEnum.transform(CapitalizationModeEnum.UPPER_FIRST, "ahahahahahah"), "Ahahahahahah")
        self.assertEqual(CapitalizationModeEnum.transform(CapitalizationModeEnum.UPPER_FIRST, "#ahahahahahah"), "#Ahahahahahah")


if __name__ == '__main__':
    unittest.main()
