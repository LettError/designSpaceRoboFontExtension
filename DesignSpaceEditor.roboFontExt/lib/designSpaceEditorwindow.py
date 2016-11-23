# coding=utf-8
import os, time
import weakref
from AppKit import NSToolbarFlexibleSpaceItemIdentifier, NSURL, NSImageCell, NSImageAlignTop, NSScaleNone, NSImageFrameNone, NSImage, NSObject
import designSpaceDocument
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.extensions import getExtensionDefault, setExtensionDefault, ExtensionBundle
from defcon import Font
from defconAppKit.windows.progressWindow import ProgressWindow
from vanilla import *
from vanilla.dialogs import getFile, putFile, askYesNo
from mojo.UI import AccordionView
from mojo.roboFont import *

from vanilla import *
import designSpaceEditorSettings
reload(designSpaceEditorSettings)

checkSymbol = u"✓"
defaultSymbol = u"🔹"

# NSOBject Hack, please remove before release.
def ClassNameIncrementer(clsName, bases, dct):
   import objc
   orgName = clsName
   counter = 0
   while 1:
       try:
           objc.lookUpClass(clsName)
       except objc.nosuchclass_error:
           break
       counter += 1
       clsName = orgName + str(counter)
   return type(clsName, bases, dct)
# /NSOBject Hack, please remove before release.

class KeyedGlyphDescriptor(NSObject):
    #__metaclass__ = ClassNameIncrementer
    def __new__(cls):
        self = cls.alloc().init()
        self.glyphName = None
        self.patterns = {}
        return self
    
    def glyphNameKey(self):
        return self.glyphName
    
    def workingKey(self):
        return len(self.patterns)==1


def renameAxis(oldName, newName, location):
    # rename the axis name in a location
    # validate if the newName is not already in this location
    if newName in location:
        return location
    if not oldName in location:
        return location
    newLocation = {}
    for name, value in location.items():
        if name == oldName:
            newLocation[newName] = value
            continue
        newLocation[name] = value
    return newLocation

    
class KeyedSourceDescriptor(NSObject):
    #__metaclass__ = ClassNameIncrementer
    def __new__(cls):
        self = cls.alloc().init()
        self.dir = None
        self.path = None
        self.name = None
        self.location = None
        self.copyLib = False
        self.copyInfo = False
        self.copyGroups = False
        self.copyFeatures = False
        self.muteKerning = False
        self.muteInfo = False
        self.mutedGlyphNames = []
        self.familyName = None
        self.styleName = None
        self.axisOrder = []
        return self
    
    def renameAxis(self, oldName, newName):
        self.location = renameAxis(oldName, newName, self.location)
        
    def makeDefault(self, state):
        # make this master the default
        # set the flags
        if state:
            self.copyInfo = True
            self.copyGroups = True
            self.copyFeatures = True
            self.copyLib = True
        else:
            self.copyInfo = False
            self.copyGroups = False
            self.copyFeatures = False
            self.copyLib = False
            
    def setName(self):
        # make a name attribute based on the location
        # this will overwrite things that the source file might already contain.
        name = ['source', self.familyName, self.styleName]
        for k, v in self.location.items():
            name.append("%s_%3.3f"%(k, v))
        if None in name:
            return
        self.name = "_".join(name)
    
    def setAxisOrder(self, names):
        self.axisOrder = names
    
    def defaultMasterKey(self):
        # apparently this is uses to indicate that this master
        # might be intended to be the default font in this system.
        # we could consider making this a separate flag?
        if self.copyInfo:
            return defaultSymbol
        return ""
        
    def sourceUFONameKey(self):
        return os.path.basename(self.path)
        
    def sourceHasFileKey(self):
        if os.path.exists(self.path):
            return checkSymbol
        return ""
    
    def sourceFamilyNameKey(self):
        return self.familyName
    
    def sourceStyleNameKey(self):
        return self.styleName
        
    def getAxisValue(self, axisIndex):
        if 0 <= axisIndex < len(self.axisOrder):
            wantAxisName = self.axisOrder[axisIndex]
            if wantAxisName in self.location:
                v = self.location[wantAxisName]
                if type(v) == tuple:
                    return v[0]
                return v
        return ""

    def sourceAxis_1(self):
        return self.getAxisValue(0)
    def sourceAxis_2(self):
        return self.getAxisValue(1)
    def sourceAxis_3(self):
        return self.getAxisValue(2)
    def sourceAxis_4(self):
        return self.getAxisValue(3)
    def sourceAxis_5(self):
        return self.getAxisValue(4)

    def setValue_forUndefinedKey_(self, value=None, key=None):
        if key == "sourceFamilyNameKey":
            self.familyName = value
        elif key == "sourceStyleNameKey":
            self.stylename = value
        elif key == "sourceAxis_1":
            axisName = self.axisOrder[0]
            try:
                self.location[axisName] = float(value)
            except ValueError:
                NSBeep()
        elif key == "sourceAxis_2":
            axisName = self.axisOrder[1]
            try:
                self.location[axisName] = float(value)
            except ValueError:
                NSBeep()
        elif key == "sourceAxis_3":
            axisName = self.axisOrder[2]
            try:
                self.location[axisName] = float(value)
            except ValueError:
                NSBeep()
        elif key == "sourceAxis_4":
            axisName = self.axisOrder[3]
            try:
                self.location[axisName] = float(value)
            except ValueError:
                NSBeep()
        elif key == "sourceAxis_5":
            axisName = self.axisOrder[4]
            try:
                self.location[axisName] = float(value)
            except ValueError:
                NSBeep()
    
