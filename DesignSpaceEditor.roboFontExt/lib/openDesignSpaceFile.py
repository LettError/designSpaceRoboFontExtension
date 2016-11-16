# open an existing designspace file with a dialog.

from vanilla.dialogs import *
from editor import DesignSpaceEditor

if __name__ == "__main__":
    for path in getFile(messageText="Open a designspace document:",
        allowsMultipleSelection=True,
        fileTypes=['designspace']):
        DesignSpaceEditor(path)
