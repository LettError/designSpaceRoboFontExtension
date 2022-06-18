import textwrap


commentSign = "#"


def getBlocks(text):
    blocks = {}
    currentTag = None
    currentBlock = []
    for line in text.splitlines():
        if commentSign in line:
            line, comment = line.split(commentSign)
        line = line.rstrip()
        if not line:
            continue

        if line.startswith(" "):
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
    lines = []
    for line in text.splitlines():
        if commentSign in line:
            line, comment = line.split(commentSign)
        line = line.strip()
        if line:
            lines.append(line)
    return lines


def stringToNumber(n):
    if not n and isinstance(n, str):
        return None
    n = float(n)
    if n.is_integer():
        return int(n)
    return n


def numberToString(s):
    s = stringToNumber(s)
    if s is None:
        return None
    return str(s)


# t = """
# foo
#    bar
#   more

# other thing
#  small indent
#  more
# second
#      test
#      test
# """



# print(getBlocks(t))