class KeyedInstanceDescriptor(NSObject):
    #__metaclass__ = ClassNameIncrementer
    def __new__(cls):
        self = cls.alloc().init()
        self.dir = None
        self.path = None
        self.name = None
        self.location = None
        self.familyName = None
        self.styleName = None
        self.postScriptFontName = None
        self.styleMapFamilyName = None
        self.styleMapStyleName = None
        self.glyphs = {}
        self.axisOrder = []
        self.kerning = True
        self.info = True
        return self

    def renameAxis(self, oldName, newName):
        self.location = renameAxis(oldName, newName, self.location)
        newAxisOrder = []
        for name in self.axisOrder:
            if name == oldName:
                newAxisOrder.append(newName)
            else:
                newAxisOrder.append(name)
        self.axisorder = newAxisOrder
    
    def copy(self):
        # construct and return a duplicate of this instance
        # umme, what to do with duplicate paths? these things could then overwrite!?
        copy = KeyedInstanceDescriptor()
        copy.familyName = self.familyName
        copy.styleName = self.styleName
        copy.postScriptFontName = self.postScriptFontName
        copy.styleMapFamilyName = self.styleMapFamilyName
        copy.glyphs.update(self.glyphs)
        copy.axisOrder = self.axisOrder
        copy.info = self.info
        copy.location = self.location
        copy.setName()
        copy.makeUFOPathFromNames()
        return copy
        
    def setName(self):
        # make a name attribute based on the location
        name = ['instance', self.familyName, self.styleName]
        for k, v in self.location.items():
            name.append("%s_%3.3f"%(k, v))
        self.name = "_".join(name)
        
    def setAxisOrder(self, names):
        self.axisOrder = names

    def instanceHasFileKey(self):
        if self.path is None:
            return ""
        if os.path.exists(self.path):
            return checkSymbol
        return u""
    
    def getAxisValue(self, axisIndex):
        if 0 <= axisIndex < len(self.axisOrder):
            wantAxisName = self.axisOrder[axisIndex]
            if wantAxisName in self.location:
                v = self.location[wantAxisName]
                if type(v) == tuple:
                    return v[0]
                return v
        return ""
        
    def instanceAxis_1(self):
        return self.getAxisValue(0)
    def instanceAxis_2(self):
        return self.getAxisValue(1)
    def instanceAxis_3(self):
        return self.getAxisValue(2)
    def instanceAxis_4(self):
        return self.getAxisValue(3)
    def instanceAxis_5(self):
        return self.getAxisValue(4)

    def instanceUFONameKey(self):
        if self.path is None:
            self.makeUFOPathFromNames()
        return os.path.basename(self.path)
    
    def setPathRelativeTo(self, docFolder, instancesFolderName):
        self.dir = os.path.join(docFolder, instancesFolderName)
        self.makeUFOPathFromNames()

    def makeUFOPathFromNames(self):
        if self.familyName is not None and self.styleName is not None:
            fileName = "%s-%s.ufo"%(self.familyName, self.styleName)
            self.postScriptFontName = "%s-%s"%(self.familyName, self.styleName)
        else:
            fileName = "NewFamily-NewStyle.ufo"
            self.postScriptFontName = "NewFamily-NewStyle"
        if self.dir is None:
            saveDir = ""
        else:
            saveDir = self.dir
        self.path = os.path.join(saveDir, fileName)

    def setValue_forUndefinedKey_(self, value=None, key=None):
        if key == "instanceFamilyNameKey":
            self.familyName = value
            self.makeUFOPathFromNames()
        elif key == "instanceStyleNameKey":
            self.styleName = value
            self.makeUFOPathFromNames()
        elif key == "instanceAxis_1":
            axisName = self.axisOrder[0]
            try:
                self.location[axisName] = float(value)
            except ValueError:
                NSBeep()
        elif key == "instanceAxis_2":
            axisName = self.axisOrder[1]
            try:
                self.location[axisName] = float(value)
            except ValueError:
                NSBeep()
        elif key == "instanceAxis_3":
            axisName = self.axisOrder[2]
            try:
                self.location[axisName] = float(value)
            except ValueError:
                NSBeep()
        elif key == "instanceAxis_4":
            axisName = self.axisOrder[3]
            try:
                self.location[axisName] = float(value)
            except ValueError:
                NSBeep()
        elif key == "instanceAxis_5":
            axisName = self.axisOrder[4]
            try:
                self.location[axisName] = float(value)
            except ValueError:
                NSBeep()
            
    def instanceFamilyNameKey(self):
        return self.familyName
    def instanceStyleNameKey(self):
        return self.styleName

def intOrFloat(num):
    if int(num) == num:
        return "%d" % num
    return "%f" % num
    
