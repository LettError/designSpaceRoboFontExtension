from mojo.UI import GetFile
from designspaceEditor.ui import DesignspaceEditorController


paths = GetFile(
    message="Open a designspace document:",
    allowsMultipleSelection=True,
    fileTypes=['designspace'],
)

if paths:
    for path in paths:
        DesignspaceEditorController(path)
