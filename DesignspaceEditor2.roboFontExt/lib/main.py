
try:
    import install
except ImportError:
    # fails cause of the old version is alreayd installed
    from mojo.UI import dontShowAgainMessage

    dontShowAgainMessage(
        messageText="Designspace editor requires a RoboFont restart.",
        informativeText='',
        dontShowAgainKey="com.letterror.designspaceEditor"
    )