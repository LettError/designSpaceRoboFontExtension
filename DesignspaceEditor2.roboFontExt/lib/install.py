import builtins
import os

import AppKit

from mojo.tools import CallbackWrapper
from mojo.events import addObserver
from mojo.extensions import ExtensionBundle, getExtensionDefault, setExtensionDefault
from mojo.subscriber import registerSubscriberEvent, Subscriber, registerRoboFontSubscriber
from mojo.UI import GetFile

from designspaceEditor.ui import DesignspaceEditorController, DesignspaceEditorOperator
from designspaceEditor import extensionIdentifier

# checking older version of the Designspace Editor and warn
oldBundle = ExtensionBundle("DesignSpaceEdit")

if oldBundle.bundleExists():
    from vanilla.dialogs import message
    message(
        "Found older version of Designspace edit.",
        "An old version of Designspace edit is still installed. This can cause issues while opening designspace files."
    )


# opening a designspace file by dropping on RF

class DesignspaceOpener(object):

    def __init__(self):
        addObserver(self, "openFile", "applicationOpenFile")

    def openFile(self, notification):
        fileHandler = notification["fileHandler"]
        path = notification["path"]
        ext = os.path.splitext(path)[-1]
        if ext.lower() != ".designspace":
            return
        DesignspaceEditorController(path)
        fileHandler["opened"] = True


DesignspaceOpener()


# api callback

def _allDesignspaceWindows(usingFont=None):
    for window in AppKit.NSApp().orderedWindows():
        delegate = window.delegate()
        if hasattr(delegate, "vanillaWrapper"):
            controller = delegate.vanillaWrapper()
            if controller.__class__.__name__ == "DesignspaceEditorController" and controller.operator is not None:
                if usingFont is not None:
                    if controller.operator.usesFont(usingFont):
                        yield controller
                else:
                    yield controller


def AllDesignspaceWindows(usingFont=None):
    """
    Return a tuple of all open Designspace windows.

    optionally provide `usingFonts`.
    """
    return tuple(_allDesignspaceWindows(usingFont=usingFont))


def AllDesignspaces(usingFont=None):
    """
    Return a tuple of all open Designspace operators.

    optionally provide `usingFonts`.
    """
    return tuple(controller.operator for controller in _allDesignspaceWindows(usingFont=usingFont))


def RelevantDesignspaces(usingFont, layerName=None):
    """
    Return a tuple of all relevant Designspace operators for a given `usingFont`/

    optionally provide a `layerName`.
    """
    layerNames = [layerName]
    if layerName in None:
        layerNames.append(usingFont.defaultLayerName)
    relevantDesignspaces = []
    for designspace in AllDesignspaces(usingFont):
        for source in designspace.sources:
            if source.path == usingFont.path and source.layerName in layerNames:
                continuousLocation, discreteLocation = designspace.splitLocation(source.location)
                if discreteLocation:
                    relevantDesignspaces.append((designspace, discreteLocation))
                elif continuousLocation is not None:
                    relevantDesignspaces.append((designspace, None))
    return tuple(relevantDesignspaces)


def CurrentDesignspace():
    """
    Return the current Designspace operator.
    """
    for controller in _allDesignspaceWindows():
        return controller.operator
    return None


def CurrentDesignspaceWindow():
    """
    Return the current Dresignspace window.
    """
    for controller in _allDesignspaceWindows():
        return controller
    return None


def OpenDesignspace(path, showInterface=True):
    """
    Opens and return a Designspace from path.

    optionally provide `showInterface` (default True) to open the UI.
    """
    if showInterface:
        controller = DesignspaceEditorController(path)
        return controller.operator
    else:
        operator = DesignspaceEditorOperator(extrapolate=True)
        operator.read(path)
        return operator


def NewDesignspace(showInterface=True):
    """
    Create a new Designspace.

    optionally provide `showInterface` (default True) to open the UI.
    """
    if showInterface:
        controller = DesignspaceEditorController()
        return controller.operator
    else:
        operator = DesignspaceEditorOperator(extrapolate=True)
        return operator


