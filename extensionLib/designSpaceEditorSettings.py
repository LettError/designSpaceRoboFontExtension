from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.extensions import getExtensionDefault, setExtensionDefault, ExtensionBundle
from vanilla import *

defaultOptions = {
    "instanceFolderName": "instances",
}

settingsIdentifier = "com.letterror.designspaceeditor"

def updateWithDefaultValues(data, defaults):
    for key, value in defaults.items():
        if key in data:
            continue
        data[key] = value

class Settings(BaseWindowController):

    identifier = "%s.%s" % (settingsIdentifier, "general")

    def __init__(self, parentWindow, callback=None):
        
        self.doneCallback = callback
        data = getExtensionDefault(self.identifier, dict())
        updateWithDefaultValues(data, defaultOptions)

        width = 380
        height = 1000

        self.w = Sheet((width, height), parentWindow=parentWindow)

        y = 10
        self.w.instanceFolderNameEdit = EditText((160, y, -10, 20), data['instanceFolderName'], sizeStyle="small")
        self.w.instanceFolderNameCaption = TextBox((10, y+3, 180, 20), "Instance folder name", sizeStyle="small")
        # self.w.threaded = CheckBox((10, y, -10, 22), "Threaded", value=data["threaded"])

        y += 30
        # self.w.exportInFolders = CheckBox((10, y, -10, 22), "Export in Sub Folders", value=data["exportInFolders"])

        y += 30
        # self.w.keepFileNames = CheckBox((10, y, -10, 22), "Keep file names (otherwise use familyName-styleName)", value=data["keepFileNames"])

        y += 35
        self.w.saveButton = Button((-100, y, -10, 20), "Save settings", callback=self.saveCallback, sizeStyle="small")
        self.w.setDefaultButton(self.w.saveButton)

        self.w.closeButton = Button((-190, y, -110, 20), "Cancel", callback=self.closeCallback, sizeStyle="small")
        self.w.closeButton.bind(".", ["command"])
        self.w.closeButton.bind(chr(27), [])

        self.w.resetButton = Button((-280, y, -200, 20), "Reset", callback=self.resetCallback, sizeStyle="small")

        y += 30
        self.w.resize(width, y, False)

        self.w.open()

    def resetCallback(self, sender):
        self.w.instanceFolderName = "instances"
        self.w.instanceFolderNameEdit.set(self.w.instanceFolderName)
        #self.w.threaded.set(defaultOptions["threaded"])
        #self.w.exportInFolders.set(defaultOptions["exportInFolders"])

    def saveCallback(self, sender):
        data = {
            "instanceFolderName": self.w.instanceFolderNameEdit.get(),
            #"exportInFolders": self.w.exportInFolders.get(),
            #"keepFileNames": self.w.keepFileNames.get()
        }
        setExtensionDefault(self.identifier, data)
        self.closeCallback(sender)

    def closeCallback(self, sender):
        if self.doneCallback is not None:
            self.doneCallback(self)
        self.w.close()

if __name__ == "__main__":
    class TestWindow(BaseWindowController):
        def __init__(self):
            # a test window to attach the settings sheet to
            self.instanceFolderName = "Aaaaa"
            self.w = Window((500, 500), "Test")
            self.w.open()
            Settings(self.w)
    w = TestWindow()