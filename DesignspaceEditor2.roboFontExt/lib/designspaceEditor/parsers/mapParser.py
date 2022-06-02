import re

from .parserTools import getLines, stringToNumber


mapRE = re.compile(r"^([0-9\.]+)\s*\>\s*([0-9\.]+)\s*$")


def parseMap(text):
    mapData = list()
    for line in getLines(text):
        for result in re.finditer(mapRE, line):
            inputValue, outputValue = result.groups()
            mapData.append((float(inputValue), float(outputValue)))
    return mapData


def dumpMap(mapData):
    return "\n".join([f"{stringToNumber(inputValue)} > {stringToNumber(outputValue)}" for inputValue, outputValue in mapData])





# t = """
# 10 >20
# 0> 100
# 20>1000
# 10 >     40
# """

# d = parseMap(t)
# r = dumpMap(d)

# print(r)