import glob, os, time
from pathlib import Path
from mojo.extensions import getExtensionDefault

from designspaceEditor import extensionIdentifier
from designspaceEditor.ui import DesignspaceEditorController

# Useful docs
# https://docs.python.org/3/library/glob.html

# This is all VERY ROUGH

# idk if this is necessary, fonttools does it this way. 
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


def sourcePathsFromDesignspace(filename):
    '''
    Check if the ufo path exists in the designspace’s source.
    This usee elementtree to get to the source.filename attribute
    without building the whole designspace.
    '''
    paths = []
    if Path(filename).suffix == ".designspace":
        root = Path(filename).parent
        try:
            et = ET.parse(filename)	
            ds = et.getroot()
            sources_element = ds.find('sources')
            if sources_element is not None:
                for et in sources_element:
                    p = et.attrib.get('filename')
                    if p:
                        ufoPath = (root / p).resolve()
                        if ufoPath.exists():
                            paths.append(ufoPath)
        except:
            print(f"Note: failed to read designspace {filename}. You might want to check that one.")
    return paths
    
def findNearbyDesignspaces(ufoPath, verbose=False):
    '''Check nearby directories for designspaces'''
    seenCount = 0
    ufoPath = Path(ufoPath).resolve()
    ufoParent = ufoPath.parent
    deep = len(ufoPath.parents)
    patterns = [
        '',            # same level
    ]
    patterns.append('../')    # one up
    #patterns.append('../**/')    # search folders at the same level, then down. Can be expensive.
    if deep > 3:
        # check this number
        # the idea is to make sure we have a minimum depth before looking at folders up. 
        # because /User/<user>/.. folders may be restricted.
        # check with test folder on desktop and downloads
        patterns.append('../../')    # two up
    if verbose:
        print("Patterns", patterns)
    candidates = []
    for pat in patterns:
        for n in ufoParent.glob(pat + '*.designspace'):
            print('>>', Path(n), Path(n).resolve())
            ab = Path(n).resolve()
            if ab not in candidates:
                candidates.append(ab)
    results = []
    for s in candidates:
        seenCount += 1
        sourcePaths = sourcePathsFromDesignspace(s)
        if ufoPath in sourcePaths:
            if s not in results:
                results.append(str(s))
    if verbose:
        print(f"\tlooked at {seenCount} nearby files")
        print(f"\t\tfound {len(results)} candidates")
    return results

def findRecentDesignspaces(ufoPath, verbose=False):
    '''Look through the recent documents of the DSE extension.'''
    recentDocumentPathsKey = f"{extensionIdentifier}.recentDocumentPaths"
    seenCount = 0
    ufoPath = Path(ufoPath).resolve()
    results = []
    other = []
    missing = []
    for docPath in getExtensionDefault(recentDocumentPathsKey, []):
        if not ".designspace" in docPath: continue    # it happens, apparently
        if not os.path.exists(docPath):
            missing.append(docPath)
            continue
        seenCount += 1
        sourcePaths = sourcePathsFromDesignspace(docPath)
        if ufoPath in sourcePaths:
            results.append(str(docPath))
    if verbose:
        print(f"\tlooked at {seenCount} recent files")
        print(f"\t\tfound {len(results)} candidates")
    return results