class KeyedAxisDescriptor(NSObject):
    #__metaclass__ = ClassNameIncrementer
    # https://www.microsoft.com/typography/otspec/fvar.htm
    registeredTags = [
        ("italic", "ital"),
        ("optical", "opsz"),
        ("slant", "slnt"),
        ("width", "wdth"),
        ("weight", "wght"),
        ]

    defaultLabelNameLanguageTag = "en"
    
    def __new__(cls):
        self = cls.alloc().init()
        self.tag = None     # opentype tag for this axis
        self.name = None    # name of the axis used in locations
        self.labelNames = {} # names for UI purposes, if this is not a standard axis,
        self.minimum = None
        self.maximum = None
        self.default = None
        self.map = []
        self.controller = None    # weakref to controller
        return self

    def renameAxis(self, oldName, newName):
        if self.name == oldName:
            self.name = newName
    
    def registeredTagKey(self):
        for name, tag in self.registeredTags:
            if name == self.name and tag == self.tag:
                return checkSymbol
        return ""
        
    def setValue_forUndefinedKey_(self, value=None, key=None):
        if key == "axisNameKey":
            self.controller().callbackRenameAxes(self.name, value)
        elif key == "axisTagKey":
            if len(value)!=4:
                return
            self.tag = value
        elif key == "axisMinimumKey":
            try:
                num = float(value)
                self.minimum = num
            except ValueError:
                NSBeep()
        elif key == "axisMaximumKey":
            try:
                num = float(value)
                self.maximum = num
            except ValueError:
                NSBeep()
        elif key == "axisDefaultKey":
            try:
                num = float(value)
                self.default = num
            except ValueError:
                NSBeep()
        elif key == "labelNameKey":
            if not self.registeredTagKey():
                self.labelNames[self.defaultLabelNameLanguageTag] = value
        elif key == "mapKey":
            # interpret the string of numbers as 
            # <input1>, <output1>, <input2>, <output2>,...
            # empty string, indicates a wish for an empty list
            if value is None or value == "-":
                self.map = []
                return
            try:
                newMapValues = []
                values = [float(p.strip()) for p in value.split(",")]
                if len(values)%2 != 0:
                    # needs to be paired values
                    return
                for i in range(0, len(values), 2):
                    inputValue = values[i]
                    outputValue = values[i+1]
                    newMapValues.append((inputValue, outputValue))
                self.map = newMapValues
            except:
                pass
    
    def labelNameKey(self):
        if self.registeredTagKey():
            return "-"
        return self.labelNames.get("en", "New Axis Label Name")
        
    def axisNameKey(self):
        return self.name
    def axisTagKey(self):
        return self.tag
    def axisMinimumKey(self):
        return self.minimum
    def axisDefaultKey(self):
        return self.default
    def axisMaximumKey(self):
        return self.maximum
    def mapKey(self):
        t = []
        if not self.map:
            return "-"
        for inputValue, outputValue in self.map:
            t.append(intOrFloat(inputValue))
            t.append(intOrFloat(outputValue))
        return ", ".join(t)


class KeyedDocReader(designSpaceDocument.BaseDocReader):
    axisDescriptorClass = KeyedAxisDescriptor
    sourceDescriptorClass = KeyedSourceDescriptor
    instanceDescriptorClass = KeyedInstanceDescriptor
    
class KeyedDocWriter(designSpaceDocument.BaseDocWriter):
    axisDescriptorClass = KeyedAxisDescriptor
    sourceDescriptorClass = KeyedSourceDescriptor
    instanceDescriptorClass = KeyedInstanceDescriptor

def newImageListCell():
    cell = NSImageCell.alloc().init()
    cell.setImageAlignment_(NSImageAlignTop)
    cell.setImageFrameStyle_(NSImageFrameNone)
    return cell


