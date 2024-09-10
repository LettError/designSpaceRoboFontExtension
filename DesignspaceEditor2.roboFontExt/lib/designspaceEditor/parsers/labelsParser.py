"""
# axis label text spec

# add localised axis label for language tag
? <languageTag> '<localised axis label>'
...

# add axis label in a between minimum value, default value, maximum value
<axis label> <minimumValue> <defaultValue> <maximumValue>
# add localised axis lables for language tag
? <languageTage '<localised axis label>'  # optional
...

# add axis label add a uservalue
<axis label> <userValue>
# add localised axis lables for language tag
? <languageTage '<localised axis label>'  # optional
...

# optionally add (elidable) or (olderSibling) or [linkedUserValue]
<axis label> <userValue> (elidable) (olderSibling) [<linkedUserValue>]


# location label text spec

<label name>
    # indent
    ? <languageTag> '<localised name>'

    <axisName> <userValue>
    ...
"""

import re
import pytest
from fontTools import designspaceLib

from .parserTools import getLines, getBlocks, stringToNumber, numberToString


axisLabelRE = re.compile(r"[\"|\']([a-zA-Z0-9\- ]+)[\"|\']\s*([0-9\.]*)\s*([0-9\.]*)\s*([0-9\.]*)")
axisLabelLinkedUserValueRE = re.compile(r".*\[([0-9\.]+)\]")
labelNameRE = re.compile(r"\?\s+([a-zA-Z\-]+)\s+[\"|\'](.*)[\"|\']")
userLocationRE = re.compile(r"([a-zA-Z\-\s]+)\s+([0-9\.]+)")

defaultLabelNameLanguageTag = "en"

locationLabelsLibKey = "com.letterror.designspaceEditor.locationLabels.text"


def parseAxisLabels(text, axisLabelDescriptorClass=None):
    if axisLabelDescriptorClass is None:
        axisLabelDescriptorClass = designspaceLib.AxisLabelDescriptor
    labelNames = {}
    axisLabels = []
    currentAxisDescriptor = None
    for line in getLines(text):
        axisLabelfound = re.match(axisLabelRE, line)
        if axisLabelfound:
            labelName, minValue, value, maxValue = axisLabelfound.groups()
            if not minValue and not value and not maxValue:
                labelNames[defaultLabelNameLanguageTag] = labelName
            elif not value:
                minValue, value = value, minValue

            if value:
                lineLeftOver = line[axisLabelfound.end():]
                currentAxisDescriptor = axisLabelDescriptorClass(
                    name=labelName,
                    userValue=stringToNumber(value),
                    userMinimum=stringToNumber(minValue),
                    userMaximum=stringToNumber(maxValue),
                    elidable=bool("(elidable)" in lineLeftOver),
                    olderSibling=bool("(olderSibling)" in lineLeftOver)
                )
                axisLabels.append(currentAxisDescriptor)
                linkedUserValueFound = re.match(axisLabelLinkedUserValueRE, lineLeftOver)
                if linkedUserValueFound:
                    currentAxisDescriptor.linkedUserValue = float(linkedUserValueFound.groups()[0])

        else:
            labelNameFound = re.match(labelNameRE, line)
            if labelNameFound:
                languageTag, labelName = labelNameFound.groups()
                if currentAxisDescriptor is None:
                    labelNames[languageTag] = labelName
                else:
                    currentAxisDescriptor.labelNames[languageTag] = labelName

    return labelNames, axisLabels


def dumpAxisLabels(labelNames, axisLabels, indent="   "):
    text = []
    if defaultLabelNameLanguageTag in labelNames:
        text.append(f"'{labelNames[defaultLabelNameLanguageTag]}'")
    for languageTag, labelName in labelNames.items():
        if defaultLabelNameLanguageTag == languageTag:
            continue
        text.append(f"? {languageTag} '{labelName}'")

    if text:
        text.append("")
    for axisLabel in axisLabels:
        labelText = [f"'{axisLabel.name}'"]

        if axisLabel.userMinimum is not None:
            labelText.append(numberToString(axisLabel.userMinimum))
        labelText.append(numberToString(axisLabel.userValue))
        if axisLabel.userMaximum is not None:
            labelText.append(numberToString(axisLabel.userMaximum))

        if axisLabel.elidable:
            labelText.append("(elidable)")
        if axisLabel.olderSibling:
            labelText.append("(olderSibling)")
        if axisLabel.linkedUserValue is not None:
            labelText.append(f"[{numberToString(axisLabel.linkedUserValue)}]")

        text.append(" ".join(labelText))

        for languageTag, labelName in axisLabel.labelNames.items():
            text.append(f"? {languageTag} '{labelName}'")
        text.append("")
    return "\n".join(text)


