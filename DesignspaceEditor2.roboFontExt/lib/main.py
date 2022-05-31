from mojo.events import addObserver
from dse.ui import DesignspaceEditorController

import os


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
