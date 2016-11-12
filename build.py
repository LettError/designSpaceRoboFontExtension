"""

    Build a robofont extension.


"""

import pprint
import os, shutil
import designspaceDocument

codeRoot = os.path.dirname(designspaceDocument.__file__)
print codeRoot
print os.path.exists(codeRoot)

editorRoot = os.path.dirname(__file__)
print "editorRoot", editorRoot, os.path.exists(editorRoot)

# copy the module
toolRoot = os.path.join(os.getcwd(), "DesignSpaceEditor.roboFontExt", "lib")
packageRoot = os.path.join(toolRoot, "designspaceDocument")
print os.path.exists(packageRoot)
if os.path.exists(packageRoot):
    shutil.rmtree(packageRoot)

# copy the other files
shutil.copytree(codeRoot, packageRoot, ignore=shutil.ignore_patterns("*.designspace"))

# files = [
#     'editor.py',
#     'toolbar_axes_m.pdf',
#     'newDesignspaceFIle.py',
#     'addDesignSpaceFileHandler.py']
# for name in files:
#     fileSrc = os.path.join(editorRoot, name)
#     print "fileSrc", fileSrc, os.path.exists(fileSrc)
#     fileDst = os.path.join(toolRoot, name)
#     if os.path.exists(fileDst):
#         os.remove(fileDst)
#     shutil.copyfile(fileSrc, fileDst)