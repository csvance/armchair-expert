class TXTFileFeeder(object):
    def __init__(self, data_file_path):
        data = open(data_file_path, 'r').read()
        self.lines = self.filter_lines(data.split("\n"))

    # noinspection PyMethodMayBeStatic
    def filter_lines(self, lines):

        filtered_line_list = []

        for line in lines:
            if line != '':
                filtered_line_list.append(line.strip())

        return filtered_line_list