
"""

Run some tests on the designspace.
Some sort of validator

"""

class DesignSpaceProblem(object):
    _categories = {
        0: "file",
        1: "designspace geometry",
        2: "sources",
        3: "instances",
        4: "glyphs",
        5: "kerning",
        6: "font info",
        7: "rules",
        }
    # problems that should prevent the designspace from doing anything
    _structural = [
        (0,0),
        (1,0),(1,1),(1,2),(1,3),(1,4),(1,5),
        (1,9),(1,10),
        (2,0),(2,4),(2,7), (2,8),(2,9),(2,10),
        ]

    _problems = {
        # 0 file 
        (0,0): "file corrupt",

        # 1 designspace geometry
        (1,0):  "no axes defined",
        (1,1):  "axis missing",
        (1,2):  "axis maximum missing",
        (1,3):  "axis minimum missing",
        (1,4):  "axis default missing",
        (1,5):  "axis name missing",
        (1,6):  "axis tag missing",
        (1,7):  "axis tag mismatch",

        (1,9):  "minimum and maximum value are the same",
        (1,10): "default not between minimum and maximum",
        (1,11): "mapped axis has overlapping input values (userspace)",
        (1,12): "mapped axis has overlapping output values (designspace)",
        (1,13): "mapped minimum > mapped maximum",
        (1,14): "axis minimum > axis maximum",

        # 2 sources
        (2,0):  "no sources defined",
        (2,1):  "source UFO missing",
        (2,2):  "source UFO format too old, recommend update.",
        (2,3):  "source layer missing",
        (2,4):  "source location missing",
        (2,5):  "source location has value for undefined axis",
        (2,6):  "source location has out of bounds value",
        (2,7):  "no source on unmapped default location",
        (2,12): "no source on mapped default location",
        (2,8):  "multiple sources on default location",
        (2,9):  "multiple sources on location",
        (2,10): "source location is anisotropic",
        (2,11): "axis without on-axis sources",

        # 3 instances
        (3,1):  'instance location missing',
        (3,2):  "instance location has value for undefined axis",
        (3,3):  "instance location has out of bounds value",
        (3,4):  "multiple instances on location",
        (3,5):  "instance location requires extrapolation",
        (3,9):  "instance location is anisotropic",
        (3,6):  "missing family name",
        (3,7):  "missing style name",
        (3,8):  "missing output path",
        (3,10): "no instances defined",
        
        # 4 glyphs
        (4,0): 'different number of contours in glyph',
        (4,1): 'different components in glyph',
        (4,2): 'different anchors in glyph',
        (4,3): 'different number of on-curve points on contour',
        (4,4): 'different number of off-curve points on contour',
        (4,5): 'curve has wrong type',
        (4,6): 'non-default glyph is empty',
        (4,7): 'default glyph is empty',
        (4,8): 'contour has wrong direction',
        (4,9): 'incompatible constructions for glyph',
        (4,10): 'different unicodes in glyph',

        # 5 kerning
        (5,0): 'no kerning in source',
        (5,1): 'no kerning in default',
        (5,2): 'kerning group members do not match',
        (5,3): 'kerning group missing in default',
        (5,4): 'kerning pair missing',
        (5,5): 'no kerning groups in default',
        (5,6): 'no kerning groups in source',
        (5,7): 'kerning group members sorted differently',

        # 6 font info
        (6,0): 'default font info missing value for units per em',
        (6,1): 'default font info missing value for ascender',
        (6,2): 'default font info missing value for descender',
        (6,3): 'default font info missing value for xheight',
        (6,4): 'source font unitsPerEm value different from default unitsPerEm',

        # 7 rules
        (7,0): 'source glyph missing',
        (7,1): 'destination glyph missing',
        (7,2): 'source and destination glyphs the same',
        (7,3): 'no substition glyphs defined',
        (7,4): 'no conditionset defined',
        (7,5): 'condition values on unknown axis',
        (7,6): 'condition values out of axis bounds',
        (7,7): 'condition values are the same',
        (7,8): 'duplicate conditions',
        (7,9): 'rule without a name',
        (7,10): 'condition with missing minimum',
        (7,11): 'condition with missing maximum',
        }
        
    def __init__(self, category=None, error=None, data=None, details=None):
        self.category = category
        self.problem = error
        self.data = data
        self.details = details
    
    def __eq__(self, otherProblem):
        # this way we can test membership in a list
        if type(otherProblem) == tuple:
            return otherProblem == (self.category, self.problem)
        return (otherProblem.category,  otherProblem.error) == (self.category, self.problem)

    def isStructural(self):
        # return True if the problem is "structural"
        # this means: the designspace is too broken to perform any kind of calculation
        return (self.category, self.problem) in self._structural

    def getDescription(self):
        t = []
        key = (self.category, self.problem)
        if self.category in self._categories:
            t.append(self._categories.get(self.category))
        if key in self._problems:
            t.append(self._problems.get(key))
        #if self.details is not None:
        #    t.append(self.details)
        return t

    def __repr__(self):
        t = []
        key = (self.category, self.problem)
        if self.category in self._categories:
            t.append(self._categories.get(self.category))
        if key in self._problems:
            t.append(self._problems.get(key))
        dt = ""
        if self.details is not None:
            dt += self.details
        if self.data is not None:
            dt += ", "+ ' '.join("%s: %s" % (a, b) for a, b in self.data.items())
        return '[' + ": ".join(t) + dt + ' %s' % str(key) + ']'
            
