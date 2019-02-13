# coding = utf-8
import os, time, sys
import weakref, importlib
import AppKit
from objc import python_method
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.extensions import getExtensionDefault, setExtensionDefault, ExtensionBundle
from mojo.events import publishEvent
from defconAppKit.windows.progressWindow import ProgressWindow
import vanilla
from vanilla.dialogs import getFile, putFile, askYesNo
from mojo.UI import AccordionView
from mojo.roboFont import *
import mojo.extensions
import ufoLib
import designspaceProblems
print(designspaceProblems.__file__)
#from importlib import reload
#reload(designspaceProblems)
from designspaceProblems import DesignSpaceChecker

if version[0] == '2':
    import fontParts.nonelab.font

import logging

import ufoProcessor
import fontTools.designspaceLib as dsd

import designSpaceEditorSettings
import ufoLib

checkSymbol = chr(10003)
defaultSymbol = chr(128313)

try:
    from variableFontGenerator import BatchDesignSpaceProcessor
    hasVariableFontGenerator = True
except ImportError:
    hasVariableFontGenerator = False

"""



    Paths
    the document reader and writer need an absolute path
    when a source is added, this is an absolute path, why?
    
    write to document: ufo paths are written relative to the document path
    
    assumption: .designspace document is always at the same or a higher level than the ufos.
    adobe: .designspace document can be higher up.
    
    what to do?
    step 1: keep the string of the filename attribute so that if there are no changes to the
    ufo, we can write the document identical to how it was read.
    step 2: on reading, calculate the absolute paths for the sources and instances

"""
DEVELOP = False

if DEVELOP:
    pathForBundle = os.path.dirname(__file__)
    resourcePathForBundle = os.path.join(os.path.dirname(pathForBundle), "resources")
    designspaceBundle = mojo.extensions.ExtensionBundle(path=pathForBundle, resourcesName=resourcePathForBundle)
else:
    designspaceBundle = mojo.extensions.ExtensionBundle("DesignspaceEditor")


#NSOBject Hack, please remove before release.
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

class KeyedGlyphDescriptor(AppKit.NSObject,
        metaclass=ClassNameIncrementer
        ):
    def __new__(cls):
        self = cls.alloc().init()
        self.glyphName = None
        self.patterns = {}
        return self
    
    def glyphNameKey(self):
        return self.glyphName
    
    def workingKey(self):
        return len(self.patterns)==1


class LiveDesignSpaceProcessor(ufoProcessor.DesignSpaceProcessor):

    def loadFonts(self, reload=False):
        # Load the fonts and find the default candidate based on the info flag
        if self._fontsLoaded and not reload:
            return
        names = set()
        for sourceDescriptor in self.sources:
            if not sourceDescriptor.name in self.fonts:
                if os.path.exists(sourceDescriptor.path):
                    self.fonts[sourceDescriptor.name] = self._instantiateFont(sourceDescriptor.path)
                    # this is not a problem, why report it as one?
                    self.problems.append("loaded master from %s, format %d"%(sourceDescriptor.path, ufoProcessor.getUFOVersion(sourceDescriptor.path)))
                    names = names | set(self.fonts[sourceDescriptor.name].keys())
                else:
                    self.fonts[sourceDescriptor.name] = None
                    self.problems.append("can't load master from %s"%(sourceDescriptor.path))
        self.glyphNames = list(names)
        self._fontsLoaded = True



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

class KeyedRuleDescriptor(AppKit.NSObject,
        metaclass=ClassNameIncrementer
        ):
    def __new__(cls):
        self = cls.alloc().init()
        self.name = None
        self.conditionSets = []
        self.conditions = []
        self.subs = []
        return self

    @python_method
    def renameAxis(self, oldName, newName=None):
        renamedConditions = []
        for conditionSet in self.conditionSets:
            for cd in conditionSet:
                if cd['name'] == oldName:
                    renamedConditions.append(dict(name=newName, minimum=cd['minimum'], maximum=cd['maximum']))
                else:
                    if newName is not None:
                        renamedConditions.append(cd)
        self.conditions = renamedConditions
    
    def nameKey(self):
        return self.name

    def setValue_forUndefinedKey_(self, value=None, key=None):
        if key == "nameKey":
            # rename this axis
            if len(value)>0:
                self.name = value
    
    @python_method
    def __repr__(self):
        return "rule: %s with %d conditionsets" % (self.name, len(self.conditionSets))


class KeyedSourceDescriptor(AppKit.NSObject,
        metaclass=ClassNameIncrementer
        ):
    def __new__(cls):
        self = cls.alloc().init()
        self.dir = None
        self.filename = None    # the filename as it appears in the document
        self.path = None
        self.layerName = None
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
        self.lib = {}
        self.isDefault = False
        self.wasEditedCallback = None
        return self
    
    @python_method
    def callbackCleanup(self):
        self.wasEditedCallback = None
        
    @python_method
    def getLayerNames(self):
        # see if we can get the layernames
        if self.path is not None:
            reader = ufoLib.UFOReader(self.path)
            return reader.getLayerNames()
        return []

    @python_method
    def renameAxis(self, oldName, newName):
        self.location = renameAxis(oldName, newName, self.location)
        
    @python_method
    def makeDefault(self, state):
        # make this master the default
        # set the flags
        if state:
            self.copyInfo = True
            self.copyGroups = True
            self.copyFeatures = True
            self.copyLib = True
            self.isDefault = True
        else:
            self.copyInfo = False
            self.copyGroups = False
            self.copyFeatures = False
            self.copyLib = False
            self.isDefault = False
            
    def setName(self):
        # make a name attribute based on the location
        # this will overwrite things that the source file might already contain.
        name = ['source', self.familyName, self.styleName]
        for k, v in self.location.items():
            name.append("%s_%3.3f"%(k, v))
        if None in name:
            return
        self.name = "_".join(name)
    
    @python_method
    def setAxisOrder(self, names):
        self.axisOrder = names
    
    def defaultMasterKey(self):
        # apparently this is uses to indicate that this master
        # might be intended to be the default font in this system.
        # we could consider making this a separate flag?
        if self.isDefault:
            return defaultSymbol
        #if self.copyInfo:
        #    return defaultSymbol
        return ""

    @python_method
    def setDocumentFolder(self, docFolder):
        # let the descriptor know what the document folder is
        # so that the descriptor can do some validation if the paths
        self.dir = docFolder
    
    def makePath(self):
        # using the document folder and the file name
        # we should be able to make an absolute path
        if self.filename is not None and self.dir is not None:
            self.path = os.path.abspath(os.path.join(self.dir, self.filename))
        
    def sourceUFONameKey(self):
        if self.filename is not None:
            if self.dir is not None:
                return self.filename
        return "[pending save]"

    def sourceLayerNameKey(self):
        return self.layerName
        
    def sourceHasFileKey(self):
        if os.path.exists(self.path):
            return checkSymbol
        return ""
    
    def sourceFamilyNameKey(self):
        return self.familyName
    
    def sourceStyleNameKey(self):
        return self.styleName
        
    @python_method
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
        elif key == "sourceUFONameKey":
            self.filename = value
            self.makePath()
        elif key == "sourceStyleNameKey":
            self.styleName = value
        elif key == "sourceAxis_1":
            axisName = self.axisOrder[0]
            try:
                self.location[axisName] = float(value)
            except (TypeError, ValueError):
                AppKit.NSBeep()
        elif key == "sourceAxis_2":
            axisName = self.axisOrder[1]
            try:
                self.location[axisName] = float(value)
            except (TypeError, ValueError):
                AppKit.NSBeep()
        elif key == "sourceAxis_3":
            axisName = self.axisOrder[2]
            try:
                self.location[axisName] = float(value)
            except (TypeError, ValueError):
                AppKit.NSBeep()
        elif key == "sourceAxis_4":
            axisName = self.axisOrder[3]
            try:
                self.location[axisName] = float(value)
            except (TypeError, ValueError):
                AppKit.NSBeep()
        elif key == "sourceAxis_5":
            axisName = self.axisOrder[4]
            try:
                self.location[axisName] = float(value)
                if self.wasEditedCallback:
                    self.wasEditedCallback(self)
            except (TypeError, ValueError):
                AppKit.NSBeep()
        elif key == "sourceLayerNameKey":
            self.layerName = value
        if self.wasEditedCallback is not None:
            self.wasEditedCallback(self)

    def setDocumentNeedSave(self, something=None):
        xx
    
