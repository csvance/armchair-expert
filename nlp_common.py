from typing import Optional
from enum import Enum, unique
from ml_common import one_hot
import re

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
class PosEnum(Enum):
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
    EOS = 100

    @staticmethod
    def one_hot(pos: 'PosEnum') -> list:
        return one_hot(pos.value-1, len(PosEnum))


def get_pos_from_token(token, people: list = None) -> Optional[PosEnum]:

    if token.text[0] == '#':
        return PosEnum.HASHTAG
    elif token.text[0] == '@':
        return PosEnum.PROPN

    if token._.is_emoji:
        return PosEnum.EMOJI

    # Makeup for shortcomings of NLP detecting online nicknames
    if people is not None:
        if token.text in people:
            return PosEnum.PROPN

    if re.match(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', token.text):
        return PosEnum.URL

    return PosEnum[token.pos_]






