"""
# map text spac

<input value> > <output value>
<input value> > <output value>
<input value> > <output value>
...
"""

import pytest
import re

from .parserTools import getLines, stringToNumber


mapRE = re.compile(r"^(-?[0-9\.]+)\s*\>\s*(-?[0-9\.]+)\s*$")


def parseMap(text):
    mapData = list()
    for line in getLines(text):
        for result in re.finditer(mapRE, line):
            inputValue, outputValue = result.groups()
            mapData.append((float(inputValue), float(outputValue)))
    return mapData


def dumpMap(mapData):
    return "\n".join([f"{stringToNumber(inputValue)} > {stringToNumber(outputValue)}" for inputValue, outputValue in mapData])


# tests

@pytest.mark.parametrize("text,expected", [
    ("", []),
    ("10 > 20", [(10, 20)]),
    ("10 > 20\n15 > 25", [(10, 20), (15, 25)]),
    ("10>20\n15>      25", [(10, 20), (15, 25)]),
    ("-10>10", [(-10, 10)]),
    ("-10>-10", [(-10, -10)]),
    ("10>-10", [(10, -10)]),
])
def test_parseMap(text, expected):
    result = parseMap(text)
    assert expected == result


@pytest.mark.parametrize("amap,expected", [
    ([], ""),
    ([(10, 20)], "10 > 20"),
    ([(10, 20), (15, 25)], "10 > 20\n15 > 25"),
])
def test_dumpMap(amap, expected):
    result = dumpMap(amap)
    assert expected == result


if __name__ == '__main__':
    pytest.main([__file__])
