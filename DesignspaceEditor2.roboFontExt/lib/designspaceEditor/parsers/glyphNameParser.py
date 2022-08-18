"""
# glyphname text spec

<glyphName> <glyphName> ...
"""


def parseGlyphNames(text):
    return [glyphName.strip() for glyphName in text.split()]


def dumpGlyphNames(glyphNames):
    return " ".join(glyphNames)


# tests

def test_parseGlyphNames():
    text = "a b c agrave \tb.alt     ccedilla"
    expected = ["a", "b", "c", "agrave", "b.alt", "ccedilla"]
    result = parseGlyphNames(text)
    assert expected == result


def test_dumpGlyphNames():
    glyphNames = ["a", "b", "c", "agrave", "b.alt", "ccedilla"]
    expected = "a b c agrave b.alt ccedilla"
    result = dumpGlyphNames(glyphNames)
    assert expected == result


if __name__ == '__main__':
    import pytest
    pytest.main([__file__])
