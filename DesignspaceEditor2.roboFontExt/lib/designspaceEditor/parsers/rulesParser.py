"""
# rules text spec

<name of the rule>
    # indent
    # list of subsititions
    <glyphName> > <glyphName>
    ...

    # conditions
    <axisName> <minimumValue> - <maximumValue>
    ...
    # condition set
    <axisName> <minimumValue> - <maximumValue> <axisName> <minimumValue> - <maximumValue>
    ...
"""

import re
from fontTools import designspaceLib

from .parserTools import getBlocks, getLines, stringToNumber, numberToString

substitionRE = re.compile(r"([a-zA-Z0-9\.\*\+\-\:\^\|\~_]+)\s+\>\s+([a-zA-Z0-9\.\*\+\-\:\^\|\~_]+)")
conditionsRE = re.compile(r"([a-zA-Z]+)\s+([0-9\.]+)-([0-9\.]+)")


def parseRules(text, ruleDescriptorClass):
    rules = []
    for name, lines in getBlocks(text).items():
        rule = ruleDescriptorClass()
        rules.append(rule)

        rule.name = name

        for line in getLines(lines):
            for r in re.finditer(substitionRE, line):
                glyphName1, glyphName2 = r.groups()
                rule.subs.append((glyphName1, glyphName2))

            conditionSet = []
            for f in re.finditer(conditionsRE, line):
                axisName, minimumValue, maximumValue = f.groups()
                conditionSet.append(dict(name=axisName, minimum=stringToNumber(minimumValue), maximum=stringToNumber(maximumValue)))
            if conditionSet:
                rule.conditionSets.append(conditionSet)
    return rules


def dumpRules(rules, indent="    "):
    text = []
    for rule in rules:
        text.append(rule.name)

        for glyphName1, glyphName2 in rule.subs:
            text.append(f"{indent}{glyphName1} > {glyphName2}")
        text.append("")

        for conditionSet in rule.conditionSets:
            conditionSetText = []
            for condition in conditionSet:
                conditionSetText.append(f"{condition['name']} {numberToString(condition['minimum'])}-{numberToString(condition['maximum'])}")
            text.append(indent + " ".join(conditionSetText))
        text.append("")
    return "\n".join(text)


def test_parseRules():
    expected = """
ruleName
    a > a.alt agrave > agrave.alt
    b > b.alt

    weight 800-1000 opsz 200-250
    width 100-300
"""
    result = parseRules(expected, designspaceLib.RuleDescriptor)


# def test_dumpRules():
#     glyphNames = ["a", "b", "c", "agrave", "b.alt", "ccedilla"]
#     expected = "a b c agrave b.alt ccedilla"
#     result = dumpRules(glyphNames)
#     assert expected == result


if __name__ == '__main__':
    import pytest
    pytest.main([__file__])


# ###

# rulersText = """

# # name of the rule
# rule name
#  # list of substitions
#  a > b c > a.grave
#  c > d
#  # conditions
#  wgth 800-1000
#  wdth 300.3-300.5


# rule name 2 with set
#     a > b
#     c > d

#     # conditions set (multiple)
#     wgth 800-1000 opsz 100-200
#     wdth 300-350

# """

# document = designspaceLib.DesignSpaceDocument()

# rules = parseRules(rulersText, document.writerClass.ruleDescriptorClass)
# print(rules)
# txt = dumpRules(rules)
# print(txt)

# rules2 = parseRules(txt, document.writerClass.ruleDescriptorClass)
# print(rules2)
# print(str(rules) == str(rules2))