builtins.AllDesignspaceWindows = AllDesignspaceWindows
builtins.AllDesignspaces = AllDesignspaces
builtins.RelevantDesignspaces = RelevantDesignspaces
builtins.CurrentDesignspace = CurrentDesignspace
builtins.CurrentDesignspaceWindow = CurrentDesignspaceWindow
builtins.OpenDesignspace = OpenDesignspace
builtins.NewDesignspace = NewDesignspace


# menu

recentDocumentPathsKey = f"{extensionIdentifier}.recentDocumentPaths"
maxRecentDocuments = 10


class DesignspaceMenuSubscriber(Subscriber):

    debug = True

    def build(self):
        self.buildDesignspaceMenuItems()

    def roboFontDidFinishLaunching(self, notification):
        self.buildDesignspaceMenuItems()

    def buildDesignspaceMenuItems(self):
        mainMenu = AppKit.NSApp().mainMenu()
        fileMenu = mainMenu.itemWithTitle_("File")
        if not fileMenu:
            return
        self.fileMenu = fileMenu.submenu()

        titles = [
            ("New Designspace", self.newDesignspaceMenuCallback),
            ("Open Designspace...", self.openDesignspaceMenuCallback),
            ("Open Recent Designspace", None),
        ]

        # remove the existing items
        # XXX this may not be needed in real usage
        for title, callback in titles:
            existing = self.fileMenu.itemWithTitle_(title)
            if existing:
                self.fileMenu.removeItem_(existing)

        # build the new items
        index = self.fileMenu.indexOfItemWithTitle_("Open Recent")
        self.targets = []
        for title, callback in reversed(titles):
            action = None
            target = None
            if callback is not None:
                target = CallbackWrapper(callback)
                self.targets.append(target)
                action = "action:"
            newItem = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, "")
            if target is not None:
                newItem.setTarget_(target)
            else:
                self.openRecentSubmenu = AppKit.NSMenu.alloc().init()
                newItem.setSubmenu_(self.openRecentSubmenu)
            self.fileMenu.insertItem_atIndex_(newItem, index + 1)
        self.fileMenu.insertItem_atIndex_(AppKit.NSMenuItem.separatorItem(), index + 1)
        self.recentDocumentPaths = getExtensionDefault(recentDocumentPathsKey, [])
        self.openRecentDesignspaceTarget = CallbackWrapper(self.openRecentDesignspageMenuCallback)
        self.clearRecentDesignspaceTarget = CallbackWrapper(self.clearRecentDesignspaceMenuCallback)
        self.populateOpenRecentDesignspaceSubmenu()

    # New

    def newDesignspaceMenuCallback(self, sender):
        DesignspaceEditorController()

    # Open

    def openDesignspaceMenuCallback(self, sender):
        paths = GetFile(
            message="Open a designspace document:",
            allowsMultipleSelection=True,
            fileTypes=['designspace'],
        )

        if paths:
            for path in paths:
                DesignspaceEditorController(path)

    # Recent

    def populateOpenRecentDesignspaceSubmenu(self):
        self.openRecentSubmenu.removeAllItems()
        for path in self.recentDocumentPaths:
            if not os.path.exists(path):
                continue
            item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(os.path.basename(path), "action:", "")
            item.setRepresentedObject_(path)
            item.setTarget_(self.openRecentDesignspaceTarget)
            self.openRecentSubmenu.addItem_(item)
        self.openRecentSubmenu.addItem_(AppKit.NSMenuItem.separatorItem())
        clearItem = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Clear Menu", "action:", "")
        clearItem.setTarget_(self.clearRecentDesignspaceTarget)
        self.openRecentSubmenu.addItem_(clearItem)

    def openRecentDesignspageMenuCallback(self, sender):
        path = sender.representedObject()
        DesignspaceEditorController(path)

    def clearRecentDesignspaceMenuCallback(self, sender):
        self.recentDocumentPaths = []
        self.storeRecentDesignspacePaths()
        self.populateOpenRecentDesignspaceSubmenu()

    def storeRecentDesignspacePaths(self):
        setExtensionDefault(recentDocumentPathsKey, self.recentDocumentPaths)

    def designspaceEditorDidOpenDesignspace(self, info):
        designspace = info["designspace"]
        path = designspace.path
        if path is not None:
            self.addPathToRecentDocuments(path)
            self.populateOpenRecentDesignspaceSubmenu()

    def designspaceEditorDidCloseDesignspace(self, info):
        designspace = info["designspace"]
        path = designspace.path
        if path is not None:
            self.addPathToRecentDocuments(path)
            self.populateOpenRecentDesignspaceSubmenu()

    def addPathToRecentDocuments(self, path):
        if path in self.recentDocumentPaths:
            self.recentDocumentPaths.remove(path)
        self.recentDocumentPaths.insert(0, path)
        self.storeRecentDesignspacePaths()


