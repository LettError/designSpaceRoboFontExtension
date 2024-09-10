"""
# variable font text spec

<name of the variableFont>
    # indent
    > '<fileName>'   # optional

    # a full axis subset
    <axisName>
    ...

    # an axis subset at user value
    <axisName> <value>
    ...

    # an axis subset with a sub range
    <axisName> <minimumUserValue> <userDefault> <maximumUserValue>
    ...

"""
import re
import math
from fontTools import designspaceLib

from .parserTools import getLines, getBlocks, stringToNumber, numberToString

axisSubsetRE = re.compile(r"([a-zA-Z0-9\-]+)\s*([\-0-9\.]*)\s*([\-0-9\.]*)\s*([\-0-9\.]*)")
filenameRE = re.compile(r"\>\s+[\"|\'](.*)[\"|\']")

variableFontsLibKey = "com.letterror.designspaceEditor.variableFonts.text"


def parseVariableFonts(text, variableFontDescriptorClass=None):
    if variableFontDescriptorClass is None:
        variableFontDescriptorClass = designspaceLib.VariableFontDescriptor

    variableFonts = list()
    for variableFontName, lines in getBlocks(text).items():
        variableFont = variableFontDescriptorClass(name=variableFontName)
        variableFonts.append(variableFont)

        for line in getLines(lines):
            filenameFound = re.match(filenameRE, line)
            if filenameFound:
                variableFont.filename = filenameFound.groups()[0]

            axisSubsetFound = re.match(axisSubsetRE, line)
            if axisSubsetFound:
                axisName, minValue, value, maxValue = axisSubsetFound.groups()
                if minValue and not value and not maxValue:
                    variableFont.axisSubsets.append(
                        designspaceLib.ValueAxisSubsetDescriptor(
                            name=axisName,
                            userValue=stringToNumber(minValue),
                        )
                    )
                else:
                    variableFont.axisSubsets.append(
                        designspaceLib.RangeAxisSubsetDescriptor(
                            name=axisName,
                            userMinimum=stringToNumber(minValue, -math.inf),
                            userDefault=stringToNumber(value),
                            userMaximum=stringToNumber(maxValue, math.inf)
                        )
                    )

    return variableFonts


def dumpVariableFonts(variableFonts, indent="   "):
    text = []
    for variableFont in variableFonts:
        text.append(variableFont.name)
        if variableFont.filename is not None:
            text.append(f"{indent}> '{variableFont.filename}'")
            text.append("")
        for axisSubset in variableFont.axisSubsets:
            line = f"{indent}{axisSubset.name}"
            if hasattr(axisSubset, "userValue"):
                line += f" {numberToString(axisSubset.userValue)}"
            else:
                if axisSubset.userMinimum is not None and axisSubset.userDefault is not None and axisSubset.userMaximum is not None:
                    line += f" {numberToString(axisSubset.userMinimum)} {numberToString(axisSubset.userDefault)} {numberToString(axisSubset.userMaximum)}"

            text.append(line)
        text.append("")

    return "\n".join(text)


def extractVariableFonts(operator, indent="    "):
    """
    Extract variable fonts to a string for a given operator:
    check if variableFonts is stored as a string in the lib,
    parse that stored string and compare with the internal variable fonts.

    Compare with ignore the variableFonts order.

    If there is no difference, use the string representation.

    This will preseve comments and white space.
    """
    storedText = operator.lib.get(variableFontsLibKey, "")
    parsed = parseVariableFonts(storedText)

    if sorted([list(item.asdict().items()) for item in parsed]) == sorted([list(item.asdict().items()) for item in operator.variableFonts]):
        return storedText
    return dumpVariableFonts(operator.variableFonts, indent=indent)


def storeVariableFonts(text, operator):
    """
    Store variable fonts as objects from a string for a given operator and
    store the variable fonts string representation in the operator lib.
    """
    parsed = parseVariableFonts(text, operator.writerClass.variableFontDescriptorClas)
    operator.lib[variableFontsLibKey] = text
    operator.variableFonts.clear()
    operator.variableFonts.extend(parsed)
