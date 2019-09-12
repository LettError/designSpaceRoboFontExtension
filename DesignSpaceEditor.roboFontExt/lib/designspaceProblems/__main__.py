import argparse
import pprint
import sys

from designspaceProblems import DesignSpaceChecker


def main(args=None):
    parser = argparse.ArgumentParser(
        description='Check designspace data.')
    parser.add_argument(
        'input_ds',
        metavar='PATH',
        help='path to designspace file',
        type=argparse.FileType())
    options = parser.parse_args(args)

    dc = DesignSpaceChecker(options.input_ds.name)
    dc.checkEverything()

    pprint.pprint(dc.problems)


if __name__ == '__main__':
    sys.exit(main())