def parseLocationLabels(text, locationLabelDescriptorClass=None):
    if locationLabelDescriptorClass is None:
        locationLabelDescriptorClass = designspaceLib.LocationLabelDescriptor
    locationLabels = []
    for labelName, lines in getBlocks(text).items():
        locationLabelDescriptor = locationLabelDescriptorClass(
            name=labelName,
            userLocation=dict(),
        )
        locationLabels.append(locationLabelDescriptor)

        for line in getLines(lines):
            labelNameFound = re.match(labelNameRE, line)
            if labelNameFound:
                languageTag, labelName = labelNameFound.groups()
                locationLabelDescriptor.labelNames[languageTag] = labelName

            userLocationFound = re.match(userLocationRE, line)
            if userLocationFound:
                axisName, value = userLocationFound.groups()
                locationLabelDescriptor.userLocation[axisName] = stringToNumber(value)
    return locationLabels


def dumpLocationLabels(locationLabels, indent="   "):
    text = []
    for locationLabel in locationLabels:
        text.append(locationLabel.name)
        for languageTag, labelName in locationLabel.labelNames.items():
            text.append(f"{indent}? {languageTag} \'{labelName}\'")
        text.append("")
        for axisName, value in locationLabel.userLocation.items():
            text.append(f"{indent}{axisName} {value}")
        text.append("")
    return "\n".join(text)


def extractLocationLabels(operator, indent="    "):
    """
    Extract location labels to a string for a given operator:
    check if location labels is stored as a string in the lib,
    parse that stored string and compare with the internal location labels.

    Compare with ignore the location labels order.

    If there is no difference, use the string representation.

    This will preseve comments and white space.
    """
    storedText = operator.lib.get(locationLabelsLibKey, "")
    parsed = parseLocationLabels(storedText)

    if sorted([list(item.asdict().items()) for item in parsed]) == sorted([list(item.asdict().items()) for item in operator.locationLabels]):
        return storedText
    return dumpLocationLabels(operator.locationLabels, indent=indent)


def storeLocationLabels(text, operator):
    """
    Store location labels as objects from a string for a given operator and
    store the location labels string representation in the operator lib.
    """
    parsed = parseLocationLabels(text, operator.writerClass.locationLabelDescriptorClass)
    operator.lib[locationLabelsLibKey] = text
    operator.locationLabels.clear()
    operator.locationLabels.extend(parsed)


# tests

@pytest.mark.parametrize("text,expected", [
    ('"Bold" 200 200 250', {'userMinimum': 200, 'userValue': 200, 'userMaximum': 250, 'name': 'Bold', 'elidable': False, 'olderSibling': False, 'linkedUserValue': None, 'labelNames': {}}),
    ('"Extra Light" 200 200 250 (elidable) (olderSibling) [300]', {'userMinimum': 200, 'userValue': 200, 'userMaximum': 250, 'name': 'Extra Light', 'elidable': True, 'olderSibling': True, 'linkedUserValue': 300.0, 'labelNames': {}}),
    ('"Extra Light" 200 200 250 (elidable) [300] (olderSibling)', {'userMinimum': 200, 'userValue': 200, 'userMaximum': 250, 'name': 'Extra Light', 'elidable': True, 'olderSibling': True, 'linkedUserValue': 300.0, 'labelNames': {}}),
    ('"Extra Light" 200 200 250 [300] (elidable) (olderSibling)', {'userMinimum': 200, 'userValue': 200, 'userMaximum': 250, 'name': 'Extra Light', 'elidable': True, 'olderSibling': True, 'linkedUserValue': 300.0, 'labelNames': {}}),
])
def test_parseAxisLabels(text, expected):
    labelNames, axisLabels = parseAxisLabels(text)
    assert axisLabels[0].asdict() == expected


if __name__ == '__main__':
    pytest.main([__file__])
