# open an existing designspace file with a dialog.

from vanilla.dialogs import *
from window import DesignSpaceEditor

if __name__ == "__main__":
    results = getFile(messageText="Open a designspace document:", allowsMultipleSelection=True, fileTypes=['designspace'])
    if results is not None:
        for path in results:
            OpenWindow(DesignSpaceEditor, path)
            #DesignSpaceEditor(path)
