
from mojo.events import addObserver
from designSpaceEditorwindow import DesignSpaceEditor

import os
# install the designspaceeditor as a tool for this filetype,
class DesignSpaceOpener(object):
    def __init__(self):
        addObserver(self, "openFile", "applicationOpenFile")
    def openFile(self, notification):
        fileHandler = notification["fileHandler"]
        path = notification["path"]
        ext = os.path.splitext(path)[-1]
        if ext.lower() != ".designspace":
            return
        DesignSpaceEditor(path)
        fileHandler["opened"] = True
    
DesignSpaceOpener()

# install the sparks tool
from mojo.events import installTool
from showSparksTool import ShowSparksTool
p = ShowSparksTool()
installTool(p)

