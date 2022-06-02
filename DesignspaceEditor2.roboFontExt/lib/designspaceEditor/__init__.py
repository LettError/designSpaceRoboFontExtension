import AppKit


def CurrentDesignspace():
    for window in AppKit.NSApp().orderedWindows():
        delegate = window.delegate()
        if delegate:
            if hasattr(delegate, "vanillaWrapper"):
                vanillaWrapper = delegate.vanillaWrapper()
                if vanillaWrapper.__class__.__name__ == "DesignspaceEditorController":
                    return vanillaWrapper.document
    return None