def allProblems():
    e = DesignSpaceProblem()
    return e._problems
    
def makeErrorDocumentationTable():
    # write the categories and the errors in a .md file
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())), 'problems.md')
    t = ["# problem categories"]
    e = DesignSpaceProblem()
    cats = list(e._categories.keys())
    cats.sort()
    for cat in cats:
        t.append("  * `%d. %s`" % (cat, e._categories[cat]))
    errs = list(e._problems.keys())
    errs.sort()
    lastCat = None
    for cat, err in errs:
        if cat != lastCat:
            t.append("\n## %d. %s\n" % (cat, e._categories[cat]))
            lastCat = cat
        t.append("  * `%d.%d\t%s`" % (cat, err, e._problems[(cat,err)]))
    f = open(path, 'w')
    f.write("\n".join(t))
    f.close()
    
def makeFunctions(whiteSpace=None):
    # make descriptive function names
    modl = ["# generated from problems.py", 'from designspaceProblems.problems import DesignSpaceProblem']
    if whiteSpace is None:
        whiteSpace = "    "
    text = []
    for key, desc in allProblems().items():
        new = []
        for i, p in enumerate(desc.split(" ")):
            if i == 0:
                new.append(p)
            else:
                t = p[0].upper()+ p[1:]
                new.append(t)
        new.append("Problem")
        new = ''.join(new)
        new = new.replace('-', '')
        new = new.replace(',', '')
        new = new.replace('.', '')
        new = new.replace('(', '_')
        new = new.replace(')', '_')
        new = new.replace('>', '_')
        new = new.replace('<', '_')
        func = "def %s(**kwargs):\n%s# %s, %s\n%sreturn DesignSpaceProblem(%d,%d,data=kwargs)\n" % (''.join(new), whiteSpace, desc, key, whiteSpace, key[0], key[1])
        modl.append(func)
    path = "./problemFunctions.py"
    f = open(path, 'w')
    f.write("\n".join(modl))
    f.close()
        
def testCompare():
    # test the error comparing thing
    for key1, desc1 in allProblems().items():
        for key2, desc2 in allProblems().items():
            e1 = DesignSpaceProblem(*key1, dict(item1=1, item2=2))
            e2 = DesignSpaceProblem(*key2, dict(item1=3, item2=4))
            if e1 == e2:
                print(key1, key2, e1 == e2)
                print(e1.data)

def showStructuralProblems():
    # show which problems are marked as structural and which arent
    e = DesignSpaceProblem()
    s = []
    ns = []
    for k, v in e._problems.items():
        if k in e._structural:
            s.append((k, v))
        else:
            ns.append((k,v))
    print("These problems are marked as structural, and will prevent the file from opening")
    for k, v in s:
        print("\t%s:\t%s" %(k, v))
    print("\nThese problems are NOT marked as structural")
    for k, v in ns:
        print("\t%s:\t%s" %(k, v))

if __name__ == "__main__":
    #makeFunctions()
    makeErrorDocumentationTable()
    showStructuralProblems()
    #testCompare()
    pass
