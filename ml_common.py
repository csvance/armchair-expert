import os
import json
import csv
from markov_schema import *
import spacy

from spacymoji import Emoji


def hashtag_pipe(doc):

    merged_hashtag = False

    while True:

        for token_index,token in enumerate(doc):
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


def create_nlp_instance():
    nlp = spacy.load('en')
    emoji_pipe = Emoji(nlp)
    nlp.add_pipe(emoji_pipe, first=True)
    nlp.add_pipe(hashtag_pipe)
    return nlp


class MLFeatureAnalyzer(object):
    def __init__(self, data: list):
        self.data = data

    def analyze(self) -> list:
        results = []
        for row in self.data:
            results.append(self.analyze_row(row))

        return results

    def analyze_row(self, row) -> dict:
        pass


class TrainingDataFetcher(object):
    def __init__(self):
        self.data = None
        self.raw_data = None

    def get_data(self) -> dict:
        return self.data


class FileDataFetcher(TrainingDataFetcher):
    def __init__(self, path):
        TrainingDataFetcher.__init__(self)
        self.path = path
        self.extensions = None

        self.read_file(self.path)
        self.process_data()

    def read_file(self,path):
        self.raw_data = open(path, 'r').read()

    def process_data(self):
        pass


class TXTFileDataFetcher(FileDataFetcher):
    EXTENSION = "txt"

    def __init__(self, path):
        FileDataFetcher.__init__(self, path)
        self.extension = TXTFileDataFetcher.EXTENSION

    def process_data(self):
        self.data = []
        for line in self.raw_data.split("\n"):
            if line != '':
                self.data.append(line.strip())


class JSONFileDataFetcher(FileDataFetcher):
    EXTENSION = "json"

    def __init__(self, path):
        FileDataFetcher.__init__(self,path)

    def process_data(self):
        self.data = json.loads(self.raw_data)


class CSVFileDataFetcher(FileDataFetcher):
    EXTENSION = "csv"

    def __init__(self, path):
        FileDataFetcher.__init__(self,path)

    def read_file(self,path):
        pass

    def process_data(self):
        self.data = []
        for row in csv.reader(open(self.path, 'r', newline='', encoding='utf-8')):
            self.data.append(row)


class DatabaseLinesDataFetcher(TrainingDataFetcher):
    def __init__(self):
        TrainingDataFetcher.__init__(self)
        self.session = Session()

    def get_lines(self):
        lines = self.session.query(Line.text)


class DirectoryFilePathFetcher(TrainingDataFetcher):
    def __init__(self, path):
        TrainingDataFetcher.__init__(self)
        self.path = path
        self.data = []
        self.enumerate_files()

    def enumerate_files(self):
        root, dirs, files = os.walk(self.path).__next__()
        for filename in files:
            filename_parts = filename.split(".")
            extension = None
            if len(filename_parts) > 1:
                extension = filename_parts[-1]
            self.data.append({'path': "%s/%s" % (root, filename),
                               'extension': extension})


class DirectoryUnstructuredDataFetcher(TrainingDataFetcher):

    def __init__(self, path):
        TrainingDataFetcher.__init__(self)
        self.path = path
        self.files = []
        self.data = []
        self.process_files()

    def process_files(self):
        self.files = DirectoryFilePathFetcher(self.path).get_data()

        for file in self.files:
            if file['extension'] == TXTFileDataFetcher.EXTENSION:
                self.data.extend(TXTFileDataFetcher(file['path']).get_data())