class DesignSpaceEditor(BaseWindowController):
    preferredAxes = [
        ("weight", "wght", 0, 1000, 0),
        ("width", "wdth", 0, 1000, 0),
        ("optical", "opsz", 3, 1000, 16),
        ]

    def __init__(self, designSpacePath=None):

        self.settingsIdentifier = "%s.%s" % (settings.settingsIdentifier, "general")
        self.updateFromSettings()
        #extensionSettings = getExtensionDefault(self.settingsIdentifier, dict())
        #self.instanceFolderName = extensionSettings.get('instanceFolderName', "instances")
        
        self.designSpacePath = designSpacePath
        self.doc = None
        self._newInstanceCounter = 1
        if self.designSpacePath is None:
            fileNameTitle = "Untitled.designspace"
        else:
            fileNameTitle = os.path.basename(self.designSpacePath)
        self.w = Window((940, 700), fileNameTitle, minSize=(200,400))
        self._updatingTheAxesNames = False
        toolbarItems = [
            {
                'itemIdentifier': "toolbarSave",
                'label': 'Save',
                'callback': self.save,
                'imageNamed': "toolbarScriptOpen",
            },
            {
                'itemIdentifier': "addOpenFonts",
                'label': 'Add Open Fonts',
                'callback': self.callbackAddOpenFonts,
                'imageNamed': "toolbarScriptOpen",
            },
            {
                'itemIdentifier': "generate",
                'label': 'Generate',
                'callback': self.callbackGenerate,
                'imageNamed': "prefToolbarMisc",
            },
            {
                'itemIdentifier': NSToolbarFlexibleSpaceItemIdentifier,
            },
            {
                'itemIdentifier': "settings",
                'label': 'Settings',
                'callback': self.toolbarSettings,
                'imageNamed': "prefToolbarMisc",
            },
        ]
        self.w.addToolbar("DesignSpaceToolbar", toolbarItems)
        
        fileIconWidth = 20
        ufoNameWidth = 220
        axisValueWidth = 80
        familyNameWidth = 130
        masterColDescriptions = [
                {   'title': '',
                    'key':'sourceHasFileKey',
                    'width':fileIconWidth,
                    'editable':False,
                },
                {   'title': '',
                    'key':'defaultMasterKey',
                    'width':fileIconWidth,
                    'editable':False,
                },
                {   'title': 'UFO',
                    'key':'sourceUFONameKey',
                    'width':ufoNameWidth,
                    'editable':False,
                },
                {   'title': 'Family Name',
                    'key': 'sourceFamilyNameKey',
                    'width':familyNameWidth,
                    'editable':True,
                },
                {   'title': 'Style Name',
                    'key':'sourceStyleNameKey',
                    'width':familyNameWidth,
                    'editable':True,
                },
                {   'title': 'Axis 1',
                    'key':'sourceAxis_1',
                    'width':axisValueWidth,
                    'editable':True,
                },
                {   'title': 'Axis 2',
                    'key':'sourceAxis_2',
                    'width':axisValueWidth,
                    'editable':True,
                },
                {   'title': 'Axis 3',
                    'key':'sourceAxis_3',
                    'width':axisValueWidth,
                    'editable':True,
                },
                {   'title': 'Axis 4',
                    'key':'sourceAxis_4',
                    'width':axisValueWidth,
                    'editable':True,
                },
                {   'title': 'Axis 5',
                    'key':'sourceAxis_5',
                    'width':axisValueWidth,
                    'editable':True,
                },
        ]
        instanceColDescriptions = [
                {   'title': '',
                    'key':'instanceHasFileKey',
                    'width':2*fileIconWidth,
                    'editable':False,
                },
                {   'title': 'UFO',
                    'key': 'instanceUFONameKey',
                    'width':ufoNameWidth,
                    'editable':False,
                },
                {   'title': 'Family Name',
                    'key': 'instanceFamilyNameKey',
                    'width':familyNameWidth,
                    'editable':True,
                },
                {   'title': 'Style Name',
                    'key':'instanceStyleNameKey',
                    'width':familyNameWidth,
                    'editable':True,
                },

                {   'title': 'Axis 1',
                    'key':'instanceAxis_1',
                    'width':axisValueWidth,
                    'editable':True,
                },
                {   'title': 'Axis 2',
                    'key':'instanceAxis_2',
                    'width':axisValueWidth,
                    'editable':True,
                },
                {   'title': 'Axis 3',
                    'key':'instanceAxis_3',
                    'width':axisValueWidth,
                    'editable':True,
                },
                {   'title': 'Axis 4',
                    'key':'instanceAxis_4',
                    'width':axisValueWidth,
                    'editable':True,
                },
                {   'title': 'Axis 5',
                    'key':'instanceAxis_5',
                    'width':axisValueWidth,
                    'editable':True,
                },
            ]
        axisColDescriptions = [
                {   'title': u"®",
                    'key':'registeredTagKey',
                    'width':2*fileIconWidth,
                    'editable':False,
                },
                {   'title': 'Name',
                    'key':'axisNameKey',
                    'width':100,
                    'editable':True,
                },
                {   'title': 'Tag',
                    'key':'axisTagKey',
                    'width':100,
                    'editable':True,
                },
                {   'title': 'Minimum',
                    'key':'axisMinimumKey',
                    'width':100,
                    'editable':True,
                },
                {   'title': 'Default',
                    'key':'axisDefaultKey',
                    'width':100,
                    'editable':True,
                },
                {   'title': 'Maximum',
                    'key':'axisMaximumKey',
                    'width':100,
                    'editable':True,
                },
                {   'title': 'Labelname',
                    'key':'labelNameKey',
                    'width':150,
                    'editable':True,
                },
                {   'title': 'Map',
                    'key':'mapKey',
                    'width':250,
                    'editable':True,
                },
            ]
        glyphsColDescriptions = [
                {   'title': '',
                    'key':'workingKey',
                    'width':40,
                    'editable':False,
                },
                {   'title': 'Glyphname',
                    'key':'glyphNameKey',
                    'width':40,
                    'editable':False,
                },
        ]
        toolbarHeight = 24
        self.axesGroup = Group((0,0,0,0))
        self.axesItem = List((0, toolbarHeight, -0, -0), [], columnDescriptions=axisColDescriptions, editCallback=self.callbackAxesListEdit)
        self.axesGroup.l = self.axesItem
        buttonMargin = 2
        buttonHeight = 20
        firstButtonSize = (48,buttonMargin+1,50,buttonHeight)
        secondButtonSize = (100,buttonMargin+1,100,buttonHeight)
        thirdButtonSize = (202,buttonMargin+1,100,buttonHeight)
        statusTextSize = (165, buttonMargin+4,-10,buttonHeight)
        addButtonSize = (102,buttonMargin+1,50,buttonHeight)
        axisToolDescriptions = [
            {'title': "+", 'width': 20,},
            {'title': "-", 'width': 20}
            ]
        self.axesGroup.tools = SegmentedButton(
            (buttonMargin,buttonMargin,100,buttonHeight),
            segmentDescriptions=axisToolDescriptions,
            selectionStyle="momentary",
            callback=self.callbackAxisTools)
        
        self.mastersGroup = Group((0,0,0,0))
        masterToolDescriptions = [
            {'title': "+", 'width': 20,},
            {'title': "-", 'width': 20},
            ]
        self.mastersItem = List((0, toolbarHeight, -0, -0), [],
            columnDescriptions=masterColDescriptions,
            #doubleClickCallback=self.callbackMastersDblClick
            selectionCallback=self.callbackMasterSelection
            )
        self.mastersGroup.l = self.mastersItem
        self.mastersGroup.tools = SegmentedButton(
            (buttonMargin, buttonMargin,100,buttonHeight),
            segmentDescriptions=masterToolDescriptions,
            selectionStyle="momentary",
            callback=self.callbackMasterTools)
        self.mastersGroup.openButton = Button(
            firstButtonSize, "Open",
            callback=self.callbackOpenMaster,
            sizeStyle="small")
        self.mastersGroup.openButton.enable(False)
        self.mastersGroup.makeDefaultButton = Button(
            secondButtonSize, "Make Default",
            callback=self.callbackMakeDefaultMaster,
            sizeStyle="small")
        self.mastersGroup.makeDefaultButton.enable(False)
        self.mastersGroup.loadNamesFromSourceButton = Button(
            thirdButtonSize, "Load Names",
            callback=self.callbackGetNamesFromSources,
            sizeStyle="small")
        self.mastersGroup.loadNamesFromSourceButton.enable(False)
        
        
        self.instancesGroup = Group((0,0,0,0))
        self.instancesItem = List((0, toolbarHeight, -0, -0), [],
            columnDescriptions=instanceColDescriptions,
            selectionCallback=self.callbackInstanceSelection,
        )
        self.instancesGroup.duplicateButton = Button(
            secondButtonSize, "Duplicate",
            callback=self.callbackDuplicateInstance,
            sizeStyle="small")
        self.instancesGroup.duplicateButton.enable(False)

        instancesToolDescriptions = [
            {'title': "+", 'width': 20,},
            {'title': "-", 'width': 20},
            ]

        self.instancesGroup.tools = SegmentedButton(
            (buttonMargin, buttonMargin,100,buttonHeight),
            segmentDescriptions=instancesToolDescriptions,
            selectionStyle="momentary",
            callback=self.callbackInstanceTools)
        self.instancesGroup.l = self.instancesItem
        self.instancesGroup.openButton = Button(
            firstButtonSize, "Open",
            callback=self.callbackOpenInstance,
            sizeStyle="small")
        self.instancesGroup.openButton.enable(False)
        
        self.glyphsGroup = Group((0,0,0,0))
        self.glyphsItem = List((0, toolbarHeight, -0, -0), [],
            #columnDescriptions=glyphsColDescriptions,
            #selectionCallback=self.callbackInstanceSelection,
        )
        self.glyphsGroup.l = self.glyphsItem
    
        self.reportGroup = Group((0,0,0,0))
        self.reportGroup.text = EditText((0,toolbarHeight,-0,-0), 'hehe')
        
        descriptions = [
           dict(label="Axes", view=self.axesGroup, size=138, collapsed=False, canResize=False),
           dict(label="Masters", view=self.mastersGroup, size=135, collapsed=False, canResize=True),
           dict(label="Instances", view=self.instancesGroup, size=135, collapsed=False, canResize=True),
           dict(label="Report", view=self.reportGroup, size=170, collapsed=False, canResize=True),
           # this panel will show glyphs and compatibiility.
           #dict(label="Glyphs", view=self.glyphsGroup, size=250, collapsed=False, canResize=True),
        ]

        self.read(self.designSpacePath)
        self.w.accordionView = AccordionView((0, 0, -0, -0), descriptions)
        self.updateAxesColumns()
        self.enableInstanceList()
        self.w.open()
        if self.designSpacePath is not None:
            self.w.getNSWindow().setRepresentedURL_(NSURL.fileURLWithPath_(self.designSpacePath))

        self.w.bind("became main", self.callbackBecameMain)
        self.w.bind("close", self.callbackCleanup)
        
        self.w.vanillaWrapper = weakref.ref(self)

        self.setUpBaseWindowBehavior()
            
    def callbackCleanup(self, sender=None):
        self.w.document = None
    
    def callbackRenameAxes(self, oldName, newName):
        # validate the new name, make sure we don't duplicate an existing name
        for axis in self.doc.axes:
            if newName == axis.name:
                return
        for source in self.doc.sources:
            source.renameAxis(oldName, newName)
        for instance in self.doc.instances:
            instance.renameAxis(oldName, newName)
        for axis in self.doc.axes:
            axis.renameAxis(oldName, newName)
        self.updateInstanceNames()
        self.validate()
        
    def _getDefaultValue(self, identifier, key):
        data = getExtensionDefault(identifier, dict())
        return data.get(key, defaultOptions[key])

    def getInstancesFolder(self):
        return self._getDefaultValue("%s.general" % settingsIdentifier, "instanceFolderName")
    
    def validate(self):
        # validate all data and write a report here.
        report = []
        
        # document and path
        if self.designSpacePath is None:
            #report.append("This document has not been saved yet.")
            if len(self.doc.sources)>0:
                masterFolder = self.getSaveDirFromMasters()
                report.append("Make sure to save this document in %s."%masterFolder)
        else:
            report.append("Document source folder:")
            report.append("\t%s"%os.path.dirname(self.designSpacePath))

        # axes
        if len(self.doc.axes)==0:
            report.append("Define one or more axes")
        else:
            report.append("Axes:")
            for axis in self.doc.axes:
                if axis.registeredTagKey():
                    report.append("\t\"%s\" registered OpenType axis name."%axis.name)
                else:
                    report.append("\t\"%s\" is a non-standard axis name."%axis.name)
                    for k, v in axis.labelNames.items():
                        report.append("\t\tlabel name %s: \"%s\""%(k,v))

                
        # masters
        if len(self.doc.sources)==0:
            report.append("Add two or more UFOs.")
        else:
            report.append("Masters:")
            for master in self.doc.sources:
                report.append("\t%s"%master.path)
                if self.designSpacePath is not None:
                    if os.path.dirname(master.path)!=os.path.dirname(self.designSpacePath):
                        report.append("\tPlease move to the same folder as this document.")
                if master.defaultMasterKey():
                    report.append("\t\tThis master is the default.")
        
        # instances
        if self.instanceFolderName is None:
            report.append("No instance folder name set.")
        else:
            if self.designSpacePath is None:
                path = "<document folder>"
            else:
                path = os.path.dirname(self.designSpacePath)
            report.append("Instance folder:\n\t%s/%s"%(path, self.instanceFolderName))
            
        if len(self.doc.instances)==0:
            report.append("Define an instance.")
        else:
            report.append("Instances:")
            for instance in self.doc.instances:
                report.append("\t%s"%instance.path)
        
        self.reportGroup.text.set("\n".join(report))
    
    def updateFromSettings(self):
        extensionSettings = getExtensionDefault(self.settingsIdentifier, dict())
        self.instanceFolderName = extensionSettings.get('instanceFolderName', "instances")

    def applySettingsCallback(self, sender):
        # callback for the settings window
        self.updateFromSettings()
        self.updateInstanceNames()
        self.validate()
        
    def toolbarSettings(self, sender):
        settings.Settings(self.w, self.applySettingsCallback)
            
    def openSelectedItem(self, sender):
        selection = sender.getSelection()
        if selection:
            progress = ProgressWindow("Opening UFO...", len(selection), parentWindow=self.w)
            for i in sender.getSelection():
                key = sender[i]
                if key.path is None:
                    continue
                path = key.path
                try:
                    alreadyOpen = False
                    for f in AllFonts():
                        if f.path == path:
                            thisWindow = f.document().getMainWindow()
                            thisWindow.show()
                            alreadyOpen = True
                            break
                    if not alreadyOpen:
                        font = RFont(path, showUI=False)
                        font.showUI()
                except:
                    print "Bad UFO:", path
                    pass
                progress.update()
            progress.close()            
    
    def callbackGenerate(self, sender):
        from mutatorMath.ufo import build
        if self.designSpacePath is None:
            return
        progress = ProgressWindow(u"Generating instance UFO’s…", 10, parentWindow=self.w)
        try:
            build(self.designSpacePath)
        except:
            import traceback
            traceback.print_exc()
        finally:
            progress.close()            
        
    def callbackBecameMain(self, sender):
        self.validate()
                    
    def setInstanceFolderName(self, value):
        self.instanceFolderName = value
        self.validate()
                
    def updateAxesColumns(self):
        # present the axis names above all the columns.
        names = []
        for axis in self.doc.axes:
            names.append(axis.name)
        for descriptor in self.doc.instances:
            descriptor.setAxisOrder(names)
        for descriptor in self.doc.sources:
            descriptor.setAxisOrder(names)
        # clear the old names
        columns = self.mastersItem.getNSTableView().tableColumns()
        sourceColumnTitleOffset = 5
        for col in range(sourceColumnTitleOffset, len(columns)):
            column = columns[col]
            try:
                newTitle = names[col-sourceColumnTitleOffset]
            except IndexError:
                newTitle = u""
            column.setTitle_(newTitle)
        self.mastersItem.getNSTableView().reloadData()

        columns = self.instancesItem.getNSTableView().tableColumns()
        instancesColumnTitleOffset = 4
        for col in range(instancesColumnTitleOffset, len(columns)):
            column = columns[col]
            try:
                newTitle = names[col-instancesColumnTitleOffset]
            except IndexError:
                newTitle = u""
            column.setTitle_(newTitle)
        self.instancesItem.getNSTableView().reloadData()
        
    def read(self, designSpacePath):
        self.doc = designSpaceDocument.DesignSpaceDocument(KeyedDocReader, KeyedDocWriter)
        if designSpacePath is not None:
            self.doc.read(designSpacePath)
        for item in self.doc.axes:
            item.controller = weakref.ref(self)
        self.axesItem.set(self.doc.axes)
        self.mastersItem.set(self.doc.sources)
        self.instancesItem.set(self.doc.instances)
        self.validate()

    def getSaveDirFromMasters(self):
        options = {}
        for master in self.mastersItem:
            if master.path is not None:
                thisFileDir = os.path.dirname(master.path)
                options[thisFileDir] = True
        if len(options)==1:
            # neat and tidy, all masters in a folder
            return options.keys()[0]
        if options:
            paths = options.keys()
            paths.sort()
            return paths[0]
        return None
            
    def save(self, sender):
        if self.designSpacePath is None:
            # get a filepath first
            saveToDir = self.getSaveDirFromMasters()    # near the masters
            putFile(messageText="Save designspace:",
                directory=saveToDir,
                canCreateDirectories=True,
                fileTypes=['designspace'],
                parentWindow=self.w,
                resultCallback=self.finalizeSave)
        else:
            self.finalizeSave(self.designSpacePath)
    
    def updateInstanceNames(self):
        # so we have the path for this document
        # we need to make sure the instances are all in the right place
        if self.designSpacePath is None:
            return
        docFolder = os.path.dirname(self.designSpacePath)
        for item in self.instancesItem:
            item.setPathRelativeTo(docFolder, self.instanceFolderName)
            item.setName()

    def finalizeSave(self, path=None):
        self.designSpacePath = path
        # so we have the path for this document
        # we need to make sure the instances are all in the right place
        self.updateInstanceNames()
        for item in self.mastersItem:
            item.setName()
        self.doc.write(self.designSpacePath)
        self.w.getNSWindow().setRepresentedURL_(NSURL.fileURLWithPath_(self.designSpacePath))
        self.w.setTitle(os.path.basename(self.designSpacePath))
        self.instancesItem.set(self.doc.instances)
        self.validate()
    
    def updateLocations(self):
        # update all the displayed locations, we might have more or fewer axes
        defaults = {}
        # find the defined names
        for axisDescriptor in self.doc.axes:
            defaults[axisDescriptor.name] = axisDescriptor.default
        for instanceDescriptor in self.doc.instances:
            self._updateLocation(instanceDescriptor, defaults)
        for sourceDescriptor in self.doc.sources:
            self._updateLocation(sourceDescriptor, defaults)
            
    def _updateLocation(self, descriptor, defaults):
        remove = []
        for axisName in descriptor.location.keys():
            if axisName not in defaults:
                remove.append(axisName)
        for name in remove:
            del descriptor.location[name]
        for axisName, defaultValue in defaults.items():
            if axisName not in descriptor.location:
                descriptor.location[axisName] = defaultValue
    
    def callbackAxesListEdit(self, sender):
        if self._updatingTheAxesNames == False:
            if sender.getSelection():
                self._updatingTheAxesNames = True        # preventing recursion? XXX
                self.updateAxesColumns()
                self.updateLocations()
                self.axesItem.set(self.doc.axes)
                self._updatingTheAxesNames = False
                self.validate()

    def callbackAxisTools(self, sender):
        if sender.get() == 0:
            # add axis button
            if len(self.doc.axes)<5:
                axisDescriptor = KeyedAxisDescriptor()
                axisDescriptor.controller = weakref.ref(self)
                axisDescriptor.name = "newAxis%d"%len(self.doc.axes)
                axisDescriptor.tag = "nwx%d"%len(self.doc.axes)
                axisDescriptor.minimum = 0
                axisDescriptor.maximum = 1000
                axisDescriptor.default = 0
                self.doc.axes.append(axisDescriptor)
                self.updateAxesColumns()
                self.updateLocations()
                self.axesItem.set(self.doc.axes)
        elif sender.get() == 1:
            axisCount = len(self.axesItem.getSelection())
            if axisCount == 0:
                return
            elif axisCount == 1:
                text = "Do you want to delete this axis?"
            else:
                text = "Do you want to delete %d axes?"%axisCount
            result = askYesNo(messageText=text, informativeText="It will disappear from all masters and instances. There is no undo.", parentWindow=self.w, resultCallback=self.finallyDeleteAxis)
        self.validate()

    def finallyDeleteAxis(self, result):
        if result != 1:
            return
        removeThese = []
        # remove axis button
        for index in self.axesItem.getSelection():
            removeThese.append(id(self.axesItem[index]))
        keepThese = []
        for item in self.doc.axes:
            if id(item) not in removeThese:
                keepThese.append(item)
        self.doc.axes = keepThese
        self.updateAxesColumns()
        self.updateLocations()
        self.axesItem.set(self.doc.axes)
        self.validate()
    
    def callbackInstanceTools(self, sender):
        if sender.get() == 0:
            # add instance button
            newInstanceDescriptor = KeyedInstanceDescriptor()
            if self.doc.instances:
                newInstanceDescriptor.familyName = self.doc.instances[0].familyName
            elif self.doc.sources:
                newInstanceDescriptor.familyName = self.doc.sources[0].familyName
            else:
                newInstanceDescriptor.familyName = "NewFamily"
            newInstanceDescriptor.location = self.doc.newDefaultLocation()
            newInstanceDescriptor.styleName = "NewInstance_%d"%self._newInstanceCounter
            self._newInstanceCounter += 1
            newInstanceDescriptor.path = "[pending save]"
            self.doc.addInstance(newInstanceDescriptor)
            self.updateAxesColumns()
            self.instancesItem.set(self.doc.instances)
        elif sender.get() == 1:
            # remove instance button.
            instanceCount = len(self.instancesItem.getSelection())
            if instanceCount == 0:
                return
            elif instanceCount == 1:
                text = "Do you want to delete this instance?"
            else:
                text = "Do you want to delete %d instances?"%instanceCount
            result = askYesNo(messageText=text, informativeText="There is no undo.", parentWindow=self.w, resultCallback=self.finallyDeleteInstance)
        self.validate()

    def finallyDeleteInstance(self, result):
        if result != 1:
            return
        removeThese = []
        for index in self.instancesItem.getSelection():
            removeThese.append(id(self.instancesItem[index]))
        keepThese = []
        for item in self.doc.instances:
            if id(item) not in removeThese:
                keepThese.append(item)
        self.doc.instances = keepThese
        self.instancesItem.set(self.doc.instances)
        self.validate()

    def callbackOpenInstance(self, sender):
        self.openSelectedItem(self.instancesItem)
        
    def callbackMasterTools(self, sender):
        if sender.get() == 0:
            # add a master
            getFile(messageText=u"Add new UFO",
                allowsMultipleSelection=True,
                fileTypes=["ufo"],
                parentWindow=self.w,
                resultCallback=self.finalizeAddMaster)
        elif sender.get() == 1:
            # remove a master
            masterCount = len(self.mastersItem.getSelection())
            if masterCount == 0:
                return
            if masterCount == 1:
                text = "Do you want to remove this master?"
            else:
                text = "Do you want to remove %d masters?"%masterCount
            result = askYesNo(messageText=text,
                informativeText="There is no undo.",
                parentWindow=self.w,
                resultCallback=self.finalizeDeleteMaster)

    def callbackOpenMaster(self, sender):
        self.openSelectedItem(self.mastersItem)
        self.updateAxesColumns()
        self.enableInstanceList()
        self.validate()
    
    def callbackMakeDefaultMaster(self, sender):
        selectedMaster = self.mastersItem[self.mastersItem.getSelection()[0]]
        for master in self.mastersItem:
            master.makeDefault(False)
        selectedMaster.makeDefault(True)
        self.mastersItem.set(self.doc.sources)
        self.validate()
    
    def callbackGetNamesFromSources(self, sender):
        # open the source fonts and load the family and stylenames
        for i in self.mastersItem.getSelection():
            selectedItem = self.doc.sources[i]
            if selectedItem.sourceHasFileKey():
                f = OpenFont(selectedItem.path, showUI=False)
                selectedItem.familyName = f.info.familyName
                selectedItem.styleName = f.info.styleName
                f.close()
        self.mastersItem.set(self.doc.sources)
        self.validate()
        
    def callbackAddOpenFonts(self, sender):
        # add the open fonts
        weHave = [s.path for s in self.doc.sources]
        for f in AllFonts():
            if f.path not in weHave:
                self.addSourceFromFont(f)
        self.enableInstanceList()
        self.validate()

    def enableInstanceList(self):
        # we have open masters:
        if len(self.mastersItem)>1:
            self.instancesItem.enable(True)
            self.instancesGroup.tools.enable(True)
        else:
            self.instancesItem.enable(False)
            self.instancesGroup.tools.enable(False)
            
    def finalizeDeleteMaster(self, result):
        if result != 1:
            return
        removeThese = []
        for index in self.mastersItem.getSelection():
            removeThese.append(id(self.mastersItem[index]))
        keepThese = []
        for item in self.doc.sources:
            if id(item) not in removeThese:
                keepThese.append(item)
        self.doc.sources = keepThese
        self.mastersItem.set(self.doc.sources)
        self.enableInstanceList()
        self.validate()
    
    def addSourceFromFont(self, font):
        defaults = {}
        for axisDescriptor in self.doc.axes:
            defaults[axisDescriptor.name] = axisDescriptor.default
        sourceDescriptor = KeyedSourceDescriptor()
        sourceDescriptor.path = font.path
        sourceDescriptor.familyName = font.info.familyName
        sourceDescriptor.styleName = font.info.styleName
        sourceDescriptor.location = {}
        sourceDescriptor.location.update(defaults)
        if len(self.mastersItem)==0:
            # this is the first master we're adding
            # make this the default so we have one.
            sourceDescriptor.makeDefault(True)
        self.doc.addSource(sourceDescriptor)
        self.mastersItem.set(self.doc.sources)
        sourceDescriptor.setName()

    def finalizeAddMaster(self, paths):
        for path in paths:
            font = OpenFont(path, showUI=False)
            self.addSourceFromFont(font)
        self.updateAxesColumns()
        self.enableInstanceList()
        self.validate()

    def callbackMasterSelection(self, sender):
        if len(sender.getSelection()) == 1:
            self.mastersGroup.makeDefaultButton.enable(True)
        else:
            self.mastersGroup.makeDefaultButton.enable(False)
        for i in sender.getSelection():
            selectedItem = self.doc.sources[i]
            if selectedItem.sourceHasFileKey():
                self.mastersGroup.openButton.enable(True)
                self.mastersGroup.loadNamesFromSourceButton.enable(True)
                return
        self.mastersGroup.openButton.enable(False)
        self.mastersGroup.loadNamesFromSourceButton.enable(False)
                
    def callbackDuplicateInstance(self, sender):
        # duplicate the selected instance
        copies = []
        for i in self.instancesItem.getSelection():
            copies.append(self.instancesItem[i].copy())
        for item in copies:
            self.doc.instances.append(item)
        self.instancesItem.set(self.doc.instances)
        
    def callbackInstanceSelection(self, sender):
        if len(sender.getSelection())>0:
            self.instancesGroup.duplicateButton.enable(True)
        else:
            self.instancesGroup.duplicateButton.enable(False)
        for i in sender.getSelection():
            selectedItem = self.doc.instances[i]
            if selectedItem.instanceHasFileKey():
                self.instancesGroup.openButton.enable(True)
                return
        self.instancesGroup.openButton.enable(False)
                
if __name__ == "__main__":
    # tests
    assert renameAxis("aaa", "bbb", dict(aaa=1)) == dict(bbb=1)
    assert renameAxis("ccc", "bbb", dict(aaa=1)) == dict(aaa=1)

    sD = KeyedSourceDescriptor()
    sD.location = dict(aaa=1, bbb=2)
    sD.renameAxis("aaa", "ddd")
    assert sD.location == dict(ddd=1, bbb=2)

    kI = KeyedInstanceDescriptor()
    kI.location = dict(aaa=1, bbb=2)
    kI.renameAxis("aaa", "ddd")
    assert kI.location == dict(ddd=1, bbb=2)
    kI.renameAxis("ddd", "bbb")
    assert kI.location == dict(ddd=1, bbb=2)

    aD = KeyedAxisDescriptor()
    aD.name = "aaa"
    aD.renameAxis("aaa", "bbb")
    assert aD.name == "bbb"
    
    results = getFile(messageText=u"Select a DesignSpace file:", allowsMultipleSelection=True, fileTypes=["designspace"])
    if results is not None:
       for path in results:
           DesignSpaceEditor(path)
