import pytest
import textwrap


commentSign = "#"


def getBlocks(text):
    """
    Split a text into indented blocks, intends could be a single space or multiple spaces or a tab
    """
    blocks = {}
    currentTag = None
    currentBlock = []
    for line in text.splitlines():
        if commentSign in line:
            line, comment = line.split(commentSign)
        line = line.rstrip()
        if not line:
            continue
        if line.startswith((" ", "\t")):
            currentBlock.append(line)
        else:
            if currentTag is not None:
                blocks[currentTag] = textwrap.dedent("\n".join(currentBlock))
                currentBlock = []
            currentTag = line

    if currentTag is not None:
        blocks[currentTag] = textwrap.dedent("\n".join(currentBlock))
    return blocks


def getLines(text):
    """
    Split a string in lines and strip white space. Ignore empty lines.
    """
    lines = []
    for line in text.splitlines():
        if commentSign in line:
            line, comment = line.split(commentSign)
        line = line.strip()
        if line:
            lines.append(line)
    return lines


def stringToNumber(n, fallback=None):
    if not n and isinstance(n, str):
        return fallback
    n = float(n)
    if n.is_integer():
        return int(n)
    return n


def numberToString(s):
    s = stringToNumber(s)
    if s is None:
        return None
    return str(s)


# tests

@pytest.mark.parametrize("text,expected", [
    ("", {}),
    ("foo\n bar\n more", {"foo": "bar\nmore"}),
    ("foo\n bar\n   more", {"foo": "bar\n  more"}),
    ("foo\n  bar\n  more", {'foo': 'bar\nmore'}),
    ("foo\n   bar\n  more", {'foo': ' bar\nmore'}),
    ("foo\n\tbar\n more", {'foo': '\tbar\n more'}),

    ("foo\n bar\n more\nhello\n world\nsecond\n    one\n    two\n    three", {"foo": "bar\nmore", "hello": "world", "second": "one\ntwo\nthree"}),
])
def test_getBlocks(text, expected):
    result = getBlocks(text)
    assert result == expected


@pytest.mark.parametrize("text,expected", [
    ("", []),
    ("this\nshould be\nsplitted\t\nin\u0020\u0020\u0020\nparts", ['this', 'should be', 'splitted', 'in', 'parts'])
])
def test_getLines(text, expected):
    result = getLines(text)
    assert result == expected


@pytest.mark.parametrize("astring,expected", [
    ("", None),
    ("10", 10),
    ("10.0", 10),
    ("10.5", 10.5),
])
def test_stringToNumber(astring, expected):
    result = stringToNumber(astring)
    assert result == expected


@pytest.mark.parametrize("anumber,expected", [
    ("", None),
    (10, "10"),
    (10.0, "10"),
    (10.5, "10.5"),
])
def test_numberToString(anumber, expected):
    result = numberToString(anumber)
    print(anumber, result)
    assert result == expected


if __name__ == '__main__':
    pytest.main([__file__])
