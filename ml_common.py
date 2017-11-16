import os
import emoji
from markov_schema import *

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
                self.data.append(emoji.demojize(line.strip()))


class DatabaseLinesDataFetcher(TrainingDataFetcher):
    def __init__(self):
        TrainingDataFetcher.__init__(self)
        self.session = Session()

    def get_lines(self):
        lines = self.session.query(Line.text)


class DirectoryFileDataFetcher(TrainingDataFetcher):

    def __init__(self, path):
        TrainingDataFetcher.__init__(self)
        self.path = path
        self.files = []
        self.data = []

        self.enumerate_files()
        self.process_files()

    def enumerate_files(self):
        root, dirs, files = os.walk(self.path).__next__()
        for filename in files:
            filename_parts = filename.split(".")
            extension = None
            if len(filename_parts) > 1:
                extension = filename_parts[-1]
            self.files.append({'path': "%s/%s" % (root, filename),
                               'extension': extension})

    def process_files(self):
        for file in self.files:
            if file['extension'] == TXTFileDataFetcher.EXTENSION:
                self.data.extend(TXTFileDataFetcher(file['path']).get_data())