# register subscriber events

designspaceEvents = [
    # document
    "designspaceEditorWillOpenDesignspace",
    "designspaceEditorDidOpenDesignspace",
    "designspaceEditorDidCloseDesignspace",

    "designspaceEditorDidBecomeCurrent",
    "designspaceEditorDidResignCurrent",

    # axis
    "designspaceEditorAxisLabelsDidChange",
    "designspaceEditorAxisMapDidChange",

    "designspaceEditorAxesWillRemoveAxis",
    "designspaceEditorAxesDidRemoveAxis",

    "designspaceEditorAxesWillAddAxis",
    "designspaceEditorAxesDidAddAxis",

    "designspaceEditorAxesDidChangeSelection",
    "designspaceEditorAxesDidChange",

    # sources
    "designspaceEditorSourcesWillRemoveSource",
    "designspaceEditorSourcesDidRemoveSource",

    "designspaceEditorSourcesWillAddSource",
    "designspaceEditorSourcesDidAddSource",

    "designspaceEditorSourcesDidChangeSelection",

    "designspaceEditorSourcesDidCloseUFO",
    "designspaceEditorSourcesDidOpenUFO",
    "designspaceEditorSourcesDidChange",

    # instances
    "designspaceEditorInstancesWillRemoveInstance",
    "designspaceEditorInstancesDidRemoveInstance",

    "designspaceEditorInstancesWillAddInstance",
    "designspaceEditorInstancesDidAddInstance",

    "designspaceEditorInstancesDidChangeSelection",

    "designspaceEditorInstancesDidChange",

    # rules
    "designspaceEditorRulesDidChange",

    # location labels
    "designspaceEditorLocationLabelsDidChange",

    # variable fonts
    "designspaceEditorVariableFontsDidChange",

    # notes
    "designspaceEditorNotesDidChange",

    # preview location
    "designspaceEditorPreviewLocationDidChange",

    # save designspace
    "designspaceEditorDidSaveDesignspace",

    # any change
    "designspaceEditorDidChange",

    # =====================
    # = font data changes =
    # =====================

    # any font data change
    # "designspaceEditorSourceDataDidChange",

    # glyph
    "designspaceEditorSourceGlyphDidChange",

    # font info
    "designspaceEditorSourceInfoDidChange",

    # font kerning
    "designspaceEditorSourceKerningDidChange",

    # font groups
    "designspaceEditorSourceGroupsDidChange",

    # external change, outside of RoboFont
    "designspaceEditorSourceFontDidChangedExternally",
]


def designspaceEventExtractor(subscriber, info):
    attributes = [
        "designspace",
        "axis",
        "source",
        "instance",
        "location",
        "selectedItems",
        "glyph"
    ]
    for attribute in attributes:
        data = info["lowLevelEvents"][-1]
        if attribute in data:
            info[attribute] = data[attribute]


def designspaceEditorEventEligibility(subscriber, notification):
    if not hasattr(subscriber, "operator"):
        return True
    elif "designspace" not in notification:
        return True
    return notification["designspace"] == subscriber.operator


for event in designspaceEvents:
    documentation = "".join([" " + c if c.isupper() else c for c in event.replace("designspaceEditor", "")]).lower().strip()
    registerSubscriberEvent(
        subscriberEventName=event,
        methodName=event,
        lowLevelEventNames=[event],
        dispatcher="roboFont",
        documentation=f"Send when a Designspace Editor {documentation}.",
        eventInfoExtractionFunction=designspaceEventExtractor,
        eventEligibilityFunction=designspaceEditorEventEligibility,
        delay=.2,
        debug=True
    )

registerRoboFontSubscriber(DesignspaceMenuSubscriber)
