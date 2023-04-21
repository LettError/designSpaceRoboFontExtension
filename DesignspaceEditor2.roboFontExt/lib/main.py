import builtins
import os

import AppKit

from mojo.events import addObserver
from mojo.extensions import ExtensionBundle
from mojo.subscriber import registerSubscriberEvent
from designspaceEditor.ui import DesignspaceEditorController


oldBundle = ExtensionBundle("DesignSpaceEdit")

if oldBundle.bundleExists():
    from vanilla.dialogs import message
    message(
        "Found older version of Designspace edit.",
        "An old version of Designspace edit is still installed. This can cause issues while opening designspace files."
    )


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


def CurrentDesignspace():
    for window in AppKit.NSApp().orderedWindows():
        delegate = window.delegate()
        if hasattr(delegate, "vanillaWrapper"):
            controller = delegate.vanillaWrapper()
            if controller.__class__.__name__ == "DesignspaceEditorController":
                return controller.operator
    return None


builtins.CurrentDesignspace = CurrentDesignspace


# register subscriber events

designspaceEvents = [
    # document
    "designspaceEditorWillOpenDesignspace",
    "designspaceEditorDidOpenDesignspace",
    "designspaceEditorDidCloseDesignspace",

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
    "designspaceEditorSourcesDidChanged",

    # instances
    "designspaceEditorInstancesWillRemoveInstance",
    "designspaceEditorInstancesDidRemoveInstance",

    "designspaceEditorInstancesWillAddInstance",
    "designspaceEditorInstancesDidAddInstance",

    "designspaceEditorInstancesDidChangeSelection",

    "designspaceEditorInstancesDidOpen",
    "designspaceEditorInstancesDidChange",

    # rules
    "designspaceEditorRulesDidChange",

    # labels
    "designspaceEditorLabelsDidChange",

    # notes
    "designspaceEditorNotesDidChange",

    # any change
    "designspaceEditorDidChange",
]


def designspaceEventExtractor(subscriber, info):
    info["designspace"] = info["lowLevelEvents"][-1].get("designspace")


def designspaceSelectionEventExtractor(subscriber, info):
    designspaceEventExtractor(subscriber, info)
    info["selectedItems"] = info["lowLevelEvents"][-1]["selectedItems"]


eventInfoExtractionFunctionsMap = dict(
    designspaceEditorAxesDidChangeSelection=designspaceSelectionEventExtractor,
    designspaceEditorSourcesDidChangeSelection=designspaceSelectionEventExtractor,
    designspaceEditorInstancesDidChangeSelection=designspaceSelectionEventExtractor
)

for event in designspaceEvents:
    documentation = "".join([" " + c if c.isupper() else c for c in event.replace("designspaceEditor", "")]).lower().strip()
    registerSubscriberEvent(
        subscriberEventName=event,
        methodName=event,
        lowLevelEventNames=[event],
        dispatcher="roboFont",
        documentation=f"Send when a Designspace Editor {documentation}.",
        eventInfoExtractionFunction=eventInfoExtractionFunctionsMap.get(event, designspaceEventExtractor),
        delay=.2,
        debug=True
    )
