import json
import re
from typing import Optional

import numpy as np

from markov_schema import *


def rebuild_pos_tree_from_db(nlp):
    pos_tree_model = PosTreeModel(nlp=nlp, people=CONFIG_DISCORD_MEMBERS, rebuild=True)

    # Process database lines
    session = Session()
    query = session.query(Line.text)

    if CONFIG_DISCORD_MINI_ME is None:
        query = query.filter(Line.author != CONFIG_DISCORD_ME)
    else:
        query = query.filter(Line.author.in_(CONFIG_DISCORD_MINI_ME))
    query = query.order_by(Line.timestamp)

    lines = query.all()
    for line in lines:
        pos_tree_model.process_line(line.text)

    pos_tree_model.update_probabilities()
    pos_tree_model.save()


class PosTreeModel(object):
    def __init__(self, nlp=None, path: str = CONFIG_POS_TREE_CONFIG_PATH, people: dict = None, rebuild: bool = False):
        self.tree = {}
        self.nlp = nlp
        self.path = path
        self.people = people

        if path is not None and not rebuild:
            self.load(path)

    @staticmethod
    def custom_pos_from_word(word: str, people: list = None, is_emoji: bool = False) -> Optional[str]:

        if word[0] == '#':
            return 'HASHTAG'
        elif word[0] == '@':
            return 'NOUN'

        if is_emoji:
            return 'EMOJI'

        # Makeup for shortcomings of NLP detecting online nicknames
        if people is not None:
            if word in people:
                return 'NOUN'

        return None

    def generate_sentence(self, tree_start: dict = None, words: list = None) -> list:

        if tree_start is None:
            tree_start = self.tree

        a_choices = []
        p_values = []

        pos_keys = [x for x in tree_start if x.find("_") == -1]

        if len(pos_keys) == 0:
            return words

        for pos in pos_keys:
            a_choices.append(pos)
            p_values.append(tree_start[pos]['_p'])

        a_choices.append('_e')
        p_values.append(tree_start['_e_p'])

        choice = np.random.choice(a_choices, p=p_values)
        if choice != '_e':
            words.append(choice)
        else:
            return words

        return self.generate_sentence(tree_start[choice], words)

    def update_probabilities(self, tree_branch=None, deep: bool = True, start=False) -> None:

        if tree_branch is None:
            tree_branch = self.tree
            start = True

        pos_keys = [x for x in tree_branch if x.find("_") == -1]

        tree_sum = 0.
        for pos_key in pos_keys:
            tree_sum += tree_branch[pos_key]['_c']

        if not start and '_e_c' in tree_branch:
            tree_sum += tree_branch['_e_c']

        for pos_key in pos_keys:
            tree_branch[pos_key]['_p'] = tree_branch[pos_key]['_c'] / tree_sum

        if not start and '_e_c' in tree_branch:
            tree_branch['_e_p'] = tree_branch['_e_c'] / tree_sum
        else:
            tree_branch['_e_p'] = 0.

        if not deep:
            return

        # Recurse through each child
        for pos_key in pos_keys:
            self.update_probabilities(tree_branch[pos_key], start=False)

    def save(self, path: str = None) -> None:
        if path is None:
            open(self.path, 'w').write(json.dumps(self.tree, separators=(',', ':')))
        else:
            open(path, 'w').write(json.dumps(self.tree, separators=(',', ':')))

    def load(self, path: str) -> None:
        try:
            data = open(path, 'r').read()
        except FileNotFoundError:
            return
        self.tree = json.loads(data)

    def process_line(self, line: str, update_prob=False) -> None:
        tree_branch = self.tree

        for token_index, token in enumerate(self.nlp(line)):

            # TODO: Implement entity dection in spacy
            custom_pos = PosTreeModel.custom_pos_from_word(token.text, people=self.people, is_emoji=token._.is_emoji)
            pos_text = custom_pos if custom_pos is not None else token.pos_

            if pos_text in tree_branch:
                tree_branch[pos_text]['_c'] += 1
            else:
                tree_branch[pos_text] = {}
                tree_branch[pos_text]['_c'] = 1

            if update_prob:
                start = False if token_index == 0 else True
                self.update_probabilities(tree_branch, deep=False, start=start)

            tree_branch = tree_branch[pos_text]

        if '_e_c' in tree_branch:
            tree_branch['_e_c'] += 1
        else:
            tree_branch['_e_c'] = 1

    def process_text(self, text: str, update_prob=False) -> None:
        for line in text.split("\n"):
            self.process_line(re.sub(CONFIG_MARKOV_SYMBOL_STRIP, "", line), update_prob=update_prob)

    def update_people(self, people: str) -> None:
        self.people = people
