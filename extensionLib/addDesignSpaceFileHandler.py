
from mojo.events import addObserver
from designSpaceEditorwindow import DesignSpaceEditor

import os

def getDesignSpaceDocuments():
    """ Try to find designspace windows."""
    designSpaces = []
    windows = [w for w in NSApp().orderedWindows() if w.isVisible()]
    for window in windows:
        delegate = window.delegate()
        if not hasattr(delegate, "vanillaWrapper"):
            continue            
        vanillaWrapper = delegate.vanillaWrapper()
        if vanillaWrapper.__class__.__name__ == "DesignSpaceEditor":
            designSpaces.append(vanillaWrapper)
    return designSpaces

# see if we can find a designspace for the current UFO
def CurrentDesignSpace():
    docs = getDesignSpaceDocuments()
    # can we find the designspace that belongs to the currentfont?
    f = CurrentFont()
    if f is not None:
        for doc in docs:
            for sourceDescriptor in doc.doc.sources:
                if sourceDescriptor.path == f.path:
                    return doc.doc
    # if we have no currentfont, can we find the designspace that is the first?
    if docs:
        return docs[0].doc
    # we have no open fonts, no open docs
    return None

# install the designspaceeditor as a tool for this filetype,
class DesignSpaceOpener(object):
    def __init__(self):
        addObserver(self, "openFile", "applicationOpenFile")
    def openFile(self, notification):
        fileHandler = notification["fileHandler"]
        path = notification["path"]
        ext = os.path.splitext(path)[-1]
        if ext.lower() != ".designspace":
            return
        DesignSpaceEditor(path)
        fileHandler["opened"] = True

# install the designspace opener, but only if we don't have skateboard installed already
try:
    import skateboard
except ImportError:
    try:
        DesignSpaceOpener()
    except:
        print("Could not add DesignSpaceOpener.")
