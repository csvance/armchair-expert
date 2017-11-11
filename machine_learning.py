class MLFeatureAnalyzer(object):
    def __init__(self, data: list):
        self.data = data

    def analyze(self) -> list:
        results = []
        for row in self.data:
            results.append(self.analyze_row(row))

        return results

    def analyze_row(self, row):
        pass