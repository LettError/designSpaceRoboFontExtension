
def run():
    import os
    import sys
    import glob

    import pytest

    root = os.path.dirname(os.path.abspath(__file__))
    if root not in sys.path:
        sys.path.append(root)
    args = [
        "--doctest-modules",
    ]
    args += [file for file in glob.glob(f"{root}/*.py")]
    return not bool(pytest.main(args))


if __name__ == '__main__':
    run()
