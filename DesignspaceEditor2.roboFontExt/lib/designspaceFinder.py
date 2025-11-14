import glob, os, time
from pathlib import Path
from mojo.extensions import getExtensionDefault


try:
    from designspaceEditor import extensionIdentifier, DesignspaceEditorController
except ImportError:
    print("this really needs the DesignspaceEditor extension installed")

from designspaceEditor.ui import DesignspaceEditorController

# Useful docs
# https://docs.python.org/3/library/glob.html

# This is all VERY ROUGH

recentDocumentPathsKey = f"{extensionIdentifier}.recentDocumentPaths"

# idk if this is necessary, fonttools does it this way. 
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


def sourcePathsFromDesignspace(filename):
    # This usee elementtree to get to the source.filename attribute
    # without building the whole designspace.
    # Check if the ufoPath exists. 
    root = Path(filename).parent
    et = ET.parse(filename)	
    paths = []
    ds = et.getroot()
    sources_element = ds.find('sources')
    if sources_element is not None:
        for et in sources_element:
            p = et.attrib.get('filename')
            if p:
                ufoPath = (root / Path(p)).absolute()
                if ufoPath.exists():
                    paths.append(ufoPath)
    return paths
    
def findNearbyDesignspaces(ufoPath, verbose=False):
    # Check nearby directories for designspaces
    seenCount = 0
    ufoPath = Path(ufoPath)
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
            ab = Path(n).absolute()
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
    # Look through the recent documents of the DSE extension.
    seenCount = 0
    ufoPath = Path(ufoPath)
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



if __name__ == "__main__":
    f = CurrentFont()
    if f:
        start = time.time()        
        nearby = findNearbyDesignspaces(f.path, verbose=True)
        recent = findRecentDesignspaces(f.path, verbose=True)
        
        result = nearby + [d for d in recent if d not in nearby]
        
        if len(result) == 1:
            print(f"action: opening 1 result: {result[0]}")

            doc = None
            try:
                doc = OpenDesignspace(result[0])
            except AttributeError:
                print('(DSE issue opening the same doc twice)')
                
        elif len(result) > 1:
            print(f"action: show dialog for {len(result)} files")
            for p in result:
                print(f"\t\t{p}")

        else:
            print("regrets")
        
        print(f"(duration {time.time()-start})")