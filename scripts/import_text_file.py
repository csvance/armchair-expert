import argparse
from storage.imported import ImportTrainingDataManager


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('datafile')
    args = parser.parse_args()

    data = open(args.datafile, 'r').read()

    data_manager = ImportTrainingDataManager()

    lines = data.split("\n")
    for line_idx, line in enumerate(lines):

        if line_idx % 1000 == 0:
            print("Import: %f%%" % (line_idx / len(lines) * 100))

        data_manager.store(line)

    data_manager.commit()


if __name__ == '__main__':
    main()