class KeyedInstanceDescriptor(AppKit.NSObject,
        metaclass=ClassNameIncrementer
        ):
    def __new__(cls):
        self = cls.alloc().init()
        self.dir = None
        self.filename = None    # the filename as it appears in the document
        self.path = None
        self.name = None
        self.location = None
        self.familyName = None
        self.styleName = None
        self.postScriptFontName = None
        self.styleMapFamilyName = None
        self.styleMapStyleName = None
        self.localisedStyleName = {}
        self.localisedFamilyName = {}
        self.localisedStyleMapStyleName = {}
        self.localisedStyleMapFamilyName = {}
        self.glyphs = {}
        self.axisOrder = []
        self.kerning = True
        self.info = True
        self.lib = {}
        return self

    @python_method
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
        copy.filename = self.filename
        copy.location = {}
        copy.location.update(self.location)
        copy.name = self.name
        #copy.setName()
        return copy
        
    def setName(self):
        # make a name attribute based on the location
        name = ['instance', self.familyName, self.styleName]
        for k, v in self.location.items():
            name.append("%s_%3.3f"%(k, v))
        self.name = "_".join(name)
        
    @python_method
    def setAxisOrder(self, names):
        self.axisOrder = names

    def instanceHasFileKey(self):
        if self.path is None:
            return ""
        if os.path.exists(self.path):
            return checkSymbol
        return ""
    
    @python_method
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
        if self.filename is not None:
            if self.dir is not None:
                return self.filename
        return "[pending save]"
    
    @python_method
    def setDocumentFolder(self, docFolder):
        # let the descriptor know what the document folder is
        # so that the descriptor can do some validation if the paths
        self.dir = docFolder
    
    @python_method
    def makePath(self):
        # using the document folder and the file name
        # we should be able to make an absolute path
        if self.filename is not None and self.dir is not None:
            self.path = os.path.abspath(os.path.join(self.dir, self.filename))
        
    @python_method
    def setPathRelativeTo(self, docFolder, instancesFolderName):
        self.dir = os.path.join(docFolder, instancesFolderName)
        self.path = os.path.join(self.dir, fileName)

    def setValue_forUndefinedKey_(self, value=None, key=None):
        if key == "instanceFamilyNameKey":
            self.familyName = value
        elif key == "instanceUFONameKey":
            # manual text edit to the path
            self.filename = value
            self.makePath()
        elif key == "instanceStyleNameKey":
            self.styleName = value
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


class KeyedAxisDescriptor(AppKit.NSObject,
        metaclass=ClassNameIncrementer
        ):
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
        self.hidden = False
        self.map = []
        self.controller = None    # weakref to controller
        return self

    @python_method
    def serialize(self):
        # output to a dict, used in testing
        return dict(
            tag=self.tag,
            name=self.name,
            labelNames=self.labelNames,
            maximum=self.maximum,
            minimum=self.minimum,
            default=self.default,
            hidden=self.hidden,
            map=self.map,
        )

    @python_method
    def renameAxis(self, oldName, newName):
        if self.name == oldName:
            self.name = newName
    
    def hiddenKey(self):
        if self.hidden: return "1"
        return "0"
        
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
        elif key == "hiddenKey":
            self.hidden = value
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


class ConditionDict(object):
    def __init__(self, callback=None):
        self.data = {}
        self.callback = callback
        
    def __getitem__(self, key):
        if not key in self.data:
            raise IndexError    
    def __setitem__(self, key, value):
        self.data[key] = value

#a = ConditionDict()
#a['a'] = 10
        
class KeyedDocReader(dsd.BaseDocReader):
    ruleDescriptorClass = KeyedRuleDescriptor
    axisDescriptorClass = KeyedAxisDescriptor
    sourceDescriptorClass = KeyedSourceDescriptor
    instanceDescriptorClass = KeyedInstanceDescriptor
    
class KeyedDocWriter(dsd.BaseDocWriter):
    ruleDescriptorClass = KeyedRuleDescriptor
    axisDescriptorClass = KeyedAxisDescriptor
    sourceDescriptorClass = KeyedSourceDescriptor
    instanceDescriptorClass = KeyedInstanceDescriptor

def newImageListCell():
    cell = AppKit.NSImageCell.alloc().init()
    cell.setImageAlignment_(AppKit.NSImageAlignTop)
    cell.setImageFrameStyle_(AppKit.NSImageFrameNone)
    return cell

