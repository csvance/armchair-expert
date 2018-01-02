from typing import Optional, List, Tuple
from enum import Enum, unique
from common.ml import one_hot, MLDataPreprocessor
import re
from spacy.tokens import Token, Doc


def create_nlp_instance():
    import spacy
    from spacymoji import Emoji

    nlp = spacy.load('en')
    emoji_pipe = Emoji(nlp)
    nlp.add_pipe(emoji_pipe, first=True)

    # Merge hashtag tokens which were split by spacy
    def hashtag_pipe(doc):
        merged_hashtag = False
        while True:
            for token_index, token in enumerate(doc):
                if token.text == '#':
                    if token.head is not None:
                        start_index = token.idx
                        end_index = start_index + len(token.head.text) + 1
                        if doc.merge(start_index, end_index) is not None:
                            merged_hashtag = True
                            break
            if not merged_hashtag:
                break
            merged_hashtag = False
        return doc

    nlp.add_pipe(hashtag_pipe)
    return nlp


@unique
class Pos(Enum):
    NONE = 0

    # Universal
    ADJ = 1
    ADP = 2
    ADV = 3
    AUX = 4
    CONJ = 5
    CCONJ = 6
    DET = 7
    INTJ = 8
    NOUN = 9
    NUM = 10
    PART = 11
    PRON = 12
    PROPN = 13
    PUNCT = 14
    SCONJ = 15
    SYM = 16
    VERB = 17
    X = 18
    SPACE = 19

    # Custom
    EMOJI = 20
    HASHTAG = 21
    URL = 22

    # Special
    EOS = 23

    def one_hot(self) -> list:
        return one_hot(self.value, len(Pos))

    @staticmethod
    def from_token(token: Token, people: list = None) -> Optional['Pos']:
        if token.text[0] == '#':
            return Pos.HASHTAG
        elif token.text[0] == '@':
            return Pos.PROPN
        elif token.text[0] == ' ' or token.text[0] == "\n":
            return Pos.SPACE

        if token._.is_emoji:
            return Pos.EMOJI

        # Makeup for shortcomings of NLP detecting online nicknames
        if people is not None:
            if token.text in people:
                return Pos.PROPN

        if re.match(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', token.text):
            return Pos.URL

        try:
            return Pos[token.pos_]
        except KeyError:
            print("Unknown PoS: %s" % token.text)
            return Pos.X


@unique
class CapitalizationMode(Enum):
    NONE = 0
    UPPER_FIRST = 1
    UPPER_ALL = 2
    LOWER_ALL = 3
    COMPOUND = 4

    def one_hot(self):

        ret_list = []

        for i in range(0, len(CapitalizationMode)):
            if i != self.value:
                ret_list.append(0)
            else:
                ret_list.append(1)

        return ret_list

    @staticmethod
    def from_token(token: Token, compound_rules: Optional[List[str]] = None) -> 'CapitalizationMode':

        # Try to make a guess for many common patterns
        pos = Pos.from_token(token)
        if pos in [Pos.NUM, Pos.EMOJI, Pos.SYM, Pos.SPACE, Pos.EOS, Pos.HASHTAG, Pos.PUNCT, Pos.URL]:
            return CapitalizationMode.COMPOUND

        if token.text[0] == '@' or token.text[0] == '#':
            return CapitalizationMode.COMPOUND

        if token.text in compound_rules:
            return CapitalizationMode.COMPOUND

        lower_count = 0
        upper_count = 0
        upper_start = False
        for idx, c in enumerate(token.text):

            if c.isupper():
                upper_count += 1
                if upper_start:
                    upper_start = False
                if idx == 0:
                    upper_start = True
            elif c.islower():
                lower_count += 1

        if upper_start:
            return CapitalizationMode.UPPER_FIRST
        elif lower_count > 0 and upper_count == 0:
            return CapitalizationMode.LOWER_ALL
        elif upper_count > 0 and lower_count == 0:
            return CapitalizationMode.UPPER_ALL
        elif upper_count == 0 and lower_count == 0:
            return CapitalizationMode.NONE
        else:
            return CapitalizationMode.COMPOUND

    @staticmethod
    def transform(mode: 'CapitalizationMode', word: str) -> str:

        ret_word = word

        if mode == CapitalizationMode.UPPER_FIRST:

            first_alpha_flag = False
            ret_list = []

            ret_word = ret_word.lower()

            # Find the first letter
            for c_idx, c in enumerate(ret_word):
                if c.isalpha() and not first_alpha_flag:
                    ret_list.append(ret_word[c_idx].upper())
                    first_alpha_flag = True
                else:
                    ret_list.append(c)
            ret_word = "".join(ret_list)

        elif mode == CapitalizationMode.UPPER_ALL:
            ret_word = ret_word.upper()
        elif mode == CapitalizationMode.LOWER_ALL:
            ret_word = ret_word.lower()

        return ret_word


class SpacyPreprocessor(MLDataPreprocessor):
    def __init__(self):
        MLDataPreprocessor.__init__(self, 'SpacyPreprocessor')

    def preprocess(self, doc: Doc) -> bool:
        self.data.append(doc)
        return True

    def get_preprocessed_data(self) -> Tuple[List, List]:
        return self.data, self.labels
