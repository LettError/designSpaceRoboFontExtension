
try:
    import install
except ImportError as e:
    print(e)
    # fails cause of the old version is alreayd installed
    from mojo.UI import dontShowAgainMessage

    dontShowAgainMessage(
        messageText="Designspace editor requires a RoboFont restart.",
        informativeText='',
        dontShowAgainKey="com.letterror.designspaceEditor"
    )