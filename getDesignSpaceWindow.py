
from AppKit import *
from mojo.UI import *
from mojo.roboFont import CurrentFont, CurrentGlyph, AllFonts, OpenWindow

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
    
if __name__ == "__main__":
    result = CurrentDesignSpace()
    if result is not None:
        for font, location in result.getFonts():
            print location, font
        
        