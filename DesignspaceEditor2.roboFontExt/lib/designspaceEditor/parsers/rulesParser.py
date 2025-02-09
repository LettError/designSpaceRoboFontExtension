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


rulesLibKey = "com.letterror.designspaceEditor.rules.text"


def parseRules(text, ruleDescriptorClass=None):
    if ruleDescriptorClass is None:
        ruleDescriptorClass = designspaceLib.RuleDescriptor
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


def extractRules(operator, indent="    "):
    """
    Extract rules to a string for a given operator:
    check if rules is stored as a string in the lib,
    parse that stored string and compare with the internal rules.

    Compare with ignore the rules order.

    If there is no difference, use the string representation.

    This will preseve comments and white space.
    """
    storedText = operator.lib.get(rulesLibKey, "")
    parsed = parseRules(storedText)

    if sorted([list(item.asdict().items()) for item in parsed]) == sorted([list(item.asdict().items()) for item in operator.rules]):
        return storedText
    return dumpRules(operator.rules, indent=indent)


def storeRules(text, operator):
    """
    Store rules as objects from a string for a given operator and
    store the rules string representation in the operator lib.
    """
    parsed = parseRules(text, operator.writerClass.ruleDescriptorClass)
    operator.lib[rulesLibKey] = text
    operator.rules.clear()
    operator.rules.extend(parsed)


# tests

def test_parseRules():
    expected = """
ruleName
    a > a.alt agrave > agrave.alt
    b > b.alt

    weight 800-1000 opsz 200-250
    width 100-300
"""
    result = parseRules(expected, designspaceLib.RuleDescriptor)
    assert len(result) == 1
    descriptor = result[0]
    assert descriptor.name == "ruleName"
    assert descriptor.subs == [("a", "a.alt"), ("agrave", "agrave.alt"), ("b", "b.alt")]


def test_Rules():
    expected = [designspaceLib.RuleDescriptor(name="ruleName", subs=[("a", "a.alt")])]
    result = dumpRules(expected)
    rules = parseRules(result, designspaceLib.RuleDescriptor)
    assert len(expected) == len(rules)
    assert expected[0].name == rules[0].name
    assert expected[0].subs == rules[0].subs


if __name__ == '__main__':
    import pytest
    pytest.main([__file__])
