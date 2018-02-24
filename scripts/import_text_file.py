import argparse
import sys
from storage.imported import ImportTrainingDataManager


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('datafile')
    parser.add_argument('--verbose', help='Print out each line of data stored for training',
                        action='store_true')
    args = parser.parse_args()

    try:
        data = open(args.datafile, 'r').read()
    except UnicodeDecodeError:
        print("WARNING: Non UTF-8 characters detected!")
        print("If the file is not in UTF-8 format, behavior may be completely non functional.")
        c = input("Continue anyway? (y/n): ")
        if c != "y":
            print("Terminating.")
            sys.exit(0)
        data = open(args.datafile, 'rb').read()
        data = data.decode('utf-8', errors='ignore')

    data_manager = ImportTrainingDataManager()

    lines = data.split("\n")

    for line_idx, line in enumerate(lines):
        if line_idx % 1000 == 0:
            print("Import: %f%%" % (line_idx / len(lines) * 100))
        if args.verbose:
            print(line)
        data_manager.store(line)

    data_manager.commit()


if __name__ == '__main__':
    main()