
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

print getDesignSpaceDocuments()

# see if we can find a designspace for the current UFO
f = CurrentFont()
if f is not None:
    for doc in getDesignSpaceDocuments():
        for sourceDescriptor in doc.doc.sources:
            if sourceDescriptor.path == f.path:
                print "yeah", doc
                # nu wat?
                
    