class DesignSpaceEditor(BaseWindowController):
    preferredAxes = [
        ("weight", "wght", 0, 1000, 0),
        ("width", "wdth", 0, 1000, 0),
        ("optical", "opsz", 3, 1000, 16),
        ]

    def __init__(self, designSpacePath=None):
        self.documentNeedSave = False
        self._documentIconImagePath = os.path.join(designspaceBundle.resourcesPath(), "toolbar_designspace.pdf")
        self._axesPath = os.path.join(designspaceBundle.resourcesPath(), "toolbar_icon_axes.pdf")
        self._sourcesPath = os.path.join(designspaceBundle.resourcesPath(), "toolbar_icon_sources.pdf")
        self._instancesPath = os.path.join(designspaceBundle.resourcesPath(), "toolbar_icon_instances.pdf")
        self._rulesPath = os.path.join(designspaceBundle.resourcesPath(), "toolbar_icon_rules.pdf")
        self._reportPath = os.path.join(designspaceBundle.resourcesPath(), "toolbar_icon_report.pdf")
        self._savePath = os.path.join(designspaceBundle.resourcesPath(), "toolbar_icon_save.pdf")
        self._generatePath = os.path.join(designspaceBundle.resourcesPath(), "toolbar_icon_generate.pdf")
        self._settingsIconPath = os.path.join(designspaceBundle.resourcesPath(), "toolbar_icon_settings.pdf")
        self.settingsIdentifier = "%s.%s" % (designSpaceEditorSettings.settingsIdentifier, "general")
        self.updateFromSettings()
        self.designSpacePath = designSpacePath
        self.doc = None
        self._newInstanceCounter = 1
        self._newRuleCounter = 1
        self._selectedRule = None
        self._selectedConditionSetIndex = None
        self._settingConditionsFlag = False
        self._settingGlyphsFlag = False
        if self.designSpacePath is None:
            fileNameTitle = "Untitled.designspace"
        else:
            fileNameTitle = os.path.basename(self.designSpacePath)
        self.w = vanilla.Window((940, 350),
                fileNameTitle,
                minSize=(800,300),
                autosaveName = "com.letterror.designspaceeditor",
                fullScreenMode = None,
                )
        self._updatingTheAxesNames = False
        if version[0] == '2':
            thisFontClass = fontParts.nonelab.font.RFont
        else:
            thisFontClass = None
        self.doc = LiveDesignSpaceProcessor(readerClass=KeyedDocReader, writerClass=KeyedDocWriter)
        self.doc.useVarlib = True
        _numberFormatter = AppKit.NSNumberFormatter.alloc().init()
        toolbarItems = [
            {
                'itemIdentifier': "toolbarAxes",
                'label': 'Axes',
                'callback': self.showTab,
                'imagePath': self._axesPath,
            },
            {
                'itemIdentifier': "toolbarSources",
                'label': 'Sources',
                'callback': self.showTab,
                'imagePath': self._sourcesPath,
            },

            {
                'itemIdentifier': "toolbarInstances",
                'label': 'Instances',
                'callback': self.showTab,
                'imagePath': self._instancesPath,
            },
            {
                'itemIdentifier': "toolbarRules",
                'label': 'Rules',
                'callback': self.showTab,
                'imagePath': self._rulesPath,
            },
            {
                'itemIdentifier': AppKit.NSToolbarFlexibleSpaceItemIdentifier,
            },
            {
                'itemIdentifier': "toolbarSave",
                'label': 'Save',
                'callback': self.save,
                'imagePath': self._savePath,
            },
            {
                'itemIdentifier': "generate",
                'label': 'Generate',
                'callback': self.callbackGenerate,
                'imagePath': self._generatePath,
            },
            {
                'itemIdentifier': "toolbarReport",
                'label': 'Problems',
                'callback': self.showTab,
                'imagePath': self._reportPath,
            },
            {
                'itemIdentifier': AppKit.NSToolbarFlexibleSpaceItemIdentifier,
            },
            {
                'itemIdentifier': "settings",
                'label': 'Settings',
                'callback': self.toolbarSettings,
                'imagePath': self._settingsIconPath,
            },
        ]
        self.w.addToolbar("DesignSpaceToolbar", toolbarItems)
        
        fileIconWidth = 30
        ufoNameWidth = 250
        axisValueWidth = 80
        familyNameWidth = 130
        masterColDescriptions = [
                {   'title': '',
                    'key':'sourceHasFileKey',
                    'width':fileIconWidth,
                    'editable':False,
                },
                {   'title': 'D',
                    'key':'defaultMasterKey',
                    'width':fileIconWidth,
                    'editable':False,
                },
                {   'title': 'UFO',
                    'key':'sourceUFONameKey',
                    'width':ufoNameWidth,
                    'editable':True,
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
                {   'title': 'Layer',
                    'key':'sourceLayerNameKey',
                    'width':familyNameWidth,
                    "editable": True
                },
                {   'title': 'Axis 1',
                    'key':'sourceAxis_1',
                    'width':axisValueWidth,
                    'editable':True,
                    'formatter': _numberFormatter,
                },
                {   'title': 'Axis 2',
                    'key':'sourceAxis_2',
                    'width':axisValueWidth,
                    'editable':True,
                    'formatter': _numberFormatter,
                },
                {   'title': 'Axis 3',
                    'key':'sourceAxis_3',
                    'width':axisValueWidth,
                    'editable':True,
                    'formatter': _numberFormatter,
                },
                {   'title': 'Axis 4',
                    'key':'sourceAxis_4',
                    'width':axisValueWidth,
                    'editable':True,
                    'formatter': _numberFormatter,
                },
                {   'title': 'Axis 5',
                    'key':'sourceAxis_5',
                    'width':axisValueWidth,
                    'editable':True,
                    'formatter': _numberFormatter,
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
                    'editable':True,
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
                    'formatter': _numberFormatter,
                },
                {   'title': 'Axis 2',
                    'key':'instanceAxis_2',
                    'width':axisValueWidth,
                    'editable':True,
                    'formatter': _numberFormatter,
                },
                {   'title': 'Axis 3',
                    'key':'instanceAxis_3',
                    'width':axisValueWidth,
                    'editable':True,
                    'formatter': _numberFormatter,
                },
                {   'title': 'Axis 4',
                    'key':'instanceAxis_4',
                    'width':axisValueWidth,
                    'editable':True,
                    'formatter': _numberFormatter,
                },
                {   'title': 'Axis 5',
                    'key':'instanceAxis_5',
                    'width':axisValueWidth,
                    'editable':True,
                    'formatter': _numberFormatter,
                },
            ]
        axisNameColumnWidth = 100
        axisColDescriptions = [
                {   'title': "®",
                    'key':'registeredTagKey',
                    'width':2*fileIconWidth,
                    'editable':False,
                },
                {   'title': 'Name',
                    'key':'axisNameKey',
                    'width':axisNameColumnWidth,
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
                    'formatter': _numberFormatter,
                },
                {   'title': 'Default',
                    'key':'axisDefaultKey',
                    'width':100,
                    'editable':True,
                    'formatter': _numberFormatter,
                },
                {   'title': 'Maximum',
                    'key':'axisMaximumKey',
                    'width':100,
                    'editable':True,
                    'formatter': _numberFormatter,
                },
                {   'title': 'Labelname',
                    'key':'labelNameKey',
                    'width':150,
                    'editable':True,
                },
                {   'title': 'Hide',
                    'key':'hiddenKey',
                    'width':30,
                    #'editable':True,
                    "cell": vanilla.CheckBoxListCell()
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
                {   'title': 'Name',
                    'key':'glyphNameKey',
                    'width':150,
                    'editable':False,
                },
                {   'title': 'Unicode',
                    'key':'unicodeKey',
                    'width':50,
                    'editable':False,
                },
        ]
        toolbarHeight = 24
        groupStart = 30
        buttonMargin = 2
        buttonHeight = 20
        titleOffset = 100
        sectionTitleSize = (65, 3, 100, 20)
        self.axesGroup = self.w.axesGroup = vanilla.Group((0, groupStart,0, -30))
        self.axesItem = vanilla.List((0, toolbarHeight, -0, -0), [], columnDescriptions=axisColDescriptions, editCallback=self.callbackAxesListEdit)
        self.axesGroup.title = vanilla.TextBox(sectionTitleSize, "Axes")
        self.axesGroup.l = self.axesItem
        linkButtonSize = (titleOffset+48, buttonMargin+1, 30, buttonHeight)
        firstButtonSize = (titleOffset+78,buttonMargin+1,50,buttonHeight)
        secondButtonSize = (titleOffset+130,buttonMargin+1,100,buttonHeight)
        first_and_secondButtonSize = (titleOffset+78,buttonMargin+1,150,buttonHeight)
        thirdButtonSize = (titleOffset+232,buttonMargin+1,100,buttonHeight)
        statusTextSize = (titleOffset+165, buttonMargin+4,-10,buttonHeight)
        addButtonSize = (titleOffset+102,buttonMargin+1,50,buttonHeight)
        axisToolDescriptions = [
            {'title': "+", 'width': 20,},
            {'title': "-", 'width': 20}
            ]
        self.axesGroup.tools = vanilla.SegmentedButton(
            (buttonMargin,buttonMargin,100,buttonHeight),
            segmentDescriptions=axisToolDescriptions,
            selectionStyle="momentary",
            callback=self.callbackAxisTools)
        #self.axesGroup.axesFromMastersButton = Button(
        #    first_and_secondButtonSize, "Deduce from Masters",
        #    callback=self.callbackAxesFromSources,
        #    sizeStyle="small")
        
        self.mastersGroup = self.w.mastersGroup = vanilla.Group((0,groupStart,0, -30))
        self.mastersGroup.title = vanilla.TextBox(sectionTitleSize, "Sources: UFOs and Layers")
        masterToolDescriptions = [
            {'title': "+", 'width': 20,},
            {'title': "-", 'width': 20},
            ]
        self.mastersItem = vanilla.List((0, toolbarHeight, -0, -0), [],
            columnDescriptions=masterColDescriptions,
            #doubleClickCallback=self.callbackMastersDblClick
            selectionCallback=self.callbackMasterSelection
            )
        self.mastersGroup.l = self.mastersItem
        self.mastersGroup.tools = vanilla.SegmentedButton(
            (buttonMargin, buttonMargin,100,buttonHeight),
            segmentDescriptions=masterToolDescriptions,
            selectionStyle="momentary",
            callback=self.callbackMasterTools)
        self.mastersGroup.openButton = vanilla.Button(
            firstButtonSize, "Open",
            callback=self.callbackOpenMaster,
            sizeStyle="small")
        self.mastersGroup.openButton.enable(False)
        self.mastersGroup.addOpenFontsButton = vanilla.Button(
            first_and_secondButtonSize, "Add Open UFOs",
            callback=self.callbackAddOpenFonts,
            sizeStyle="small")
        #self.mastersGroup.makeDefaultButton = Button(
        #    secondButtonSize, "Make Default",
        #    callback=self.callbackMakeDefaultMaster,
        #    sizeStyle="small")
        #self.mastersGroup.makeDefaultButton.enable(False)
        self.mastersGroup.loadNamesFromSourceButton = vanilla.Button(
            thirdButtonSize, "Load Names",
            callback=self.callbackGetNamesFromSources,
            sizeStyle="small")
        self.mastersGroup.loadNamesFromSourceButton.enable(False)
        
        self.instancesGroup = self.w.instancesGroup = vanilla.Group((0,groupStart,0, -30))
        self.instancesGroup.title = vanilla.TextBox(sectionTitleSize, "Instances")
        self.instancesItem = vanilla.List((0, toolbarHeight, -0, -0), [],
            columnDescriptions=instanceColDescriptions,
            selectionCallback=self.callbackInstanceSelection,
        )
        self.instancesGroup.duplicateButton = vanilla.Button(
            secondButtonSize, "Duplicate",
            callback=self.callbackDuplicateInstance,
            sizeStyle="small")
        self.instancesGroup.duplicateButton.enable(False)

        instancesToolDescriptions = [
            {'title': "+", 'width': 20,},
            {'title': "-", 'width': 20},
            ]

        self.instancesGroup.tools = vanilla.SegmentedButton(
            (buttonMargin, buttonMargin,100,buttonHeight),
            segmentDescriptions=instancesToolDescriptions,
            selectionStyle="momentary",
            callback=self.callbackInstanceTools)
        self.instancesGroup.l = self.instancesItem
        self.instancesGroup.openButton = vanilla.Button(
            firstButtonSize, "Open",
            callback=self.callbackOpenInstance,
            sizeStyle="small")
        self.instancesGroup.openButton.enable(False)
        
        self.glyphsGroup = vanilla.Group((0,0,0,0))
        self.glyphsItem = vanilla.List((0, toolbarHeight, -0, -0), [],
            columnDescriptions=glyphsColDescriptions,
            #selectionCallback=self.callbackInstanceSelection,
        )
        self.glyphsGroup.l = self.glyphsItem
        
        ruleNameColDescriptions = [
                {   'title': 'Rule',
                    'key':'nameKey',
                    #'width':40,
                    'editable':True,
                },
            ]
        ruleConditionSetColDescriptions = [
                {   'title': 'Condition Sets',
                    'key':'nameKey',
                    #'width':40,
                    'editable':False,
                },
            ]
        
        ruleConditionColDescriptions = [
                {   'title': 'Axis',
                    'key':'name',
                    'width':axisNameColumnWidth,
                    'editable':False,
                },
                {   'title': 'Minimum',
                    'key':'minimum',
                    'width':axisValueWidth,
                    'editable':True,
                    'formatter': _numberFormatter,
                },
                {   'title': 'Maximum',
                    'key':'maximum',
                    'width':axisValueWidth,
                    'editable':True,
                    'formatter': _numberFormatter,
                },
            ]
        ruleGlyphsColDescriptions = [
                {   'title': 'Swap',
                    'key':'name',
                    #'width':40,
                    'editable':True,
                },
                {   'title': 'with',
                    'key':'with',
                    #'width':40,
                    'editable':True,
                },
            ]
        
        listMargin = 5
        self.rulesGroup = self.w.ruleGroup = vanilla.Group((0,groupStart,0, -30))
        self.rulesGroup.title = vanilla.TextBox((50, 3, 150, 20), "Rules")
        ruleToolbarHeight = 25
        self.rulesNames = vanilla.List((0,ruleToolbarHeight, 200,-0), [],
            columnDescriptions=ruleNameColDescriptions,
            selectionCallback=self.callbackRuleNameSelection,
            drawFocusRing = False,
            showColumnTitles = False
        )

        ruleGlyphListLeftMargin = 200+listMargin
        self.rulesGroup.title3 = vanilla.TextBox((ruleGlyphListLeftMargin + 50, 3, 150, 20), "Subs")
        self.rulesGlyphs = vanilla.List((ruleGlyphListLeftMargin,ruleToolbarHeight, 200,-0), [],
            columnDescriptions=ruleGlyphsColDescriptions,
            editCallback = self.callbackEditRuleGlyphs,
            selectionCallback = self.callbackGlyphsSubsSelection,
            drawFocusRing = False,
            showColumnTitles = False
        )

        ruleConditionSetListLeftMargin = 400+3*listMargin
        self.rulesGroup.title2 = vanilla.TextBox((ruleConditionSetListLeftMargin + 50, 3, 250, 20), "Conditionsets")
        self.rulesConditionSets = vanilla.List((ruleConditionSetListLeftMargin,ruleToolbarHeight, 100-listMargin,-0), [],
            #columnDescriptions=ruleConditionSetColDescriptions,
            selectionCallback = self.callbackSelectedConditionSet,
            drawFocusRing = False,
            showColumnTitles = False,
            allowsMultipleSelection=False,
        )
        ruleAxesListLeftMargin = ruleConditionSetListLeftMargin + 95 +listMargin
        self.rulesConditions = vanilla.List((ruleAxesListLeftMargin,ruleToolbarHeight, 300-listMargin,-0), [],
            columnDescriptions=ruleConditionColDescriptions,
            editCallback = self.callbackEditRuleCondition,
            drawFocusRing = False,
            showColumnTitles = False,
            allowsMultipleSelection = False,
        )

        self.rulesGroup.rulesNameList = self.rulesNames
        self.rulesGroup.conditionSets = self.rulesConditionSets
        self.rulesGroup.conditions = self.rulesConditions
        self.rulesGroup.glyphs = self.rulesGlyphs
        # segmented button for + - rules
        self.rulesGroup.tools = vanilla.SegmentedButton(
            (buttonMargin, buttonMargin,100,buttonHeight),
            segmentDescriptions=instancesToolDescriptions,
            selectionStyle="momentary",
            callback=self.callbackRulesTools)
        self.rulesGroup.conditionSetTools = vanilla.SegmentedButton(
            (ruleConditionSetListLeftMargin, buttonMargin,100,buttonHeight),
            segmentDescriptions=instancesToolDescriptions,
            selectionStyle="momentary",
            callback=self.callbackConditionSetTools)
        self.rulesGroup.glyphTools = vanilla.SegmentedButton(
            (ruleGlyphListLeftMargin, buttonMargin,100,buttonHeight),
            segmentDescriptions=instancesToolDescriptions,
            selectionStyle="momentary",
            callback=self.callbackRuleGlyphTools)
        
        self.reportGroup = self.w.reportGroup = vanilla.Group((0,groupStart,0,-30))
        reportColumns = [
                {   'title': '',
                    'key':'problemIcon',
                    'width':2*fileIconWidth,
                    'editable':False,
                },
                {   'title': 'Data',
                    'key':'problemClass',
                    'width':160,
                    'editable':False,
                },
                {   'title': 'Description',
                    'key':'problemDescription',
                    'width':400,
                    'editable':False,
                },
                {   'title': 'Data',
                    'key':'problemData',
                    'width':500,
                    'editable':False,
                },
            ]
        self.reportGroup.text = vanilla.List((0,toolbarHeight,-0,0), columnDescriptions=reportColumns, items=[])
        
        descriptions = [
           dict(label="Axes", view=self.axesGroup, size=138, collapsed=False, canResize=False),
           dict(label="Masters", view=self.mastersGroup, size=135, collapsed=False, canResize=True),
           dict(label="Instances", view=self.instancesGroup, size=135, collapsed=False, canResize=True),
           dict(label="Rules", view=self.rulesGroup, size=135, collapsed=False, canResize=True),
           dict(label="Report", view=self.reportGroup, size=170, collapsed=True, canResize=True),
           #dict(label="Glyphs", view=self.glyphsGroup, size=250, collapsed=False, canResize=True),
           # this panel will show glyphs and compatibiility.
        ]
        
        if self.designSpacePath is not None:
            self.read(self.designSpacePath)
            self.updateAxesColumns()
        self.enableInstanceList()
        for sourceDescriptor in self.doc.sources:
            sourceDescriptor.wasEditedCallback = self.sourceDescriptorWasEditedCallback
        self.w.open()
        if self.designSpacePath is not None:
            self.w.getNSWindow().setRepresentedURL_(AppKit.NSURL.fileURLWithPath_(self.designSpacePath))

        self.w.bind("became main", self.callbackBecameMain)
        self.w.bind("close", self.callbackCleanup)
        
        self.w.vanillaWrapper = weakref.ref(self)
        self.setUpBaseWindowBehavior()
        
        
        # @@
        self.axesGroup.show(True)
        self.mastersGroup.show(False)
        self.instancesGroup.show(False)
        self.rulesGroup.show(False)
        self.reportGroup.show(False)
    
    def showTab(self, sender):
        wantTab = sender.label()
        if wantTab == "Axes":
            self.axesGroup.show(True)
            self.mastersGroup.show(False)
            self.instancesGroup.show(False)
            self.rulesGroup.show(False)
            self.reportGroup.show(False)
        elif wantTab == "Sources":
            self.axesGroup.show(False)
            self.mastersGroup.show(True)
            self.instancesGroup.show(False)
            self.rulesGroup.show(False)
            self.reportGroup.show(False)
        elif wantTab == "Instances":
            self.axesGroup.show(False)
            self.mastersGroup.show(False)
            self.instancesGroup.show(True)
            self.rulesGroup.show(False)
            self.reportGroup.show(False)
        elif wantTab == "Rules":
            self.axesGroup.show(False)
            self.mastersGroup.show(False)
            self.instancesGroup.show(False)
            self.rulesGroup.show(True)
            self.reportGroup.show(False)
        elif wantTab == "Problems":
            self.axesGroup.show(False)
            self.mastersGroup.show(False)
            self.instancesGroup.show(False)
            self.rulesGroup.show(False)
            self.reportGroup.show(True)

    def setDocumentNeedSave(self, state=True):
        self.documentNeedSave = state
        if state:
            #self.w.file.saveButton.enable(True)
            self.w.getNSWindow().setDocumentEdited_(True)
        else:
            #self.w.file.saveButton.enable(False)
            self.w.getNSWindow().setDocumentEdited_(False)

    def close(self):
        # close the window
        self.w.close()
        
    def callbackCleanup(self, sender=None):
        self.w.document = None
        for source in self.doc.sources:
            source.callbackCleanup()
    
    def callbackRenameAxes(self, oldName, newName):
        # validate the new name, make sure we don't duplicate an existing name
        for axis in self.doc.axes:
            if newName == axis.name:
                return
        for source in self.doc.sources:
            source.renameAxis(oldName, newName)
        for instance in self.doc.instances:
            instance.renameAxis(oldName, newName)
        for rule in self.doc.rules:
            rule.renameAxis(oldName, newName)
        for axis in self.doc.axes:
            axis.renameAxis(oldName, newName)
        self.updateRules()
        #self.updateDocumentPath()
        self.updatePaths()
        self.validate()
        self.setDocumentNeedSave(True)
    
    def _getAxisNames(self):
        # return a list of current axis names
        names = []
        for axis in self.doc.axes:
            names.append(axis.name)
        return names
        
    def _getDefaultValue(self, identifier, key):
        data = getExtensionDefault(identifier, dict())
        return data.get(key, defaultOptions[key])

    def getInstancesFolder(self):
        return self._getDefaultValue("%s.general" % settingsIdentifier, "instanceFolderName")
    
    def validate(self):
        # validate with the designspaceErrors checker
        checker = DesignSpaceChecker(self.doc)
        checker.checkEverything()
        print(checker.problems)
        report = []
        for problem in checker.problems:
            icon=""
            cat, desc = problem.getDescription()
            print('cat', cat)
            if problem.category in [0,1,2]:
                icon="❗️"
            elif problem.category in [3,4,5]:
                icon="❕"
            data = ""
            if problem.data:
                t = []
                for k, v in problem.data.items():
                    t.append("%s: %s" % (k, str(v)))
                data = ", ".join(t)
            d = dict(problemIcon=icon, problemClass=cat, problemDescription=desc, problemData=data)
            report.append(d)
        self.reportGroup.text.set(report)
        
    def old_validate(self):
        # validate all data and write a report here.
        report = []
        
        # document and path
        if self.designSpacePath is None:
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
        
        # rules XXXX
        axisData = {}
        axisNames = []
        for axis in self.doc.axes:
            axisData[axis.name] = (axis.minimum, axis.maximum)
            axisNames.append(axis.name)
        if len(self.doc.rules)==0:
            report.append("No rules defined.")
        else:
            report.append("Rules:")
            for rule in self.doc.rules:
                for cd in rule.conditions:
                    conditionAxis = cd['name']
                    if conditionAxis not in axisNames:
                        report.append("\tCondition in rule %s references unknown axis %s"%(rule.name, cd['name']))
                    if conditionAxis in axisData:
                        axisMin, axisMax = axisData[conditionAxis]
                        if cd.get('minimum') is None:
                            report.append("\tCondition in rule %s has no minimum on axis %s, will use %3.3f from axis"%(rule.name, conditionAxis, axisMin))
                        elif cd.get('maximum') is None:
                            report.append("\tCondition in rule %s has no maximum on axis %s, will use %3.3f from axis"%(rule.name, conditionAxis, axisMax))
                                
        
        self.reportGroup.text.set("\n".join(report))
    
    def updateFromSettings(self):
        extensionSettings = getExtensionDefault(self.settingsIdentifier, dict())
        self.instanceFolderName = extensionSettings.get('instanceFolderName', "instances")

    def applySettingsCallback(self, sender):
        # callback for the settings window
        self.updateFromSettings()
        self.updatePaths()
        self.validate()
        
    def toolbarSettings(self, sender):
        designSpaceEditorSettings.Settings(self.w, self.applySettingsCallback)
            
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
                        if version[0] == '2':
                            font = OpenFont(path, showInterface=True)
                        else:
                            font = OpenFont(path, showUI=True)
                except:
                    print("Bad UFO:", path)
                    pass
                progress.update()
            progress.close()            
    
    def callbackGenerate(self, sender):
        #from mutatorMath.ufo import build
        if self.designSpacePath is None:
            return
        self.doc.problems = []
        progress = ProgressWindow("Generating instance UFO’s…", 10, parentWindow=self.w)
        try:
            messages = self.doc.generateUFO()
        except ufoProcessor.UFOProcessorError:
            error_type, error_instance, traceback = sys.exc_info()
            self.doc.problems.append(str(error_instance.msg))
        except:
            import traceback
            traceback.print_exc()
        finally:
            progress.close()
        if self.doc.problems:
            self.reportGroup.text.set("\n".join([str(s) for s in self.doc.problems]))
            
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
        sourceColumnTitleOffset = 6    # index of the column where we can start messing with the names
        for col in range(sourceColumnTitleOffset, len(columns)):
            column = columns[col]
            try:
                newTitle = names[col-sourceColumnTitleOffset]
            except IndexError:
                newTitle = ""
            column.setTitle_(newTitle)
        self.mastersItem.getNSTableView().reloadData()

        columns = self.instancesItem.getNSTableView().tableColumns()
        instancesColumnTitleOffset = 4
        for col in range(instancesColumnTitleOffset, len(columns)):
            column = columns[col]
            try:
                newTitle = names[col-instancesColumnTitleOffset]
            except IndexError:
                newTitle = ""
            column.setTitle_(newTitle)
        self.instancesItem.getNSTableView().reloadData()
        
    def read(self, designSpacePath):
        if designSpacePath is not None:
            try:
                self.doc.read(designSpacePath)
            except:
                self.doc = None
                self.validate()
                return
        #if len(self.doc.axes)==0:
        #    self.doc.checkAxes()
        for item in self.doc.axes:
            item.controller = weakref.ref(self)
        self.axesItem.set(self.doc.axes)
        self.mastersItem.set(self.doc.sources)
        self.instancesItem.set(self.doc.instances)
        self.rulesGroup.rulesNameList.set(self.doc.rules)
        self.rulesGroup.rulesNameList.setSelection([0])
        self.updatePaths()
        self.doc.loadFonts()
        self.findDefault()
        self.validate()
        # what if we replace the loaded fonts with locally loaded fonts?
        # ('loaded', 'temp_master.0', <RFont 'MutatorMathTest LightCondensed' path='u'/Users/erik/code/braces/MutatorSansLightCondensed.ufo'' at 4581778896>)
        # ('loaded', 'temp_master.1', <RFont 'MutatorMathTest BoldCondensed' path='u'/Users/erik/code/braces/MutatorSansBoldCondensed.ufo'' at 4581744080>)

    def findDefault(self):
        # find the source descriptor that is the default. set this value in the sourcedescriptor
        for sd in self.doc.sources:
            sd.makeDefault(False)
        defaultSourceDescriptor = self.doc.findDefault()
        if defaultSourceDescriptor is not None:
            defaultSourceDescriptor.makeDefault(True)

    def getSaveDirFromMasters(self):
        options = {}
        for master in self.mastersItem:
            if master.path is not None:
                thisFileDir = os.path.dirname(master.path)
                options[thisFileDir] = True
        if len(options)==1:
            # neat and tidy, all masters in a folder
            return list(options.keys())[0]
        if options:
            paths = list(options.keys())
            paths.sort()
            return paths[0]
        return None
            
    def save(self, sender=None):
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
    
    def updatePaths(self):
        # a fresh attempt at updating all the paths in the sources and instances
        # the item.filename is leading
        if self.designSpacePath is None:
            return
        docFolder = os.path.dirname(self.designSpacePath)
        for item in self.mastersItem:
            item.setDocumentFolder(docFolder)
            item.makePath()
        for item in self.instancesItem:
            item.setDocumentFolder(docFolder)
            item.makePath()

    def updateDocumentPath(self):
        # so we have the path for this document
        # we need to make sure the instances are all in the right place
        if self.designSpacePath is None:
            return
        docFolder = os.path.dirname(self.designSpacePath)
        for item in self.instancesItem:
            item.setDocPath(docFolder)

    def finalizeSave(self, path=None):
        self.designSpacePath = path
        # so we have the path for this document
        # we need to make sure the instances are all in the right place
        for sourceDescriptor in self.mastersItem:
            if sourceDescriptor.filename == sourceDescriptor.path:
                # - new unsaved document
                # - masters added, we have no relative path
                # - in this case the .filename and .path are the same
                #     so we can check for this and update the .filename
                sourceDescriptor.setDocumentFolder(self.designSpacePath)
                sourceDescriptor.filename = os.path.relpath(sourceDescriptor.path, os.path.dirname(self.designSpacePath))
                sourceDescriptor.makePath()
        for instanceDescriptor in self.instancesItem:
            if instanceDescriptor.filename == instanceDescriptor.path:
                # - new unsaved document
                # - instance added, we have no relative path
                instanceDescriptor.setDocumentFolder(self.designSpacePath)
                instanceDescriptor.filename = os.path.relpath(instanceDescriptor.filename, os.path.dirname(self.designSpacePath))
                instanceDescriptor.makePath()
        self.updatePaths()
        self.doc.write(self.designSpacePath)
        self.w.getNSWindow().setRepresentedURL_(AppKit.NSURL.fileURLWithPath_(self.designSpacePath))
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
        for ruleDescriptor in self.doc.rules:
            self._updateConditions(ruleDescriptor, defaults)
        self.updateRules()                
            
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
    
    def callbackEditRuleGlyphs(self, sender = None):
        if not self._selectedRule:
            return
        if self._settingGlyphsFlag:
            # not actually editing the list, we can skip
            return
        newGlyphs = []
        for item in self.rulesGroup.glyphs:
            newGlyphs.append((item['name'],item['with']))
        self._selectedRule.subs = newGlyphs
        self._checkRuleGlyphListHasEditableEmpty()
    
    def callbackEditRuleCondition(self, sender=None):
        # vanilla callback for selected a specific axis in the condition list
        if not self._selectedRule: return
        if self._selectedConditionSetIndex is None:
            return
        edited = []
        for item in sender.get():
            d = {'minimum':None, 'maximum':None}
            if item.get("minimum") is None:
                d['minimum'] = None
            else:
                try:
                    v = int(item['minimum'])
                except ValueError:
                    v = None
                d['minimum'] = v
            if item.get("maximum") is None:
                d['maximum'] = None
            else:
                try:
                    v = int(item['maximum'])
                except ValueError:
                    v = None
                d['maximum'] = v
            d['name'] = item['name']
            edited.append(d)
        self._selectedRule.conditionSets[self._selectedConditionSetIndex] = edited

    def callbackSelectedConditionSet(self, sender=None):
        sel = sender.getSelection()
        if len(sel) != 1:
            # no selected items
            # empty the conditions on display
            self._selectedConditionSetIndex = None
            self.rulesGroup.conditions.set([])
            self.rulesGroup.conditions.setSelection([])
            # disable the "-" segment
            self.rulesGroup.conditionSetTools._nsObject.setEnabled_forSegment_(False, 1)
            return
        # selected items
        # enable the "-" item
        self.rulesGroup.conditionSetTools._nsObject.setEnabled_forSegment_(True, 1)
        sel = sel[0]
        self._selectedConditionSetIndex = sel
        self._setConditionsFromSelectedConditionSet()
    
    def _setConditionsFromSelectedConditionSet(self):
        # set the conditions from the selected condition set
        if self._selectedConditionSetIndex is None:
            return
        thing = self._selectedRule.conditionSets[self._selectedConditionSetIndex]
        newThing = []
        # XXX make sure we add all the axes here
        for item in thing:
            d = {}
            for k, v in item.items():
                if v is None:
                    v = ""
                d[k]=v
            newThing.append(d)
        self.rulesGroup.conditions.set(newThing)

    def callbackGlyphsSubsSelection(self, sender):
        # vanilla callback for selection in the rules subs / glyphs list
        selection = sender.getSelection()
        if not selection:
            self.rulesGroup.glyphTools._nsObject.setEnabled_forSegment_(False, 1)
        else:            
            self.rulesGroup.glyphTools._nsObject.setEnabled_forSegment_(True, 1)
        
    def callbackRuleNameSelection(self, sender):
        selection = sender.getSelection()
        self._selectedRule = None
        if len(selection) > 1 or len(selection) == 0:
            self._settingConditionsFlag = True
            self._settingConditionsFlag = False
            self._settingGlyphsFlag = True
            self.rulesGroup.glyphs.set([])
            self._settingGlyphsFlag = False
            self.rulesGroup.conditions.enable(False)
            self.rulesGroup.conditions.set([])
            self.rulesGroup.conditions.setSelection([])
            self.rulesGroup.conditionSets.enable(False)
            self.rulesGroup.conditionSets.setSelection([])
            self.rulesGroup.conditionSets.set([])
            self._selectedConditionSetIndex = None
            self.rulesGroup.glyphs.enable(False)
            self.rulesGroup.glyphTools.enable(False)
            # ZZZ
            self.rulesGroup.tools._nsObject.setEnabled_forSegment_(False, 1)
            self.rulesGroup.glyphTools._nsObject.setEnabled_forSegment_(False, 1)
        else:
            self._selectedRule = self.rulesGroup.rulesNameList[selection[0]]
            self._selectedConditionSetIndex = 0
            self.rulesGroup.conditions.enable(True)
            self.rulesGroup.conditionSets.enable(True)
            self._updateConditionSetsList()
            self.rulesGroup.conditionSets.setSelection([0])
            self.rulesGroup.glyphs.enable(True)
            self._settingGlyphsFlag = True
            self._setGlyphNamesToList()
            self._settingGlyphsFlag = False
            self.rulesGroup.glyphTools.enable(True)
            self.rulesGroup.glyphTools._nsObject.setEnabled_forSegment_(False, 1)
            self.rulesGroup.tools._nsObject.setEnabled_forSegment_(True, 1)
            
    def _updateConditionSetsList(self):
        conditionSetsForThisRule = []
        for i, conditionSet in enumerate(self._selectedRule.conditionSets):
            conditionSetsForThisRule.append("set %d" % (i+1))
        self.rulesGroup.conditionSets.set(conditionSetsForThisRule)
    
    def _setGlyphNamesToList(self):
        names = []
        for a, b in self._selectedRule.subs:
            names.append({'name':a, 'with':b})
        self.rulesGroup.glyphs.set(names)
    
    def callbackConditionSetTools(self, sender):
        # vanilla callback for the +- button above the conditionsets
        if sender.get() == 0:
            # + button
            if not self._selectedRule:
                return
            newConditions = []
            for axisDescriptor in self.doc.axes:
                d = {}
                d['name'] = axisDescriptor.name
                d['minimum'] = None
                d['maximum'] = None
                newConditions.append(d)
            self._selectedRule.conditionSets.append(newConditions)
            self._setConditionsFromSelectedConditionSet()
            self._updateConditionSetsList()
        elif sender.get() == 1:
            # + button
            if not self._selectedRule:
                return
            selectedConditionSet = self.rulesConditionSets.getSelection()
            for index in selectedConditionSet:
                del self._selectedRule.conditionSets[index]
            self._updateConditionSetsList()
        # things
                
    def callbackRuleGlyphTools(self, sender):
        if sender.get() == 0:
            # + button
            if not self._selectedRule:
                return
            self._appendGlyphNameToRuleGlyphList(("#name", "#name"))
            #self._selectedRule.subs.append(("<glyph>", "<glyph>"))
            self._setGlyphNamesToList()
        else:
            if not self._selectedRule:
                return
        selected = self.rulesGlyphs.getSelection()
        keepThese = []
        for i, pair in enumerate(self._selectedRule.subs):
            if i not in selected:
                keepThese.append(pair)
        self._selectedRule.subs = keepThese
        self._checkRuleGlyphListHasEditableEmpty()
        self._setGlyphNamesToList()
    
    def _appendGlyphNameToRuleGlyphList(self, names):
        # and make sure the last one remains empty and editable
        if self._selectedRule is None:
            return
        if not names in self._selectedRule.subs:
            self._selectedRule.subs.append(names)
            self.rulesGroup.rulesNameList.set(self.doc.rules)
            
    def _checkRuleGlyphListHasEditableEmpty(self):
        if self._selectedRule is None:
            return
        self.rulesGroup.rulesNameList.set(self.doc.rules)

    def callbackRulesTools(self, sender):
        # add or remove a rule
        if sender.get() == 0:
            # + button
            newRuleDescriptor = KeyedRuleDescriptor()
            newRuleDescriptor.name = "Unnamed Rule %d"%self._newRuleCounter
            newRuleDescriptor.conditionSets = []
            
            oneNewConditionSet = []            
            for axis in self.doc.axes:
                oneNewConditionSet.append(dict(name=axis.name, minimum=axis.minimum, maximum=axis.maximum))
            newRuleDescriptor.conditionSets.append(oneNewConditionSet)                    
            self._newRuleCounter += 1
            self.doc.addRule(newRuleDescriptor)
            self.rulesGroup.rulesNameList.set(self.doc.rules)
        else:
            selection = self.rulesGroup.rulesNameList.getSelection()
            if not selection:
                # no selected rules, nothing to delete
                return
            if len(selection) == 1:
                text = "Do you want to delete this rule?"
            else:
                text = "Do you want to delete %d rules?"%len(selection)
            result = askYesNo(messageText=text, informativeText="There is no undo.", parentWindow=self.w, resultCallback=self.finallyDeleteRule)
    
    def finallyDeleteRule(self, result):
        if result != 1:
            return
        removeThese = []
        for index in self.rulesGroup.rulesNameList.getSelection():
            removeThese.append(id(self.rulesGroup.rulesNameList[index]))
        keepThese = []
        for item in self.doc.rules:
            if id(item) not in removeThese:
                keepThese.append(item)
        self.doc.rules = keepThese
        self.updateRules()
        #self.rulesGroup.rulesNameList.set(self.doc.rules)
        #self.rulesGroup.rulesNameList.setSelection([])
    
    def _updateConditions(self, ruleDescriptor, defaults):
        # this is called when the axes have changed. More, fewer
        # so check the conditions and update them
        keepThese = []
        for cd in ruleDescriptor.conditions:
            if cd.get('name') in defaults:
                # we're good
                keepThese.append(cd)
        ruleDescriptor.conditions = keepThese
        
    def updateRules(self):
        # update the presentation of the rules
        self.rulesGroup.rulesNameList.set(self.doc.rules)
        self.rulesGroup.rulesNameList.setSelection([])
        
    def callbackAxesListEdit(self, sender):
        if self._updatingTheAxesNames == False:
            if sender.getSelection():
                self._updatingTheAxesNames = True        # preventing recursion? XXX
                self.updateAxesColumns()
                self.updateLocations()
                self.axesItem.set(self.doc.axes)
                self._updatingTheAxesNames = False
                self.findDefault()
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
        self.updateRules()
        self.axesItem.set(self.doc.axes)
        self.findDefault()
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
            newInstanceDescriptor.styleName = "Style_%d"%self._newInstanceCounter
            ufoName = "%s-%s.ufo"%(newInstanceDescriptor.familyName, newInstanceDescriptor.styleName)
            self._newInstanceCounter += 1
            if self.designSpacePath is not None:
                # we have a path
                newInstanceDescriptor.setDocumentFolder(os.path.dirname(self.designSpacePath))
                newInstanceDescriptor.filename = os.path.join(self.instanceFolderName, ufoName)
                newInstanceDescriptor.makePath()
            else:
                # we don't have a path
                # we're going to make a new path to <preferred instance folder><ufoname>
                newInstanceDescriptor.filename = os.path.join(self.instanceFolderName, ufoName)
                newInstanceDescriptor.path = None
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
            getFile(messageText="Add new UFO",
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
    
    def callbackAxesFromSources(self, sender):
        # if we have no axes:
        # get the axes from the masters
        # if we have axes:
        # show a dialog first.
        if len(self.doc.axes)==0:
            self.finalizeAxesFromMasters(1)
        else:
            text = "Do you want to deduce the axes from the masters and overwrite the existing ones?"
            result = askYesNo(messageText=text,
                informativeText="There is no undo.",
                parentWindow=self.w,
                resultCallback=self.finalizeAxesFromMasters)

    def finalizeAxesFromMasters(self, result):
        if result != 1:
            return
        self.doc.checkAxes(overwrite=True)
        self.axesItem.set(self.doc.axes)
        self.validate()
        for item in self.doc.axes:
            item.controller = weakref.ref(self)
        
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
        self.doc.findDefault()
        self.axesItem.set(self.doc.axes)
        self.validate()
        
    def callbackGetNamesFromSources(self, sender):
        # open the source fonts and load the family and stylenames
        for i in self.mastersItem.getSelection():
            selectedItem = self.doc.sources[i]
            if selectedItem.sourceHasFileKey():
                f = OpenFont(selectedItem.path, showUI=True)
                selectedItem.familyName = f.info.familyName
                selectedItem.styleName = f.info.styleName
                #f.close()
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
            else:
                item.callbackCleanup()
        self.doc.sources = keepThese
        self.mastersItem.set(self.doc.sources)
        self.enableInstanceList()
        self.validate()
    
    def sourceDescriptorWasEditedCallback(self, sd):
        # callback to be given to keyedSourceDescriptor when values are edited.
        self.findDefault()
        
    def addSourceFromFont(self, font):
        defaults = {}
        for axisDescriptor in self.doc.axes:
            defaults[axisDescriptor.name] = axisDescriptor.default
        sourceDescriptor = KeyedSourceDescriptor()
        sourceDescriptor.wasEditedCallback = self.sourceDescriptorWasEditedCallback
        sourceDescriptor.path = font.path
        sourceDescriptor.familyName = font.info.familyName
        sourceDescriptor.styleName = font.info.styleName
        sourceDescriptor.location = {}
        sourceDescriptor.location.update(defaults)
        if self.designSpacePath is not None:
            sourceDescriptor.setDocumentFolder(self.designSpacePath)
            sourceDescriptor.filename = os.path.relpath(font.path, os.path.dirname(self.designSpacePath))
            sourceDescriptor.makePath()
        else:
            # we're adding sources to an unsaved document
            # that means we can't make a relative path
            # what to do? absolute path to the source?
            sourceDescriptor.filename = font.path
        if len(self.mastersItem)==0:
            # this is the first master we're adding
            # make this the default so we have one.
            sourceDescriptor.makeDefault(True)
        self.doc.addSource(sourceDescriptor)
        self.mastersItem.set(self.doc.sources)

    def finalizeAddMaster(self, paths):
        for path in paths:
            font = OpenFont(path, showUI=True)
            self.addSourceFromFont(font)
        self.updateAxesColumns()
        self.enableInstanceList()
        self.updatePaths()
        self.validate()

    def callbackMasterSelection(self, sender):
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
    
    testWithFile = True    # set to False to test without getfile dialog

    if not testWithFile:
        # test
        DesignSpaceEditor()
    else:
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
    
        results = getFile(messageText="Select a DesignSpace file:", allowsMultipleSelection=True, fileTypes=["designspace"])
        if results is not None:
           for path in results:
               DesignSpaceEditor(path)
