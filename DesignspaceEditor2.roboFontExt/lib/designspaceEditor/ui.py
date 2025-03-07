import os
from copy import deepcopy
import weakref
import AppKit
from objc import super

import vanilla

from fontTools import designspaceLib
from ufoProcessor import InstanceDescriptor, ufoOperator

from mojo.UI import CodeEditor, SliderEditStepper
from mojo.events import addObserver, removeObserver
from mojo.subscriber import WindowController, Subscriber
from mojo.extensions import getExtensionDefault, ExtensionBundle
from mojo.roboFont import AllFonts, OpenFont, RFont, internalFontClasses

from lib.tools.debugTools import ClassNameIncrementer
from lib.tools.misc import coalescingDecorator, tryExceptDecorator

from lib.cells.doubleClickCell import RFDoubleClickCell
from lib.formatters import PathFormatter

from designspaceProblems import DesignSpaceChecker

from designspaceEditor.designspaceLexer import DesignspaceLexer, TextLexer
from designspaceEditor.parsers import mapParser, rulesParser, labelsParser, glyphNameParser, variableFontsParser
from designspaceEditor.parsers.parserTools import numberToString
from designspaceEditor.tools import holdRecursionDecorator, addToolTipForColumn, TryExcept, HoldChanges, symbolImage, NumberListFormatter, SendNotification, notificationConductor, postScriptNameTransformer, styleMapNameTransformer, fileNameForInstance
from designspaceEditor.locationPreview import LocationPreview
from designspaceEditor.designspaceSubscribers import registerOperator, unregisterOperator
from designspaceEditor import extensionIdentifier

designspaceBundle = ExtensionBundle("DesignspaceEditor2")

registeredAxisTags = [
    ("italic", "ital"),
    ("optical", "opsz"),
    ("slant", "slnt"),
    ("width", "wdth"),
    ("weight", "wght"),
]


preferredAxes = [
    ("weight", "wght", 400, 700, 400, dict(en="Weight")),
    ("width", "wdth", 50, 100, 100, dict(en="Width")),
    ("optical", "opsz", 10, 16, 10, dict(en="Optical Size")),
]

designspacenotesLibKey = "designspaceEdit.notes"

numberFormatter = AppKit.NSNumberFormatter.alloc().init()
numberFormatter.setNumberStyle_(AppKit.NSNumberFormatterDecimalStyle)
numberFormatter.setAllowsFloats_(True)
numberFormatter.setLocalizesFormat_(False)
numberFormatter.setUsesGroupingSeparator_(False)

numberListFormatter = NumberListFormatter.alloc().init()

checkSymbol = "✓"
defaultSymbol = "🔹"
defaultDiscreteSymbol = "🔸"
dotSymbol = "⚬"

try:
    infoImage = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_("info.circle.fill", None)
except Exception:
    # older systems
    infoImage = AppKit.NSImage.imageNamed_(AppKit.NSImageNameInfo)


class DesignspaceEditorOperator(ufoOperator.UFOOperator):

    ##### to be removed when RF get a updated ufoOperator
    def sourceNameGenerator(self, prefix="source", count=1):
        name = f"{prefix}.{count}"
        for sourceDescriptor in self.sources:
            if sourceDescriptor.name == name:
                return self.sourceNameGenerator(prefix=prefix, count=count + 1)
        return name

    def _instantiateFont(self, path):
        for font in AllFonts():
            if font.path == path:
                return font.asDefcon()
        return internalFontClasses.createFontObject(path)

    def updateFonts(self, fonts=None):
        if fonts is None:
            fonts = AllFonts()
        super().udpateFonts([font.asDefcon() for font in fonts])

    # axes

    def addAxis(self, axisDescriptor):
        with SendNotification("Axes", action="AddAxis", designspace=self) as notification:
            super().addAxis(axisDescriptor)
            notification["axis"] = axisDescriptor

    def removeAxis(self, axisDescriptor):
        with SendNotification("Axes", action="RemoveAxis", designspace=self, axis=axisDescriptor):
            self.axes.remove(axisDescriptor)

    def addAxisDescriptor(self, **kwargs):
        with SendNotification("Axes", action="AddAxis", designspace=self) as notification:
            axisDescriptor = super().addAxisDescriptor(**kwargs)
            notification["axis"] = axisDescriptor
        return axisDescriptor

    # sources

    def addSource(self, sourceDescriptor):
        with SendNotification("Sources", action="AddSource", designspace=self) as notification:
            super().addSource(sourceDescriptor)
            notification["source"] = sourceDescriptor

    def removeSource(self, sourceDescriptor):
        with SendNotification("Sources", action="RemoveSource", designspace=self, source=sourceDescriptor):
            self.sources.remove(sourceDescriptor)
            if sourceDescriptor.name in self.fonts:
                del self.fonts[sourceDescriptor.name]

    def addSourceDescriptor(self, **kwargs):
        with SendNotification("Sources", action="AddSource", designspace=self) as notification:
            sourceDescriptor = super().addSourceDescriptor(**kwargs)
            notification["source"] = sourceDescriptor
        return sourceDescriptor

    # instances

    def addInstance(self, instanceDescriptor):
        with SendNotification("Instances", action="AddInstance", designspace=self) as notification:
            super().addInstance(instanceDescriptor)
            notification["instance"] = instanceDescriptor

    def removeInstance(self, instanceDescriptor):
        with SendNotification("Instances", action="RemoveInstance", designspace=self, instance=instanceDescriptor):
            self.instances.remove(instanceDescriptor)

    def addInstanceDescriptor(self, **kwargs):
        familyName = kwargs.get("familyName")
        styleName = kwargs.get("styleName")
        if familyName is None:
            if self.instances:
                familyName = self.instances[0].familyName
            elif self.sources:
                familyName = self.sources[0].familyName
            else:
                familyName = "NewFamily"
            kwargs["familyName"] = familyName
        if styleName is None:
            styleName = kwargs["styleName"] = f"Style_{len(self.instances)}"

        if "filename" not in kwargs:
            filename = postScriptNameTransformer(kwargs["familyName"], kwargs["styleName"])
            kwargs["filename"] = os.path.join(getExtensionDefault('instanceFolderName', 'instances'), f"{filename}.ufo")
        if "name" not in kwargs:
            kwargs["name"] = f"instance.{len(self.instances)}"

        with SendNotification("Instances", action="AddInstance", designspace=self) as notification:
            instanceDescriptor = super().addInstanceDescriptor(**kwargs)
            notification["instance"] = instanceDescriptor
        return instanceDescriptor

    # rules

    def addRule(self, ruleDescriptor):
        with SendNotification("Rules", action="AddRule", designspace=self) as notification:
            super().addRule(ruleDescriptor)
            notification["rule"] = ruleDescriptor

    def removeRule(self, ruleDescriptor):
        with SendNotification("Rules", action="RemoveRule", designspace=self, instance=ruleDescriptor):
            self.rules.remove(ruleDescriptor)

    def addRuleDescriptor(self, **kwargs):
        with SendNotification("Rules", action="AddRule", designspace=self) as notification:
            ruleDescriptor = super().addRuleDescriptor(**kwargs)
            notification["rule"] = ruleDescriptor
        return ruleDescriptor

    # location labels

    def addLocationLabel(self, locationLabelDescriptor):
        with SendNotification("LocationLabel", action="addLocationLabel", designspace=self) as notification:
            super().addLocationLabel(locationLabelDescriptor)
            notification["locationLabel"] = locationLabelDescriptor

    def removeLocationLabel(self, locationLabelDescriptor):
        with SendNotification("LocationLabel", action="removeLocationLabel", designspace=self, instance=locationLabelDescriptor):
            self.locationLabels.remove(locationLabelDescriptor)

    def addLocationLabelDescriptor(self, **kwargs):
        with SendNotification("LocationLabel", action="addLocationLabel", designspace=self) as notification:
            locationLabelDescriptor = super().addLocationLabelDescriptor(**kwargs)
            notification["locationLabel"] = locationLabelDescriptor
        return locationLabelDescriptor

    # variable font

    def addVariableFont(self, variableFontDescriptor):
        with SendNotification("VariableFonts", action="AddVariableFont", designspace=self) as notification:
            super().addVariableFont(variableFontDescriptor)
            notification["variableFont"] = variableFontDescriptor

    def removeVariableFont(self, variableFontDescriptor):
        with SendNotification("VariableFonts", action="RemoveVariableFont", designspace=self, instance=variableFontDescriptor):
            self.variableFonts.remove(variableFontDescriptor)

    def addVariableFontDescriptor(self, **kwargs):
        with SendNotification("VariableFonts", action="AddVariableFont", designspace=self) as notification:
            variableFontDescriptor = super().addVariableFontDescriptor(**kwargs)
            notification["variableFont"] = variableFontDescriptor
        return variableFontDescriptor

    def openInterface(self):
        for controller in AllDesignspaceWindows():
            if controller.operator == self:
                controller.w.show()
                return
        controller = DesignspaceEditorController()
        controller.loadOperator(self)

    def close(self):
        for controller in AllDesignspaceWindows():
            if controller.operator == self:
                controller.w.close()
                return

    # send notifications

    def changed(self, clearCaches=True, **kwargs):
        if clearCaches:
            super().changed()
        SendNotification.single(designspace=self, **kwargs)

    def axesChanged(self, **kwargs):
        self.changed(
            clearCaches=kwargs.pop("clearCaches", False),
            who="Axes",
            **kwargs
        )

    def sourcesChanged(self, **kwargs):
        self.changed(
            clearCaches=kwargs.pop("clearCaches", False),
            who="Sources",
            **kwargs
        )

    def instancesChanged(self, **kwargs):
        self.changed(
            clearCaches=kwargs.pop("clearCaches", False),
            who="Instances",
            **kwargs
        )

    def rulesChanged(self, **kwargs):
        self.changed(
            clearCaches=kwargs.pop("clearCaches", False),
            who="Rules",
            **kwargs
        )

    def locationLabelsChanged(self, **kwargs):
        self.changed(
            clearCaches=kwargs.pop("clearCaches", False),
            who="LocationLabels",
            **kwargs
        )

    def variableFontsChanged(self, **kwargs):
        self.changed(
            clearCaches=kwargs.pop("clearCaches", False),
            who="VariableFonts",
            **kwargs
        )

    def notesChanged(self, **kwargs):
        self.changed(
            clearCaches=kwargs.pop("clearCaches", False),
            who="Notes",
            **kwargs
        )

    previewLocationLibKey = f"{extensionIdentifier}.previewLocation"

    def previewLocationChanged(self, location=None, **kwargs):
        self.changed(
            clearCaches=kwargs.pop("clearCaches", False),
            who="PreviewLocation",
            location=location,
            **kwargs
        )

    def getPreviewLocation(self):
        location = self.lib.get(self.previewLocationLibKey)
        if location is None:
            location = self.newDefaultLocation(bend=True)
        return location

    def setPreviewLocation(self, location):
        if location is None:
            if self.previewLocationLibKey in self.lib:
                del self.lib[self.previewLocationLibKey]
        else:
            self.lib[self.previewLocationLibKey] = location
        self.previewLocationChanged(location=location)


class GenerateInstanceSheet:

    def __init__(self, parentWindow, operator, instances):
        self.operator = operator
        # update the path attribute in all given instanceDescriptors
        for item in instances:
            instanceDescriptor = item["object"]
            # filename could be None
            filename = instanceDescriptor.filename
            if filename is None:
                filename = fileNameForInstance(instanceDescriptor)
            instanceDescriptor.path = os.path.abspath(os.path.join(os.path.dirname(self.operator.path), filename))

        self.instances = instances
        self.w = vanilla.Sheet((350, 140), parentWindow=parentWindow)

        split = 100
        self.w.mathModelText = vanilla.TextBox((10, 10, split, 22), "Math model:", alignment="right")
        self.w.mathModel = vanilla.RadioGroup((split + 20, 10 - 2, 230, 22), ["Mutator Math", "VarLib"], isVertical=False)
        self.w.mathModel.set(0)

        self.w.roundCheckBox = vanilla.CheckBox((split + 20, 45, -10, 22), "Round Geometry")
        self.w.mathModelSuffix = vanilla.CheckBox((split + 20, 70, -10, 22), "Add Math Model Suffix")

        # self.w.instancesRootText = vanilla.TextBox((10, 105, split, 22), "Instances Folder:", alignment="right")
        # self.w.instancesRoot = vanilla.EditText((split + 20, 105 - 2, -10, 22), "foo")

        self.w.closeButton = vanilla.Button((-180, -30, -110, 20), "Cancel", callback=self.closeCallback)
        self.w.closeButton.bind(".", ["command"])
        self.w.closeButton.bind(chr(27), [])

        self.w.okButton = vanilla.Button((-100, -30, -10, 20), "Generate", callback=self.okCallback)
        self.w.open()

    def okCallback(self, sender):
        # generate
        mathModel = self.w.mathModel.get()
        shouldRound = self.w.roundCheckBox.get()
        addMathModelSuffix = self.w.mathModelSuffix.get()

        prereserveuseVarlib = self.operator.useVarlib
        prereserveRoundGeometry = self.operator.roundGeometry

        self.operator.useVarlib = mathModel == 1
        self.operator.roundGeometry = bool(shouldRound)
        self.operator.loadFonts()
        self.operator.findDefault()

        for item in self.instances:
            instanceDescriptor = item["object"]
            try:
                font = self.operator.makeInstance(instanceDescriptor)
                if not os.path.exists(os.path.dirname(instanceDescriptor.path)):
                    os.makedirs(os.path.dirname(instanceDescriptor.path))
                fontPath = instanceDescriptor.path
                if addMathModelSuffix:
                    fileName, ext = os.path.splitext(fontPath)
                    fontPath = f"{fileName}-{('mm', 'varLib')[mathModel]}{ext}"

                font.save(path=fontPath)
            except Exception as e:
                print(f"Failed to generate instance: {e}")

        self.operator.useVarlib = prereserveuseVarlib
        self.operator.roundGeometry = prereserveRoundGeometry

        self.w.close()

    def closeCallback(self, sender):
        self.w.close()


class AxisListItem(AppKit.NSObject, metaclass=ClassNameIncrementer):

    def __new__(cls, *args, **kwargs):
        self = cls.alloc().init()
        return self

    def __init__(self, axisDescriptor, controller):
        self.axisDescriptor = axisDescriptor
        self.controller = controller

    def __getitem__(self, key):
        if key == "object":
            return self.axisDescriptor
        return super().__getitem__(key)

    def dealloc(self):
        self.axisDescriptor = None
        self.controller = None
        super().dealloc()

    def axisRegisterd(self):
        for name, tag in registeredAxisTags:
            if name == self.axisName() and tag == self.axisTag():
                return checkSymbol
        return ""

    def axisName(self):
        return self.axisDescriptor.name

    def setAxisName_(self, value):
        # prevent setting name if the name already exists
        if self.controller.validateAxisName(value):
            self.axisDescriptor.name = str(value)
            self.controller.updateColumnHeadersFromAxes()
        else:
            print(f"Duplicate axis name: '{value}'")

    def axisTag(self):
        return self.axisDescriptor.tag

    def setAxisTag_(self, value):
        # prevent setting tag if the name already exists
        if self.controller.validateAxisTag(value):
            self.axisDescriptor.tag = str(value)
        else:
            print(f"Duplicate axis tag: '{value}'")

    def axisMinimum(self):
        if self.axisIsDescrete():
            return None
        return self.axisDescriptor.minimum

    # @tryExceptDecorator
    def setAxisMinimum_(self, value):
        if self.axisIsDescrete():
            # convert to a continuous axis
            self.axisDescriptor = self.controller.convertDiscreteAxisToContinuousAxis(self.axisDescriptor)
        if value is not None:
            self.axisDescriptor.minimum = float(value)

    def axisDefault(self):
        return self.axisDescriptor.default

    def setAxisDefault_(self, value):
        if value is not None:
            self.axisDescriptor.default = float(value)

    def axisMaximum(self):
        if self.axisIsDescrete():
            return None
        return self.axisDescriptor.maximum

    # @tryExceptDecorator
    def setAxisMaximum_(self, value):
        if self.axisIsDescrete():
            # convert to a continuous axis
            self.axisDescriptor = self.controller.convertDiscreteAxisToContinuousAxis(self.axisDescriptor)
        if value is not None:
            self.axisDescriptor.maximum = float(value)

    def axisIsDescrete(self):
        return hasattr(self.axisDescriptor, "values")

    def axisDiscreteValues(self):
        if self.axisIsDescrete():
            return " ".join([numberToString(value) for value in self.axisDescriptor.values])
        return ""

    # @tryExceptDecorator
    def setAxisDiscreteValues_(self, value):
        if not self.axisIsDescrete():
            # convert to a discrete axis
            self.axisDescriptor = self.controller.convertContinuousAxisToDiscreteAxis(self.axisDescriptor)
        self.axisDescriptor.values = [float(item) for item in value.split()]

    def axisHidden(self):
        return bool(self.axisDescriptor.hidden)

    def setAxisHidden_(self, value):
        self.axisDescriptor.hidden = bool(value)

    def axisHasMap(self):
        if self.axisDescriptor.map:
            return dotSymbol
        return ""

    def axisHasLabels(self):
        if self.axisDescriptor.labelNames or self.axisDescriptor.axisLabels:
            return dotSymbol
        return ""

    def genericInfoButton(self):
        return ""


class BaseAttributePopover:

    def __init__(self, listView, operator, closeCallback=None):
        tableView = listView.getNSTableView()
        index = listView.getSelection()[0]
        item = listView[index]
        relativeRect = tableView.rectOfRow_(index)
        self.operator = operator
        self.closeCallback = closeCallback
        self.popover = vanilla.Popover((500, 400))
        self.build(item)
        self.popover.bind("will close", self.popoverWillCloseCallback)
        self.popover.open(parentView=tableView, preferredEdge='bottom', relativeRect=relativeRect)

    def popoverWillCloseCallback(self, sender):
        if not self.controlEdited:
            return
        self.close()

        if self.closeCallback is not None:
            if isinstance(self.closeCallback, (list, tuple)):
                for callback in self.closeCallback:
                    callback()
            else:
                self.closeCallback()

    controlEdited = False

    def controlEditCallback(self, sender=None):
        self.controlEdited = True

    def build(self, item):
        pass

    def close(self):
        pass


class AxisAttributesPopover(BaseAttributePopover):

    def build(self, item):
        """
        support:
            * map
            * labels
        """
        self.axisDescriptor = item.axisDescriptor
        self.isDiscreteAxis = item.axisIsDescrete()

        self.popover.tabs = vanilla.Tabs((0, 15, -0, -0), ["Map", "Axis Labels"])

        self.axisMap = self.popover.tabs[0]
        self.axisLabels = self.popover.tabs[1]

        self.axisMap.editor = CodeEditor(
            (10, 10, -10, -10),
            mapParser.dumpMap(self.axisDescriptor.map),
            lexer=DesignspaceLexer(),
            showLineNumbers=False,
            callback=self.axisMapEditorCallback
        )
        # if self.isDiscreteAxis:
        #     self.axisMap.editor.setPosSize((10, 40, -10, -10))
        #     self.axisMap.editor.getNSTextView().setEditable_(False)
        #     self.axisMap.info = vanilla.TextBox((10, 10, -10, 22), "A discrete axis with a map does not make sense.")

        self.axisLabels.editor = CodeEditor(
            (10, 10, -10, -10),
            labelsParser.dumpAxisLabels(self.axisDescriptor.labelNames, self.axisDescriptor.axisLabels),
            lexer=DesignspaceLexer(),
            showLineNumbers=False,
            callback=self.axisLabelsEditorCallback
        )

    def axisMapEditorCallback(self, sender):
        self.controlEditCallback(sender)

    def axisLabelsEditorCallback(self, sender):
        self.controlEditCallback(sender)

    def close(self):
        if not self.isDiscreteAxis:
            self.axisDescriptor.map = mapParser.parseMap(self.axisMap.editor.get())
            SendNotification.single("AxisMap", designspace=self.operator)

        labelNames, axisLabels = labelsParser.parseAxisLabels(self.axisLabels.editor.get())
        self.axisDescriptor.labelNames = labelNames
        self.axisDescriptor.axisLabels = axisLabels
        SendNotification.single("AxisLabels", designspace=self.operator)


class SourceAttributesPopover(BaseAttributePopover):

    def build(self, item):
        """
        support:
            * localisedFamilyName
            * mutedGlyphNames
        """
        self.sourceDescriptor = item["object"]

        self.popover.tabs = vanilla.Tabs((0, 15, -0, -0), ["Localised Family Name", "Muted Glyphs"])

        self.sourceLocalisedFamilyName = self.popover.tabs[0]
        self.sourceMutedGlyphNames = self.popover.tabs[1]

        self.sourceLocalisedFamilyName.editor = CodeEditor(
            (10, 10, -10, -10),
            labelsParser.dumpAxisLabels(self.sourceDescriptor.localisedFamilyName, []),
            lexer=DesignspaceLexer(),
            showLineNumbers=False,
            callback=self.controlEditCallback
        )

        self.sourceMutedGlyphNames.editor = CodeEditor(
            (10, 10, -10, -10),
            glyphNameParser.dumpGlyphNames(self.sourceDescriptor.mutedGlyphNames),
            lexer=TextLexer(),
            showLineNumbers=False,
            callback=self.controlEditCallback
        )

    def close(self):
        labels, _ = labelsParser.parseAxisLabels(self.sourceLocalisedFamilyName.editor.get())
        self.sourceDescriptor.localisedFamilyName = labels
        self.sourceDescriptor.mutedGlyphNames = glyphNameParser.parseGlyphNames(self.sourceMutedGlyphNames.editor.get())


class InstancesAttributesPopover(BaseAttributePopover):

    def build(self, item):
        """
        support:
            * postScriptFontName
            * styleMapFamilyName
            * styleMapStyleName
            * localisedFamilyName
            * localisedStyleName
        """
        # Create the instancesDescriptor attribute
        self.instancesDescriptor = item["object"]

        # Create the popover tabs
        self.popover.tabs = vanilla.Tabs((0, 15, -0, -0), ["Additional Names", "Localised Family Name", "Localised Style Name"])

        # Assign the tabs to variables for easier access
        self.instanceStyleMapNames = self.popover.tabs[0]
        self.instanceLocalisedFamilyName = self.popover.tabs[1]
        self.instanceLocalisedStyleName = self.popover.tabs[2]

        # Create the container for the Style Map tab
        self.instanceStyleMapNames.container = vanilla.Box((10, 10, -10, -10))
        self.styleMapStyleOptions = ["regular", "italic", "bold", "bold italic"]

        col1 = 10
        col2 = 180
        padding = 24
        y = 10

        wand = symbolImage("wand.and.stars", "primary")

        # Create the text box and edit box for identifier Name
        # self.instanceStyleMapNames.container.identifierNameLabel = vanilla.TextBox((col1, y, col2-padding, 22), "Identifying Name:", alignment="right")
        # self.instanceStyleMapNames.container.identifierNameTextBox = vanilla.EditText((col2, y, -40, 22), "", callback=self.controlEditCallback)
        # self.instanceStyleMapNames.container.identifierNameAutoBtn = vanilla.ImageButton((-32, y, -10, 22), imageObject=wand, bordered=False, callback=self.autoIdentifyingNameCallback)
        # y += 42

        # Create the text box and edit box for PostScript Font Name
        self.instanceStyleMapNames.container.postScriptFontNameLabel = vanilla.TextBox((col1, y, col2-padding, 22), "PostScript Name:", alignment="right")
        self.instanceStyleMapNames.container.postScriptFontNameTextBox = vanilla.EditText((col2, y, -40, 22), "", callback=self.controlEditCallback)
        self.instanceStyleMapNames.container.postScriptFontNameAutoBtn = vanilla.ImageButton((-32, y, -10, 22), imageObject=wand, bordered=False, callback=self.autoPostScriptNameCallback)
        y += 42

        # Create the text box and edit box for Style Map Family Name
        self.instanceStyleMapNames.container.styleMapFamilyNameLabel = vanilla.TextBox((col1, y, col2-padding, 22), "Style Map Family Name:", alignment="right")
        self.instanceStyleMapNames.container.styleMapFamilyNameTextBox = vanilla.EditText((col2, y, -40, 22), "", callback=self.controlEditCallback)
        self.instanceStyleMapNames.container.styleMapFamilyNameAutoBtn = vanilla.ImageButton((-32, y, -10, 22), imageObject=wand, bordered=False, callback=self.autoStyleMapNamesCallback)
        y += 30

        # Create the text box and radio group for Style Map Style Name
        self.instanceStyleMapNames.container.styleMapStyleNameLabel = vanilla.TextBox((col1, y, col2-padding, 22), "Style Map Style Name:", alignment="right")
        self.instanceStyleMapNames.container.styleMapStyleNameRadio = vanilla.RadioGroup((col2, y, -10, 88), ["Regular", "Italic", "Bold", "Bold Italic"], callback=self.controlEditCallback)
        self.instanceStyleMapNames.container.styleMapStyleNameRadio.getNSMatrix().setAllowsEmptySelection_(True)

        # self.instanceStyleMapNames.container.helpButton = vanilla.HelpButton((-32, -32, -10, 22), callback=self.instancesHelpCallback)

        # Create the CodeEditor for Localised Family Name
        self.instanceLocalisedFamilyName.editor = CodeEditor(
            (10, 10, -10, -10),
            labelsParser.dumpAxisLabels(self.instancesDescriptor.localisedFamilyName, []),
            lexer=DesignspaceLexer(),
            showLineNumbers=False,
            callback=self.controlEditCallback
        )

        # Create the CodeEditor for Localised Style Name
        self.instanceLocalisedStyleName.editor = CodeEditor(
            (10, 10, -10, -10),
            labelsParser.dumpAxisLabels(self.instancesDescriptor.localisedStyleName, []),
            lexer=DesignspaceLexer(),
            showLineNumbers=False,
            callback=self.controlEditCallback
        )

        # Set the initial value for identifier name
        # self.instanceStyleMapNames.container.identifierNameTextBox.set(self.instancesDescriptor.name)

        # Set the initial value for PostScript Font Name
        self.instanceStyleMapNames.container.postScriptFontNameTextBox.set(self.instancesDescriptor.postScriptFontName)

        # Set the initial values for Style Map Family Name and Style Map Style Name
        self.instanceStyleMapNames.container.styleMapFamilyNameTextBox.set(self.instancesDescriptor.styleMapFamilyName)

        if self.instancesDescriptor.styleMapStyleName not in self.styleMapStyleOptions:
            self.instanceStyleMapNames.container.styleMapStyleNameRadio.set(-1)
        else:
            styleMapStyleNameIndex = self.styleMapStyleOptions.index(self.instancesDescriptor.styleMapStyleName)
            self.instanceStyleMapNames.container.styleMapStyleNameRadio.set(styleMapStyleNameIndex)

    def close(self):
        # Update the name attribute based on the identifierNameTextBox value
        # self.instancesDescriptor.name = self.instanceStyleMapNames.container.identifierNameTextBox.get() or None

        # Update the postScriptFontName attribute based on the postScriptFontNameTextBox value
        self.instancesDescriptor.postScriptFontName = self.instanceStyleMapNames.container.postScriptFontNameTextBox.get() or None

        # Update the styleMapFamilyName attribute based on the styleMapFamilyNameTextBox value, or if it's not set, set to None
        self.instancesDescriptor.styleMapFamilyName = self.instanceStyleMapNames.container.styleMapFamilyNameTextBox.get() or None

        # Update the styleMapStyleName attribute based on the styleMapStyleNameRadio value, or if it's not set, set to None
        styleMapStyleNameIndex = self.instanceStyleMapNames.container.styleMapStyleNameRadio.get()
        self.instancesDescriptor.styleMapStyleName = self.styleMapStyleOptions[styleMapStyleNameIndex] if styleMapStyleNameIndex > -1 else None

        # Parse the axis labels from the instanceLocalisedFamilyName editor and update the localisedFamilyName attribute
        familyNamelabels, _ = labelsParser.parseAxisLabels(self.instanceLocalisedFamilyName.editor.get())
        self.instancesDescriptor.localisedFamilyName = familyNamelabels

        # Parse the axis labels from the instanceLocalisedStyleName editor and update the localisedStyleName attribute
        styleNamelabels, _ = labelsParser.parseAxisLabels(self.instanceLocalisedStyleName.editor.get())
        self.instancesDescriptor.localisedStyleName = styleNamelabels

    # def instancesHelpCallback(self, sender):
    #     # TODO: Doesn't quite work 100% of the time? Crashes if you click it too much
    #     designspaceBundle.developerURL = "https://fonttools.readthedocs.io/en/latest/designspaceLib/xml.html#instance-element"
    #     designspaceBundle.developer = "Documentation"

    #     helpWindow = designspaceBundle.openHelp()
    #     helpWindow.visitButton.setTitle_(" Open on Browser ")
    #     helpWindow.visitButton.sizeToFit()

    #     visitButtonToolbarItem = helpWindow.w.getToolbarItems()["developerURL"]
    #     visitButtonToolbarItem.setMinSize_(helpWindow.visitButton.frame().size)
    #     visitButtonToolbarItem.setMaxSize_(helpWindow.visitButton.frame().size)

    # def autoIdentifyingNameCallback(self, sender):
    #     # Set the identifierNameTextBox value to the name attribute
    #     self.instancesDescriptor.name = identifyingNameTransformer(self.instancesDescriptor.familyName, self.instancesDescriptor.styleName)
    #     self.instanceStyleMapNames.container.identifierNameTextBox.set(self.instancesDescriptor.name)

    def autoPostScriptNameCallback(self, sender):
        # Set the postScriptFontNameTextBox value to the postScriptFontName attribute
        self.instancesDescriptor.postScriptFontName = postScriptNameTransformer(self.instancesDescriptor.familyName, self.instancesDescriptor.styleName)
        self.instanceStyleMapNames.container.postScriptFontNameTextBox.set(self.instancesDescriptor.postScriptFontName)

    def autoStyleMapNamesCallback(self, sender):
        # Set the styleMapFamilyNameTextBox value to the styleMapFamilyName attribute

        self.instancesDescriptor.styleMapFamilyName, self.instancesDescriptor.styleMapStyleName = styleMapNameTransformer(self.instancesDescriptor.familyName, self.instancesDescriptor.styleName)

        self.instanceStyleMapNames.container.styleMapFamilyNameTextBox.set(self.instancesDescriptor.styleMapFamilyName)
        styleMapStyleNameIndex = self.styleMapStyleOptions.index(self.instancesDescriptor.styleMapStyleName)
        self.instanceStyleMapNames.container.styleMapStyleNameRadio.set(styleMapStyleNameIndex)


class BaseButtonPopover:

    def __init__(self, vanillaObject, closeCallback=None, **kwargs):
        self.closeCallback = closeCallback
        self.popover = vanilla.Popover((400, 300))
        self.build(**kwargs)
        self.popover.bind("will close", self.popoverWillCloseCallback)
        self.popover.open(parentView=vanillaObject, preferredEdge='bottom')

    def popoverWillCloseCallback(self, sender):
        self.close()

        if self.closeCallback is not None:
            if isinstance(self.closeCallback, (list, tuple)):
                for callback in self.closeCallback:
                    callback()
            else:
                self.closeCallback()

    def build(self, **kwargs):
        pass

    def close(self):
        pass


class BaseNotificationObserver:

    notifications = []

    def observeNotifications(self):
        for notification, method in self.notifications:
            addObserver(self, notification, method)

    def removeObserverNotifications(self):
        for notification, method in self.notifications:
            removeObserver(self, notification)


class LocationLabelsPreview(Subscriber, WindowController):

    def build(self, operator):
        self.operator = operator

        self.w = vanilla.FloatingWindow((250, 300), "Labels Preview")
        self.w.languages = vanilla.PopUpButton((10, 10, 80, 22), [], self.controlEdited)
        self.w.previewText = vanilla.TextBox((100, 10, -10, 22))
        self.buildLocationLabels()

    def started(self):
        self.w.open()

    def destroy(self):
        self.operator = None

    def update(self):
        self.controlEdited(setLanguages=self.w.languages.getItem())

    def buildLocationLabels(self):
        location = dict()
        if hasattr(self.w, "controls"):
            location = self.getControlLocation()
            del self.w.controls
        self.w.controls = vanilla.Group((0, 40, 0, 0))

        y = 10
        for axis in self.operator.axes:
            setattr(
                self.w.controls,
                f"{axis.name}_name",
                vanilla.TextBox((10, y, 80, 22), f"{axis.name}:", sizeStyle="small", alignment="right")
            )
            if hasattr(axis, "values"):
                control = vanilla.PopUpButton(
                    (100, y, 100, 16),
                    [str(value) for value in axis.values],
                    sizeStyle="small",
                    callback=self.controlEdited
                )
                control.set(location.get(axis.name, axis.values.index(axis.default)))
            else:
                control = SliderEditStepper(
                    (100, y, -10, 20),
                    minValue=axis.minimum,
                    maxValue=axis.maximum,
                    value=location.get(axis.name, axis.default),
                    sizeStyle="small",
                    callback=self.controlEdited
                )
            setattr(self.w.controls, f"{axis.name}_control", control)
            y += 30
        self.w.resize(400, y + 40)
        self.controlEdited(setLanguages="en")

    def getControlLocation(self):
        location = dict()
        for axis in self.operator.axes:
            if hasattr(self.w.controls, f"{axis.name}_control"):
                control = getattr(self.w.controls, f"{axis.name}_control")
                if hasattr(axis, "values"):
                    value = axis.values[control.get()]
                else:
                    value = control.get()
                location[axis.name] = value
        return location

    def controlEdited(self, sender=None, setLanguages=None):
        self.names = designspaceLib.statNames.getStatNames(self.operator.doc, self.getControlLocation())
        if setLanguages:
            languages = list(sorted(set(list(self.names.familyNames.keys()) + list(self.names.styleNames.keys()))))
            self.w.languages.setItems(languages)
            if setLanguages in languages:
                self.w.languages.set(languages.index(setLanguages))

        language = self.w.languages.getItem()
        self.w.previewText.set(f"{self.names.familyNames.get(language, '-')} {self.names.styleNames.get(language, '-')}")

    # notifications

    def designspaceEditorDidChange(self, info):
        self.buildLocationLabels()

    def designspaceEditorLabelsDidChange(self, info):
        self.update()

    def designspaceEditorAxisLabelsDidChange(self, info):
        self.update()


class DesignspaceEditorController(Subscriber, WindowController, BaseNotificationObserver):

    notifications = [
        ("fontDidOpen", "roboFontFontDidOpen"),
        ("fontWillClose", "roboFontFontWillClose"),
    ]

    def __init__(self, path=None):
        if path is not None:
            # search for already open designspace files
            for controller in AllDesignspaceWindows():
                if controller.operator.path == path:
                    controller.w.show()
                    return

        self.holdChanges = HoldChanges()
        with self.holdChanges:
            super().__init__()
            self.load(path)

    def build(self):
        self.operator = DesignspaceEditorOperator(extrapolate=True)

        self.w = vanilla.Window((900, 500), "Designspace Editor", minSize=(720, 400))
        self.w.vanillaWrapper = weakref.ref(self)
        self.w.bind("should close", self.windowShouldClose)

        self.tabItems = ["Axes", "Sources", "Instances", "Rules", "Location Labels", "Variable Fonts", "Problems", "Notes"]
        self.w.tabs = vanilla.Tabs((0, 0, 0, 0), self.tabItems, showTabs=False)

        self.axes = self.w.tabs[0]
        self.sources = self.w.tabs[1]
        self.instances = self.w.tabs[2]
        self.rules = self.w.tabs[3]
        self.locationLabels = self.w.tabs[4]
        self.variableFonts = self.w.tabs[5]
        self.problems = self.w.tabs[6]
        self.notes = self.w.tabs[7]

        toolbarItems = [dict(
            itemIdentifier=tabItem.lower(),
            label=tabItem,
            callback=self.toolbarSelectTab,
            imageObject=designspaceBundle.getResourceImage(f"toolbar_30_30_icon_{tabItem.lower().replace(' ', '_')}"),
            selectable=True,
            visibleByDefault=tabItem not in ["Notes"],
        ) for tabItem in self.tabItems]

        other_extensions = []
        if self.hasPreplatorSupport:
            other_extensions.append(
                dict(
                    itemIdentifier="prepolator",
                    label="Prepolator",
                    callback=self.toolbarPrepolator,
                    imageObject=symbolImage("atom", (1, 0, 1, 1))
                    )
                )
        if self.hasBatchSupport:
            other_extensions.append(
                dict(
                    itemIdentifier="batch",
                    label="Batch",
                    callback=self.toolbarBatch,
                    imageObject=symbolImage("arrow.right.filled.filter.arrow.right", (1, 0, 1, 1))
                    )
                )
        if other_extensions:
            toolbarItems.append(dict(itemIdentifier=AppKit.NSToolbarSpaceItemIdentifier))

        toolbarItems.extend(other_extensions)

        toolbarItems.extend([
            dict(itemIdentifier=AppKit.NSToolbarSpaceItemIdentifier,
            ),
            dict(
                itemIdentifier="preview",
                label="Preview",
                callback=self.toolbarPreview,
                imageObject=symbolImage("chart.bar.doc.horizontal", (1, 0, 1, 1))  # doc.plaintext
            ),
            dict(
                itemIdentifier="save",
                label="Save",
                callback=self.toolbarSave,
                imageObject=symbolImage("square.and.arrow.down", (1, 0, 1, 1))
            ),
            # dict(itemIdentifier=AppKit.NSToolbarSpaceItemIdentifier),
            dict(
                itemIdentifier="help",
                label="Help",
                callback=self.toolbarHelp,
                imageObject=symbolImage("questionmark.circle", (1, 0, 1, 1))

            ),
            # dict(
            #     itemIdentifier="generate",
            #     label="Generate",
            #     callback=self.toolbarGenerate,
            #     imagePath=None,
            # ),
            # dict(
            #     itemIdentifier="settings",
            #     label="Settings",
            #     callback=self.toolbarSettings,
            #     imageObject=designspaceBundle.getResourceImage("toolbar_30_30_icon_settings"),
            # ),
        ])
        self.w.addToolbar("DesignSpaceToolbar", toolbarItems, addStandardItems=False)

        items = self.w.getToolbarItems()
        if "batch" in items:
            items["batch"].setVisibilityPriority_(AppKit.NSToolbarItemVisibilityPriorityLow)
        if "prepolator" in items:
            items["prepolator"].setVisibilityPriority_(AppKit.NSToolbarItemVisibilityPriorityLow)


        # AXES
        axesToolsSsegmentDescriptions = [
            dict(title="+", width=20),
            dict(title="-", width=20),
        ]
        self.axes.tools = vanilla.SegmentedButton(
            (10, 5, 400, 22),
            selectionStyle="momentary",
            callback=self.axisToolsCallback,
            segmentDescriptions=axesToolsSsegmentDescriptions
        )
        self.axes.editorTools = vanilla.SegmentedButton(
            (72, 5, 370, 22),
            selectionStyle="momentary",
            callback=self.axisEditorToolsCallback,
            segmentDescriptions=[dict(title=f"Add {preferredAxis[-1]['en']} Axis") for preferredAxis in preferredAxes]
        )

        axisDoubleClickCell = RFDoubleClickCell.alloc().init()
        axisDoubleClickCell.setDoubleClickCallback_(self.axisListDoubleClickCallback)
        axisDoubleClickCell.setImage_(infoImage)

        axesColumnDescriptions = [
            dict(title="", key="genericInfoButton", width=20, editable=False, cell=axisDoubleClickCell),
            dict(title="Ⓡ", key="axisRegisterd", width=20, allowsSorting=False, editable=False),
            dict(title="Name", key="axisName", allowsSorting=False, editable=True),
            dict(title="Tag", key="axisTag", width=70, allowsSorting=False, editable=True),
            dict(title="Minimum", key="axisMinimum", width=70, allowsSorting=False, editable=True, formatter=numberFormatter),
            dict(title="Default", key="axisDefault", width=70, allowsSorting=False, editable=True, formatter=numberFormatter),
            dict(title="Maximum", key="axisMaximum", width=70, allowsSorting=False, editable=True, formatter=numberFormatter),
            dict(title="Discrete Values", key="axisDiscreteValues", width=100, allowsSorting=False, editable=True),

            dict(title="Hidden", key="axisHidden", width=50, cell=vanilla.CheckBoxListCell(), allowsSorting=False, editable=True),
            dict(title="📈", key="axisHasMap", width=20, allowsSorting=False, editable=False),
            dict(title="🏷️", key="axisHasLabels", width=20, allowsSorting=False, editable=False),
        ]

        self.axes.list = vanilla.List(
            (0, 30, 0, 0),
            [],
            editCallback=self.axesListEditCallback,
            columnDescriptions=axesColumnDescriptions,
            selectionCallback=self.axesListSelectionCallback,
            allowsSorting=False,
            dragSettings=dict(type="sourcesListDragAndDropType", callback=self.dragCallback),
            selfDropSettings=dict(type="sourcesListDragAndDropType", operation=AppKit.NSDragOperationMove, callback=self.dropCallback),
        )
        self.axes.list.designspaceContent = "axes"
        addToolTipForColumn(self.axes.list, "genericInfoButton", "Double click to pop over an axis map and label editor")
        addToolTipForColumn(self.axes.list, "axisRegisterd", "Axis tag and name is registered")
        addToolTipForColumn(self.axes.list, "axisHasMap", "Axis has a map")
        addToolTipForColumn(self.axes.list, "axisHasLabels", "Axis has labels")

        # SOURCES
        sourcesToolsSsegmentDescriptions = [
            dict(title="+", width=20),
            dict(title="-", width=20),
        ]
        self.sources.tools = vanilla.SegmentedButton(
            (10, 5, 400, 22),
            selectionStyle="momentary",
            callback=self.sourcesToolsCallback,
            segmentDescriptions=sourcesToolsSsegmentDescriptions
        )

        sourcesEditorToolsSsegmentDescriptions = [
            dict(title="Add Open UFOs to Designspace"),
            # dict(title="Load Names"),
            dict(title="Replace UFO"),
        ]
        self.sources.editorTools = vanilla.SegmentedButton(
            (72, 5, 300, 22),
            selectionStyle="momentary",
            callback=self.sourcesEditorToolsCallback,
            segmentDescriptions=sourcesEditorToolsSsegmentDescriptions
        )

        sourcesDoubleClickCell = RFDoubleClickCell.alloc().init()
        sourcesDoubleClickCell.setDoubleClickCallback_(self.sourcesListDoubleClickCallback)
        sourcesDoubleClickCell.setImage_(infoImage)

        sourcesColumnDescriptions = [
            dict(title="", key="genericInfoButton", width=20, editable=False, cell=sourcesDoubleClickCell),
            dict(title="💾", key="sourceHasPath", width=20, editable=False),
            dict(title="📍", key="sourceIsDefault", width=20, editable=False),
            dict(title="UFO", key="sourceUFOFileName", width=200, minWidth=100, maxWidth=350, editable=False, formatter=PathFormatter.alloc().init()),
            dict(title="Family Name", key="sourceFamilyName", editable=True, width=130, minWidth=130, maxWidth=250),
            dict(title="Style Name", key="sourceStyleName", editable=True, width=130, minWidth=130, maxWidth=250),
            dict(title="Layer Name", key="sourceLayerName", editable=True, width=130, minWidth=130, maxWidth=250),
            dict(title="🌐", key="sourceHasLocalisedFamilyNames", width=20, allowsSorting=False, editable=False),
            dict(title="🔕", key="sourceHasMutedGlyphs", width=20, allowsSorting=False, editable=False),
        ]

        self.sources.list = vanilla.List(
            (0, 30, 0, 0),
            [],
            columnDescriptions=sourcesColumnDescriptions,
            editCallback=self.sourcesListEditCallback,
            menuCallback=self.listMenuCallack,
            selectionCallback=self.sourceListSelectionCallback,
            allowsSorting=False,
            dragSettings=dict(type="sourcesListDragAndDropType", callback=self.dragCallback),
            selfDropSettings=dict(type="sourcesListDragAndDropType", operation=AppKit.NSDragOperationMove, callback=self.dropCallback),
            otherApplicationDropSettings=dict(type=AppKit.NSFilenamesPboardType, operation=AppKit.NSDragOperationCopy, callback=self.sourcesListDropCallback),
        )
        self.sources.list.designspaceContent = "sources"
        addToolTipForColumn(self.sources.list, "genericInfoButton", "Double click to pop over an axis map and label editor")
        addToolTipForColumn(self.sources.list, "sourceHasPath", "Source is saved")
        addToolTipForColumn(self.sources.list, "sourceIsDefault", "Source is the default")
        addToolTipForColumn(self.sources.list, "sourceHasLocalisedFamilyNames", "Source has localised family names")
        addToolTipForColumn(self.sources.list, "sourceHasMutedGlyphs", "Source has muted glyphs")

        # INSTANCES
        instancesToolsSsegmentDescriptions = [
            dict(title="+", width=20),
            dict(title="-", width=20),
        ]
        self.instances.tools = vanilla.SegmentedButton(
            (10, 5, 400, 22),
            selectionStyle="momentary",
            callback=self.instancesToolsCallback,
            segmentDescriptions=instancesToolsSsegmentDescriptions
        )

        instancesEditorToolsSsegmentDescriptions = [
            dict(title="Duplicate"),
            dict(title="Add Sources as Instances")
        ]
        self.instances.editorTools = vanilla.SegmentedButton(
            (72, 5, 250, 22),
            selectionStyle="momentary",
            callback=self.instancesEditorToolsCallback,
            segmentDescriptions=instancesEditorToolsSsegmentDescriptions
        )
        instancesEditorGenerateToolsSsegmentDescriptions = [
            dict(title="Generate Instance"),
        ]
        self.instances.generateTools = vanilla.SegmentedButton(
            (330, 5, 150, 22),
            selectionStyle="momentary",
            callback=self.instancesEditorGenerateToolsCallback,
            segmentDescriptions=instancesEditorGenerateToolsSsegmentDescriptions
        )

        instancesDoubleClickCell = RFDoubleClickCell.alloc().init()
        instancesDoubleClickCell.setDoubleClickCallback_(self.instancesListDoubleClickCallback)
        instancesDoubleClickCell.setImage_(infoImage)

        instancesColumnDescriptions = [
            dict(title="", key="genericInfoButton", width=20, editable=False, cell=instancesDoubleClickCell),
            dict(title="UFO", key="instanceUFOFileName", width=200, minWidth=100, maxWidth=350, editable=False, formatter=PathFormatter.alloc().init()),
            dict(title="Family Name", key="instanceFamilyName", editable=True, width=130, minWidth=130, maxWidth=250),
            dict(title="Style Name", key="instanceStyleName", editable=True, width=130, minWidth=130, maxWidth=250),
            # dict(title="PostScript Name", key="instancePostscriptFontName", editable=True, width=130, minWidth=130, maxWidth=250),
            dict(title="🏷️", key="instanceHasAdditionalNames", width=20, allowsSorting=False, editable=False),
            dict(title="🌐", key="instanceHasLocalisedFamilyNames", width=20, allowsSorting=False, editable=False),
            dict(title="📍", key="instanceLocation", editable=False, width=20)
        ]

        self.instances.list = vanilla.List(
            (0, 30, 0, 0),
            [],
            editCallback=self.instancesListEditCallback,
            columnDescriptions=instancesColumnDescriptions,
            menuCallback=self.listMenuCallack,
            selectionCallback=self.instancesListSelectionCallback,
            allowsSorting=False,
            dragSettings=dict(type="sourcesListDragAndDropType", callback=self.dragCallback),
            selfDropSettings=dict(type="sourcesListDragAndDropType", operation=AppKit.NSDragOperationMove, callback=self.dropCallback),
        )
        addToolTipForColumn(self.sources.list, "genericInfoButton", "Double click to edit additional instance info")
        addToolTipForColumn(self.instances.list, "instanceHasAdditionalNames", "Instance has additional names")
        addToolTipForColumn(self.instances.list, "instanceHasLocalisedFamilyNames", "Instance has localised family and/or style names")
        addToolTipForColumn(self.instances.list, "instanceLocation", "Indicate if the location of the instance is a user location or a design location.")

        self.instances.list.designspaceContent = "instances"

        # RULES
        self.rules.editor = CodeEditor((0, 0, 0, 0), lexer=DesignspaceLexer(), showLineNumbers=False, callback=self.rulesEditorCallback)

        # LABELS
        self.locationLabels.tools = vanilla.SegmentedButton(
            (10, 5, 125, 22),
            selectionStyle="momentary",
            callback=self.locationLabelsToolsCallback,
            segmentDescriptions=[dict(title="Labels Preview")]
        )
        self.locationLabels.editor = CodeEditor((0, 30, 0, 0), lexer=DesignspaceLexer(), showLineNumbers=False, callback=self.locationLabelsEditorCallback)

        # VARIABLE FONTS
        variableFontsEditorToolsSsegmentDescriptions = [
            dict(title="Add All Possible Variable Fonts"),
        ]
        self.variableFonts.editorTools = vanilla.SegmentedButton(
            (10, 5, 200, 22),
            selectionStyle="momentary",
            callback=self.variableFontsEditorToolsCallback,
            segmentDescriptions=variableFontsEditorToolsSsegmentDescriptions
        )
        self.variableFonts.editor = CodeEditor((0, 30, 0, 0), lexer=DesignspaceLexer(), showLineNumbers=False, callback=self.variableFontsEditorCallback)

        # PROBLEMS
        self.problems.tools = vanilla.SegmentedButton(
            (10, 5, 130, 22),
            selectionStyle="momentary",
            callback=self.problemsToolsCallback,
            segmentDescriptions=[dict(title="Check for problems")]
        )

        problemsColumnDescriptions = [
            dict(title="", key="problemIcon", width=20),
            dict(title="Where", key="problemClass", width=130),
            dict(title="What", key="problemDescription", minWidth=200, width=200, maxWidth=1000),
            dict(title="Specifically", key="problemData", minWidth=200, width=200, maxWidth=1000),
        ]
        self.problems.list = vanilla.List((0, 30, 0, 0), [], columnDescriptions=problemsColumnDescriptions)

        # NOTES
        self.notes.editor = vanilla.TextEditor((0, 0, 0, 0), callback=self.notesEditorCallback)

        self.w.getNSWindow().toolbar().setSelectedItemIdentifier_("axes")

        self.observeNotifications()

    def started(self):
        with SendNotification(action="OpenDesignspace", designspace=self.operator):
            self.w.open()
        registerOperator(self.operator)

    def destroy(self):
        for controller in [self.locationLabelsPreview, self.locationPreview]:
            try:
                controller.w.close()
            except Exception:
                pass
        SendNotification.single(action="CloseDesignspace", designspace=self.operator)
        unregisterOperator(self.operator)
        self.operator = None
        self.removeObserverNotifications()

    def load(self, path):
        if path is not None:
            fileName = os.path.basename(path)
            try:
                self.operator.read(path)
                self.operator.loadFonts()
            except Exception as e:
                self.showMessage(
                    "DesignSpaceEdit can't open this file",
                    informativeText=f"Error reading {fileName}.\n{e}."
                )
            self.loadObjects()
            self.setWindowTitleFromPath(path)

    def loadOperator(self, operator):
        self.operator = operator
        self.operator.loadFonts()
        self.loadObjects()
        self.setWindowTitleFromPath(operator.path)

    def loadObjects(self):
        with self.holdChanges:
            self.axes.list.set([AxisListItem(axisDescriptor, self) for axisDescriptor in self.operator.axes])
            self.sources.list.set([self.wrapSourceDescriptor(sourceDescriptor) for sourceDescriptor in self.operator.sources])
            self.instances.list.set([self.wrapInstanceDescriptor(instanceDescriptor) for instanceDescriptor in self.operator.instances])
            self.rules.editor.set(rulesParser.extractRules(self.operator))
            self.locationLabels.editor.set(labelsParser.extractLocationLabels(self.operator))
            self.variableFonts.editor.set(variableFontsParser.extractVariableFonts(self.operator))
            self.notes.editor.set(self.operator.lib.get(designspacenotesLibKey, ""))
            self.updateColumnHeadersFromAxes()

    @property
    def hasPreplatorSupport(self):    
        try:
            import prepolator
            return True
        except ImportError:
            return False

    @property
    def hasBatchSupport(self):
        try:
            import batch
            return True
        except ImportError:
            return False

    # AXES

    def axisToolsCallback(self, sender):
        value = sender.get()
        if value == 1:
            # remove
            for index in reversed(self.axes.list.getSelection()):
                item = self.axes.list[index]
                self.operator.removeAxis(item.axisDescriptor)
        else:
            # add
            name = f"newAxis{len(self.operator.axes) + 1}"
            tag = f"nwx{len(self.operator.axes) + 1}"
            minimum = 0
            maximum = 1000
            default = 0
            self._addAxis(name, tag, minimum, maximum, default)

        self.setDocumentNeedSave(True, who="Axes")
        self.updateColumnHeadersFromAxes()

    def axisEditorToolsCallback(self, sender):
        index = sender.get()
        name, tag, minimum, maximum, default, labelNames = preferredAxes[index]
        self._addAxis(name, tag, minimum, maximum, default, labelNames)

        self.setDocumentNeedSave(True, who="Axes")
        self.updateColumnHeadersFromAxes()

    def _addAxis(self, name, tag, minimum, maximum, default, labelNames=None):
        if self.validateAxisName(name) and self.validateAxisTag(tag):
            self.operator.addAxisDescriptor(
                name=name,
                tag=tag,
                minimum=minimum,
                maximum=maximum,
                default=default,
                labelNames=labelNames
            )
        else:
            print(f"Duplicate axis: '{name}'")

    def axisListDoubleClickCallback(self, sender):
        self.axisPopover = AxisAttributesPopover(self.axes.list, self.operator, closeCallback=self.axesChangedCallback)

    def axesListEditCallback(self, sender):
        self.axesChangedCallback(shouldReload=False)

    def axesChangedCallback(self, shouldReload=True):
        if shouldReload:
            self.axes.list.getNSTableView().reloadData()
        self.setDocumentNeedSave(True, who="Axes")

    def axesListSelectionCallback(self, sender):
        selectedItems = [sender[index]["object"] for index in sender.getSelection()]
        SendNotification.single("Axes", action="ChangeSelection", selectedItems=selectedItems, designspace=self.operator)

    # SOURCES

    def sourcesToolsCallback(self, sender):

        def addSourceCallback(paths):
            for path in paths:
                self.addSourceFromPath(path)

        # with self.holdChanges:
        value = sender.get()
        if value == 0:
            # add
            self.showGetFile(
                messageText="Add new UFO",
                allowsMultipleSelection=True,
                fileTypes=["ufo"],
                callback=addSourceCallback
            )

        elif value == 1:
            # remove
            for index in reversed(self.sources.list.getSelection()):
                item = self.sources.list[index]
                self.operator.removeSource(item["object"])

        self.setDocumentNeedSave(True, who="Sources")

    def sourcesEditorToolsCallback(self, sender):
        value = sender.get()
        if value == 0:
            # Add Open UFOs
            existingSourcePaths = [sourceDescriptor.path for sourceDescriptor in self.operator.sources]
            for font in AllFonts():
                if font.path not in existingSourcePaths:
                    self.addSourceFromFont(font)
        elif value == 1:
            # Replace UFO
            selection = self.sources.list.getSelection()
            if len(selection) == 1:
                index = selection[0]
                item = self.sources.list[index]
                sourceDescriptor = item["object"]

                def callback(paths):
                    if paths:
                        font = OpenFont(paths[0], showInterface=False)
                        sourceDescriptor.path = font.path
                        sourceDescriptor.familyName = font.info.familyName
                        sourceDescriptor.styleName = font.info.styleName
                        if self.operator.path is not None:
                            sourceDescriptor.filename = os.path.relpath(font.path, os.path.dirname(self.operator.path))
                        else:
                            sourceDescriptor.filename = font.path
                        self.operator.fonts[sourceDescriptor.name] = font.asDefcon()
                        item.update(self.wrapSourceDescriptor(sourceDescriptor))
                        self.setDocumentNeedSave(True, who="Sources")

                self.showGetFile(
                    messageText=f"New UFO for {os.path.basename(sourceDescriptor.path)}",
                    allowsMultipleSelection=False,
                    fileTypes=["ufo"],
                    callback=callback
                )
            else:
                self.showMessage(
                    messageText="Cannot replace source UFOs",
                    informativeText="Selection only one source item to be replace"
                )

    def addSourceFromPath(self, path):
        font = OpenFont(path, showInterface=False)
        self.addSourceFromFont(font)

    def addSourceFromFont(self, font):
        defaultLocation = self.operator.newDefaultLocation(bend=True)
        if self.operator.path is not None:
            filename = os.path.relpath(font.path, os.path.dirname(self.operator.path))
        else:
            filename = font.path

        sourceDescriptor = self.operator.addSourceDescriptor(
            path=font.path,
            filename=filename,
            name=self.operator.sourceNameGenerator(),
            familyName=font.info.familyName,
            styleName=font.info.styleName,
            location=defaultLocation
        )
        self.operator.fonts[sourceDescriptor.name] = font.asDefcon()
        self.setDocumentNeedSave(True)

    def wrapSourceDescriptor(self, sourceDescriptor):
        allDefaults = self.operator.findAllDefaults()
        wrapped = dict(
            sourceHasPath=checkSymbol if sourceDescriptor.path and os.path.exists(sourceDescriptor.path) else "",
            sourceIsDefault=defaultSymbol if sourceDescriptor in allDefaults else "",
            sourceUFOFileName=sourceDescriptor.filename if sourceDescriptor.filename is not None and sourceDescriptor.filename != sourceDescriptor.path else "[pending save]",
            sourceFamilyName=sourceDescriptor.familyName or "",
            sourceStyleName=sourceDescriptor.styleName or "",
            sourceLayerName=sourceDescriptor.layerName if sourceDescriptor.layerName else "",
            sourceHasLocalisedFamilyNames=dotSymbol if sourceDescriptor.localisedFamilyName else "",
            sourceHasMutedGlyphs=dotSymbol if sourceDescriptor.mutedGlyphNames else "",
            object=sourceDescriptor
        )
        for axis, value in sourceDescriptor.location.items():
            wrapped[f"axis_{axis}"] = value
        return wrapped

    def unwrapSourceDescriptor(self, wrappedSourceDescriptor):
        sourceDescriptor = wrappedSourceDescriptor["object"]
        sourceDescriptor.familyName = wrappedSourceDescriptor["sourceFamilyName"] if wrappedSourceDescriptor.get("sourceFamilyName") else None
        sourceDescriptor.styleName = wrappedSourceDescriptor["sourceStyleName"] if wrappedSourceDescriptor.get("sourceStyleName") else None
        sourceDescriptor.layerName = wrappedSourceDescriptor["sourceLayerName"] if wrappedSourceDescriptor.get("sourceLayerName") else None
        # update locations
        for axis in self.operator.axes:
            sourceDescriptor.location[axis.name] = wrappedSourceDescriptor.get(f"axis_{axis.name}", axis.default)
        # remove non existing location axis names
        existingAxisNames = [axis.name for axis in self.operator.axes]
        for locationName in list(sourceDescriptor.location):
            if locationName not in existingAxisNames:
                del sourceDescriptor.location[locationName]

        return sourceDescriptor

    def sourcesListDoubleClickCallback(self, sender):
        self.sourcePopover = SourceAttributesPopover(self.sources.list, self.operator, closeCallback=self.sourcesChangedCallback)

    def sourcesChangedCallback(self):
        self.updateSources()
        self.setDocumentNeedSave(True, who="Sources")

    def sourcesListEditCallback(self, sender):
        self.sourcesChangedCallback()

    def sourceListSelectionCallback(self, sender):
        selectedItems = [sender[index]["object"] for index in sender.getSelection()]
        SendNotification.single("Sources", action="ChangeSelection", selectedItems=selectedItems, designspace=self.operator)

    def sourcesListDropCallback(self, sender, dropInfo):
        isProposal = dropInfo["isProposal"]
        existingUFOPaths = [sourceDescriptor.path for sourceDescriptor in self.operator.sources]

        paths = dropInfo["data"]
        paths = [path for path in paths if os.path.splitext(path)[-1].lower() == ".ufo" and path not in existingUFOPaths]

        if not paths:
            return False

        if not isProposal:
            for path in paths:
                self.addSourceFromPath(path)

        return True

    @holdRecursionDecorator
    def updateSources(self):
        with self.holdChanges:
            for item in self.sources.list:
                sourceDescriptor = self.unwrapSourceDescriptor(item)
                item.update(self.wrapSourceDescriptor(sourceDescriptor))

    # INSTANCES

    def instancesToolsCallback(self, sender):
        with self.holdChanges:
            value = sender.get()
            if value == 0:
                # add
                self.operator.addInstanceDescriptor(
                    designLocation=self.operator.newDefaultLocation()
                )
            elif value == 1:
                # remove
                for index in reversed(self.instances.list.getSelection()):
                    item = self.instances.list[index]
                    self.operator.removeInstance(item["object"])
        self.instancesChanged()

    def wrapInstanceDescriptor(self, instanceDescriptor):
        filename = postScriptNameTransformer(instanceDescriptor.familyName, instanceDescriptor.styleName)
        wrapped = dict(
            instanceUFOFileName=instanceDescriptor.filename if instanceDescriptor.filename is not None else os.path.join(getExtensionDefault('instanceFolderName', 'instances'), f"{filename}.ufo"),
            instanceFamilyName=instanceDescriptor.familyName or "",
            instanceStyleName=instanceDescriptor.styleName or "",
            # instancePostscriptFontName=instanceDescriptor.postScriptFontName or "",
            instanceHasAdditionalNames=dotSymbol if any((instanceDescriptor.postScriptFontName, instanceDescriptor.styleMapFamilyName, instanceDescriptor.styleMapStyleName)) else "",
            instanceHasLocalisedFamilyNames=dotSymbol if any((instanceDescriptor.localisedFamilyName, instanceDescriptor.localisedStyleName)) else "",

            instanceLocation="✏️" if instanceDescriptor.designLocation else "👤",
            object=instanceDescriptor
        )
        location = instanceDescriptor.designLocation or instanceDescriptor.userLocation
        for axis, value in location.items():
            wrapped[f"axis_{axis}"] = value
        return wrapped

    def unwrapInstanceDescriptor(self, wrappedInstanceDescriptor):
        instanceDescriptor = wrappedInstanceDescriptor["object"]
        instanceDescriptor.familyName = wrappedInstanceDescriptor["instanceFamilyName"] if wrappedInstanceDescriptor.get("instanceFamilyName") else None
        instanceDescriptor.styleName = wrappedInstanceDescriptor["instanceStyleName"] if wrappedInstanceDescriptor.get("instanceStyleName") else None
        # instanceDescriptor.postScriptFontName = wrappedInstanceDescriptor["instancePostscriptFontName"] if wrappedInstanceDescriptor.get("instancePostscriptFontName") else None
        # update locations
        location = instanceDescriptor.designLocation or instanceDescriptor.userLocation
        for axis in self.operator.axes:
            location[axis.name] = wrappedInstanceDescriptor.get(f"axis_{axis.name}", axis.default)
        # remove non existing location axis names
        existingAxisNames = [axis.name for axis in self.operator.axes]
        for locationName in list(location):
            if locationName not in existingAxisNames:
                del location[locationName]
        return instanceDescriptor

    def instancesListDoubleClickCallback(self, sender):
        self.instancesPopover = InstancesAttributesPopover(self.instances.list, self.operator, closeCallback=self.instancesChanged)

    def instancesEditorToolsCallback(self, sender):
        value = sender.get()
        if value == 0:
            # duplicate
            for index in self.instances.list.getSelection():
                item = self.instances.list[index]
                instanceDescriptor = item["object"]
                self.operator.addInstanceDescriptor(
                    **deepcopy(instanceDescriptor.asdict())
                )

        elif value == 1:
            # Add Sources as Instances
            existingLocations = [instanceDescriptor.getFullDesignLocation(self.operator) for instanceDescriptor in self.operator.instances]
            for sourceDescriptor in self.operator.sources:
                if sourceDescriptor.location not in existingLocations:
                    fileName = postScriptNameTransformer(sourceDescriptor.familyName, sourceDescriptor.styleName)
                    self.operator.addInstanceDescriptor(
                        familyName=sourceDescriptor.familyName,
                        styleName=sourceDescriptor.styleName,
                        designLocation=sourceDescriptor.location,
                        filename=os.path.join(getExtensionDefault('instanceFolderName', 'instances'), f"{fileName}.ufo")
                    )

    def instancesEditorGenerateToolsCallback(self, sender):
        if self.operator.path is None:
            self.showMessage("Save the designspace first.", "Instances are generated in a relative path next to the designspace file.")
            return

        selection = self.instances.list.getSelection()
        if selection:
            instances = [self.instances.list[index] for index in selection]
        else:
            instances = self.instances.list
        GenerateInstanceSheet(self.w, self.operator, instances)

    def instancesListEditCallback(self, sender):
        if self.holdChanges:
            return
        for wrappedInstanceDescriptor in sender:
            self.unwrapInstanceDescriptor(wrappedInstanceDescriptor)
        self.operator.instances[:] = [item["object"] for item in sender]
        self.instancesChanged()

    def instancesListSelectionCallback(self, sender):
        selectedItems = [sender[index]["object"] for index in sender.getSelection()]
        SendNotification.single("Instances", action="ChangeSelection", selectedItems=selectedItems, designspace=self.operator)

    def instancesChanged(self):
        self.setDocumentNeedSave(True, who="Instances")

    @holdRecursionDecorator
    def updateInstances(self):
        with self.holdChanges:
            for item in self.instances.list:
                instanceDescriptor = self.unwrapInstanceDescriptor(item)
                item.update(self.wrapInstanceDescriptor(instanceDescriptor))
    # rules

    @coalescingDecorator(delay=0.2)
    def rulesEditorCallback(self, sender):
        rulesParser.storeRules(sender.get(), self.operator)
        self.setDocumentNeedSave(True, who="Rules")

    # labels

    locationLabelsPreview = None

    def locationLabelsToolsCallback(self, sender):
        if self.operator.findDefault() is None:
            self.showMessage("No default is found.", "Place a source on the default location of all axes.")
        else:
            try:
                self.locationLabelsPreview.w.show()
            except Exception:
                self.locationLabelsPreview = LocationLabelsPreview(operator=self.operator)

    @coalescingDecorator(delay=0.2)
    def locationLabelsEditorCallback(self, sender):
        labelsParser.storeLocationLabels(sender.get(), self.operator)
        self.setDocumentNeedSave(True, who="LocationLabels")

    # variable fonts

    def variableFontsEditorToolsCallback(self, sender):
        value = sender.get()
        if value == 0:
            # Add All Possible Variable Fonts
            def callback(result=True):
                if result:
                    # this does not check and compare with extising variable font entries
                    self.operator.variableFonts.clear()
                    self.operator.variableFonts.extend(self.operator.getVariableFonts())
                    self.variableFonts.editor.set(variableFontsParser.dumpVariableFonts(self.operator.variableFonts))
                    self.setDocumentNeedSave(True, who="VariableFonts")

            if self.operator.variableFonts:
                self.showAskYesNo(
                    messageText="Add All Possible Variable Fonts will remove existing variable fonts.",
                    informativeText="Do you want to replace them?",
                    callback=callback
                )
            else:
                callback()

    @coalescingDecorator(delay=0.2)
    def variableFontsEditorCallback(self, sender):
        variableFontsParser.storeVariableFonts(sender.get(), self.operator)
        self.setDocumentNeedSave(True, who="VariableFonts")

    # problems

    def problemsToolsCallback(self, sender):
        value = sender.get()
        if value == 0:
            # validate
            self.validate()

    # notes
    @coalescingDecorator(delay=0.2)
    def notesEditorCallback(self, sender):
        self.operator.lib[designspacenotesLibKey] = sender.get()
        self.setDocumentNeedSave(True, who="Notes")

    def validate(self):
        # validate with the designspaceProblems checker
        checker = DesignSpaceChecker(self.operator)
        checker.checkEverything()
        report = []
        for problem in checker.problems:
            cat, desc = problem.getDescription()
            if problem.isStructural():
                icon = "❗️"
            else:
                icon = "❕"
            data = ""
            if problem.details:
                data = problem.details
            elif problem.data:
                data = ", ".join([f"{key}: {value}" for key, value in problem.data.items() if value])
            d = dict(problemIcon=icon, problemClass=cat, problemDescription=desc, problemData=data)
            report.append(d)
        self.problems.list.set(report)

    # tools

    def listMenuCallack(self, sender):
        tableView = sender.getNSTableView()
        if not tableView.dataSource().arrangedObjects():
            return
        point = AppKit.NSEvent.mouseLocation()
        point = tableView.window().convertPointFromScreen_(point)
        point = tableView.convertPoint_fromView_(point, None)
        columnIndex = tableView.columnAtPoint_(point)
        rowIndex = tableView.rowAtPoint_(point)

        column = tableView.tableColumns()[columnIndex]
        columnIdentifier = column.identifier()
        axisName = column.title()
        item = tableView.dataSource().arrangedObjects()[rowIndex]

        selectedItems = [sender[i] for i in sender.getSelection()]

        tableView.selectedRowIndexes()

        defaultLocation = self.operator.newDefaultLocation(bend=True)

        def menuCallback(menuItem):
            item[columnIdentifier] = float(menuItem.title())

        def menuMakeDefaultCallback(menuItem):
            for axisName, value in defaultLocation.items():
                item[f"axis_{axisName}"] = value

        def revealInFinderCallback(menuItem):
            workspace = AppKit.NSWorkspace.sharedWorkspace()
            workspace.selectFile_inFileViewerRootedAtPath_(item["object"].path, "")

        def forceSourcesChangeCallback(menuItem):
            self.operator.sourcesChanged(clearCaches=True)

        def sliderCallback(slider):
            item[columnIdentifier] = slider.get()

        def convertInstanceToUserLocation(menuItem):
            for item in selectedItems:
                instanceDescriptor = item["object"]
                instanceDescriptor.userLocation = instanceDescriptor.getFullUserLocation(self.operator)
                instanceDescriptor.designLocation.clear()
                item.update(self.wrapInstanceDescriptor(instanceDescriptor))

        def convertInstanceToDesignLocation(menuItem):
            for item in selectedItems:
                instanceDescriptor = item["object"]
                instanceDescriptor.designLocation = instanceDescriptor.getFullDesignLocation(self.operator)
                instanceDescriptor.userLocation.clear()
                item.update(self.wrapInstanceDescriptor(instanceDescriptor))

        def menuSetPreviewToSelectionCallback(menuItem):
            selectedObject = selectedItems[0]['object']
            selectedDesignLocation = selectedObject.getFullDesignLocation(self.operator)
            self.operator.setPreviewLocation(selectedDesignLocation)

        def newInstanceBetween(menuItem):
            # make a new instance at the average of all selected instances
            first = selectedItems[0]['object']
            firstLocation = first.getFullDesignLocation(self.operator)
            firstContinuous, firstDiscrete = self.operator.splitLocation(firstLocation)
            second = selectedItems[1]['object']
            secondLocation = second.getFullDesignLocation(self.operator)
            secondContinuous, secondDiscrete = self.operator.splitLocation(secondLocation)
            # make sure both selected instances are in the same discrete space
            if firstDiscrete != secondDiscrete:
                self.showMessage("Can't make a new instance:", "Select instances in the same discrete spaces.")
                return
            location = self.operator.newDefaultLocation(discreteLocation=firstDiscrete)
            for axisName in firstContinuous.keys():
                newValue = .5 * (firstContinuous.get(axisName) + secondContinuous.get(axisName))
                location[axisName] = newValue
            newFamilyName = first.familyName
            newStyleName = f"{first.styleName}_{second.styleName}"
            # postScriptFontName = f"{newFamilyName}-{newStyleName}"
            instanceUFOFileName = postScriptNameTransformer(newFamilyName, newStyleName) + ".ufo"
            self.operator.addInstanceDescriptor(
                familyName=first.familyName,
                styleName=newStyleName,
                designLocation=location,
                filename=instanceUFOFileName,
                # postScriptFontName=postScriptFontName,
            )

        def updateUFOFilenameFromFontNames(menuItem):
            for item in selectedItems:
                instanceDescriptor = item["object"]
                instanceDescriptor.filename = fileNameForInstance(instanceDescriptor)
                item.update(self.wrapInstanceDescriptor(instanceDescriptor))
            self.instancesChanged()

        # def updatePostScriptFontNameFromFontNamesCallback(menuItem):
        #     for item in selectedItems:
        #         instanceDescriptor = item["object"]
        #         psName = f"{instanceDescriptor.familyName}-{instanceDescriptor.styleName}"
        #         psName = psName.replace(" ", "")    # does this need to filter more?
        #         instanceDescriptor.postScriptFontName = psName
        #         item.update(self.wrapInstanceDescriptor(instanceDescriptor))
        #     self.instancesChanged()

        def openUFO(menuItem):
            self.openSelectedItem(sender)

        menu = []
        for axisDescriptor in self.operator.axes:
            if axisDescriptor.name == axisName:
                if hasattr(axisDescriptor, "values"):
                    menu.extend([dict(title=numberToString(value), callback=menuCallback) for value in axisDescriptor.values])
                else:
                    values = set((axisDescriptor.minimum, axisDescriptor.default, axisDescriptor.maximum, defaultLocation[axisDescriptor.name]))
                    for value in sorted(values):
                        menu.append(dict(title=numberToString(value), callback=menuCallback))

                    if not isinstance(item[columnIdentifier], (tuple, list)):
                        menu.append("----")
                        self._menuGroup = vanilla.Group((0, 0, 150, 30))

                        self._menuGroup.slider = vanilla.Slider(
                            (10, 0, 130, 22),
                            minValue=axisDescriptor.minimum,
                            maxValue=axisDescriptor.maximum,
                            value=item[columnIdentifier],
                            callback=sliderCallback,
                            sizeStyle="mini"
                        )
                        self._menuGroup.getNSView().setFrame_(((0, 0), (150, 30)))
                        menuItem = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("sourceSlider", None, "")
                        menuItem.setView_(self._menuGroup.getNSView())
                        menu.append(menuItem)

        if sender.designspaceContent == "sources":
            if selectedItems:
                menu.append("----")
                if item["object"].path and os.path.exists(item["object"].path):
                    menu.append("----")
                    menu.append(dict(title="Open Source UFO", callback=openUFO))
                    menu.append(dict(title="Reveal Source in Finder", callback=revealInFinderCallback))
                menu.append("----")
                menu.append(dict(title="Move to Default Location", callback=menuMakeDefaultCallback))
                if len(selectedItems) == 1:
                    menu.append(dict(title="Set Preview to Selection", callback=menuSetPreviewToSelectionCallback))

            menu.append("----")
            menu.append(dict(title="Force Refresh of All Sources", callback=forceSourcesChangeCallback))

        if selectedItems and sender.designspaceContent == "instances":
            menu.append("----")
            menu.append(dict(title="Open Instance UFO", callback=openUFO))
            menu.append(dict(title="Reveal Instance in Finder", callback=revealInFinderCallback))
            menu.append("----")
            menu.append(dict(title="Update UFO Filename", callback=updateUFOFilenameFromFontNames))
            # menu.append(dict(title="Update PostScript Font Name", callback=updatePostScriptFontNameFromFontNamesCallback))
            menu.append("----")
            menu.append(dict(title="Convert to User Location", callback=convertInstanceToUserLocation))
            menu.append(dict(title="Convert to Design Location", callback=convertInstanceToDesignLocation))
            if len(selectedItems) == 1:
                menu.append(dict(title="Set Preview to Selection", callback=menuSetPreviewToSelectionCallback))
            if len(selectedItems) == 2:
                menu.append(dict(title="New instance inbetween", callback=newInstanceBetween))

        return menu

    def convertAxisTo(self, axisDescriptor, destinationClass, **kwargs):
        index = self.operator.axes.index(axisDescriptor)
        newAxisDescriptor = destinationClass(
            tag=axisDescriptor.tag,
            name=axisDescriptor.name,
            labelNames=axisDescriptor.labelNames,
            default=axisDescriptor.default,
            hidden=axisDescriptor.hidden,
            map=axisDescriptor.map,
            axisLabels=axisDescriptor.axisLabels,
            **kwargs
        )
        self.operator.axes[index] = newAxisDescriptor
        return newAxisDescriptor

    def convertContinuousAxisToDiscreteAxis(self, axisDescriptor):
        return self.convertAxisTo(
            axisDescriptor,
            self.operator.writerClass.discreteAxisDescriptorClass
        )

    def convertDiscreteAxisToContinuousAxis(self, axisDescriptor):
        return self.convertAxisTo(
            axisDescriptor,
            self.operator.writerClass.axisDescriptorClass,
            minimum=min(0, axisDescriptor.default),
            maximum=max(1000, axisDescriptor.default)
        )

    def openSelectedItem(self, listObject):
        selection = listObject.getSelection()
        # todo:
        # find font if its already open and replace it internally in the operator?
        # fontPathMap = {font.path: font for font in AllFonts() if font.path is not None}
        if selection:
            progress = self.startProgress("Opening UFO...", len(selection))
            for index in selection:
                item = listObject[index]
                descriptor = item["object"]
                if descriptor.path is None:
                    continue
                if descriptor.flavor == "instance":
                    if os.path.exists(descriptor.path):
                        OpenFont(descriptor.path)
                elif descriptor.flavor == "source":
                    name = descriptor.name
                    internalFontObject = self.operator.fonts.get(name)
                    if internalFontObject is None:
                        continue
                    try:
                        font = RFont(internalFontObject, showInterface=True)
                        SendNotification.single("Sources", action="Open", font=font, designspace=self.operator)
                    except Exception as e:
                        print(f"Bad UFO: {path}, {e}")
                        pass
                progress.update()
            progress.close()

    def windowShouldClose(self, window):
        def callback(result):
            if result == 0:
                # save
                self.toolbarSave(None)
            elif result == 1:
                # dont save
                self.setDocumentNeedSave(False)
                self.w.close()
            elif result == 2:
                # cancel
                pass
        if self.w.getNSWindow().isDocumentEdited():
            self.showAsk(
                messageText="Do you want to save the changes made to the document?",
                informativeText="Your changes will be lost if youd don't save them.",
                buttonTitles=[("Save...", 0), ("Don't Save", 1), ("Cancel", 2)],
                callback=callback
            )
        return not self.w.getNSWindow().isDocumentEdited()

    def setDocumentNeedSave(self, state=True, **notificationsKwargs):
        if self.holdChanges:
            return
        if state:
            if notificationsKwargs:
                self.operator.changed(**notificationsKwargs)
            self.operator.changed()
        else:
            self.w.getNSWindow().setDocumentEdited_(False)

    def setWindowTitleFromPath(self, path):
        if path is not None:
            self.w.getNSWindow().setRepresentedURL_(AppKit.NSURL.fileURLWithPath_(path))
            self.w.setTitle(os.path.basename(path))

    def updateColumnHeadersFromAxes(self):
        updateLists = [
            (self.sources.list, dict()),
            (self.instances.list, dict(formatter=numberListFormatter))
        ]
        for listObject, options in updateLists:
            tableView = listObject.getNSTableView()
            for column in list(tableView.tableColumns()):
                if column.identifier().startswith("axis_"):
                    tableView.removeTableColumn_(column)
            for axis in self.operator.axes:
                identifier = f"axis_{axis.name}"
                column = AppKit.NSTableColumn.alloc().initWithIdentifier_(identifier)
                column.headerCell().setTitle_(axis.name)
                column.setEditable_(True)
                column.setResizingMask_(AppKit.NSTableColumnUserResizingMask | AppKit.NSTableColumnAutoresizingMask)
                column.setMinWidth_(70)
                column.setMaxWidth_(1000)
                column.setWidth_(70)
                column.bind_toObject_withKeyPath_options_("value", listObject._arrayController, f"arrangedObjects.{identifier}", {AppKit.NSCreatesSortDescriptorBindingOption: False})
                cell = column.dataCell()
                cell.setDrawsBackground_(False)
                cell.setStringValue_("")
                cell.setFormatter_(options.get("formatter", numberFormatter))

                listObject._arrayController.addObserver_forKeyPath_options_context_(listObject._editObserver, f"arrangedObjects.{identifier}", AppKit.NSKeyValueObservingOptionNew, 0)
                listObject.getNSTableView().addTableColumn_(column)
                listObject._orderedColumnIdentifiers.append(identifier)

                # tableView.moveColumn_toColumn_()

                for item in listObject:
                    if identifier not in item:
                        location = item["object"].location
                        item[identifier] = location.get(axis.name, axis.default)
            tableView.sizeToFit()

    # drag and drop

    def dragCallback(self, sender, indexes):
        return indexes

    def dropCallback(self, sender, dropInfo):
        isProposal = dropInfo["isProposal"]

        if not isProposal:
            indexes = [int(i) for i in sorted(dropInfo["data"])]
            indexes.sort()
            rowIndex = dropInfo["rowIndex"]
            items = sender.get()
            toMove = [items[index] for index in indexes]
            for index in reversed(indexes):
                del items[index]
            rowIndex -= len([index for index in indexes if index < rowIndex])
            for item in toMove:
                items.insert(rowIndex, item)
                rowIndex += 1
            with self.holdChanges:
                sender.set(items)
                # update internal operator objects
                descriptors = [item["object"] for item in items]
                if sender.designspaceContent == "axes":
                    self.operator.axes[:] = descriptors
                elif sender.designspaceContent == "sources":
                    self.operator.sources[:] = descriptors
                elif sender.designspaceContent == "instances":
                    self.operator.instances[:] = descriptors
        return True

    # validation

    def validateAxisName(self, name):
        for axisDescriptor in self.operator.axes:
            if axisDescriptor.name == name:
                return False
        return True

    def validateAxisTag(self, tag):
        for axisDescriptor in self.operator.axes:
            if axisDescriptor.tag == tag:
                return False
        return True

    # toolbar
    
    def toolbarPrepolator(self, sender):
        import prepolator
        if self.operator.sources:
            prepolator.OpenPrepolator(ufoOperator=self.operator)

    def toolbarBatch(self, sender):
        import batch
        if self.operator.path:
            batch.BatchController([self.operator.path])

    def toolbarSelectTab(self, sender):
        selectedTab = sender.label()
        # if selectedTab == "Problems":
        #     self.validate()
        if selectedTab == "Sources":
            self.updateSources()
        self.w.tabs.set(self.tabItems.index(selectedTab))

    locationPreview = None

    def toolbarPreview(self, sender):
        try:
            self.locationPreview.w.show()
        except Exception:
            self.locationPreview = LocationPreview(
                operator=self.operator,
                selectedSources=[self.sources.list[index]["object"] for index in self.sources.list.getSelection()],
                selectedInstances=[self.instances.list[index]["object"] for index in self.instances.list.getSelection()],
            )

    def toolbarSave(self, sender):

        def saveDesignspace(path):
            # so we have the path for this operator
            # we need to make sure the sources and instances are all in the right place
            root = os.path.dirname(path)
            for wrappedSourceDescriptor in self.sources.list:
                sourceDescriptor = self.unwrapSourceDescriptor(wrappedSourceDescriptor)
                sourceDescriptor.filename = os.path.relpath(sourceDescriptor.path, root)
            for wrappedInstanceDescriptor in self.instances.list:
                instanceDescriptor = self.unwrapInstanceDescriptor(wrappedInstanceDescriptor)
                if instanceDescriptor.filename is None:
                    # maybe DSE should always update the ufo name?
                    instanceDescriptor.filename = fileNameForInstance(instanceDescriptor)
                instanceDescriptor.path = os.path.abspath(os.path.join(root, instanceDescriptor.filename))

            # TODO self.operator.lib[self.mathModelPrefKey] = self.mathModelPref
            self.operator.write(path)
            self.updateSources()
            self.setWindowTitleFromPath(path)
            self.setDocumentNeedSave(False)
            SendNotification.single(action="SaveDesignspace", designspace=self.operator)

        if len(self.operator.axes) == 0:
            self.showMessage(
                messageText="No axes defined!",
                informativeText="The designspace needs at least one axis before saving."
            )
        elif any([source.path is None for source in self.operator.sources]):
            self.showMessage(
                messageText="Save the sources first!",
                informativeText="All sources must be saved to disk before saving the designspace."
            )
        elif self.operator.path is None or AppKit.NSEvent.modifierFlags() & AppKit.NSAlternateKeyMask:
            if self.operator.path is None:
                # check if we have defined any axes
                # can't save without axes
                # get a filepath first
                sourcePaths = set([os.path.dirname(source.path) for source in self.operator.sources if source.path])
                saveToDir = None
                saveToName = 'Untitled'
                if sourcePaths:
                    saveToDir = sorted(sourcePaths)[0]
            else:
                saveToDir = os.path.dirname(self.operator.path)
                saveToName = os.path.basename(self.operator.path)

            self.showPutFile(
                messageText="Save designspace:",
                directory=saveToDir,
                fileName=saveToName,
                canCreateDirectories=True,
                fileTypes=['designspace'],
                callback=saveDesignspace
            )

        else:
            saveDesignspace(self.operator.path)

    def toolbarHelp(self, sender):
        designspaceBundle.developerURL = "https://letterror.github.io/designSpaceRoboFontExtension/"
        designspaceBundle.developer = "Documentation"

        helpWindow = designspaceBundle.openHelp()
        helpWindow.visitButton.setTitle_(" Open on Browser ")
        helpWindow.visitButton.sizeToFit()

        visitButtonToolbarItem = helpWindow.w.getToolbarItems()["developerURL"]
        visitButtonToolbarItem.setMinSize_(helpWindow.visitButton.frame().size)
        visitButtonToolbarItem.setMaxSize_(helpWindow.visitButton.frame().size)

    def toolbarSettings(self, sender):
        pass

    # notifications

    def roboFontFontDidOpen(self, notification):
        font = notification["font"]
        for sourceDescriptor in self.operator.sources:
            if sourceDescriptor.path == font.path:
                self.operator.fonts[sourceDescriptor.name] = font.asDefcon()
                SendNotification.single("Sources", action="OpenUFO", designspace=self.operator, font=font)
                break

    def roboFontFontWillClose(self, notification):
        font = notification["font"]
        for sourceDescriptor in self.operator.sources:
            if sourceDescriptor.path == font.path:
                SendNotification.single("Sources", action="CloseUFO", designspace=self.operator, font=font)
                break

    # axes notifications

    designspaceEditorAxesDidAddAxisDelay = 0

    @notificationConductor
    def designspaceEditorAxesDidAddAxis(self, notification):
        axisDescriptor = notification["axis"]
        self.axes.list.append(AxisListItem(axisDescriptor, self))

    designspaceEditorAxesDidRemoveAxisDelay = 0

    @notificationConductor
    def designspaceEditorAxesDidRemoveAxis(self, notification):
        axisDescriptor = notification["axis"]
        for item in list(self.axes.list):
            if item.axisDescriptor == axisDescriptor:
                self.axes.list.remove(item)
                return

    # sources notifications

    designspaceEditorDidChangeDelay = 0

    @notificationConductor
    def designspaceEditorDidChange(self, notification):
        self.w.getNSWindow().setDocumentEdited_(True)

    designspaceEditorSourcesDidAddSourceDelay = 0

    @notificationConductor
    def designspaceEditorSourcesDidAddSource(self, notification):
        sourceDescriptor = notification["source"]
        self.sources.list.append(self.wrapSourceDescriptor(sourceDescriptor))

    designspaceEditorSourcesDidRemoveSourceDelay = 0

    @notificationConductor
    def designspaceEditorSourcesDidRemoveSource(self, notification):
        sourceDescriptor = notification["source"]
        for item in list(self.sources.list):
            if item["object"] == sourceDescriptor:
                self.sources.list.remove(item)
                return

    @notificationConductor
    def designspaceEditorSourcesDidChange(self, notification):
        if len(self.operator.sources) == len(self.sources.list):
            for item, sourceDescriptor in zip(self.sources.list, self.operator.sources):
                item.update(self.wrapSourceDescriptor(sourceDescriptor))
        else:
            self.sources.list.set([self.wrapSourceDescriptor(sourceDescriptor) for sourceDescriptor in self.operator.instances])

        self.updateColumnHeadersFromAxes()

    # instances notifications

    designspaceEditorInstancesDidAddInstanceDelay = 0

    @notificationConductor
    def designspaceEditorInstancesDidAddInstance(self, notification):
        instanceDescriptor = notification["instance"]
        self.instances.list.append(self.wrapInstanceDescriptor(instanceDescriptor))

    designspaceEditorInstancesDidRemoveInstanceDelay = 0

    @notificationConductor
    def designspaceEditorInstancesDidRemoveInstance(self, notification):
        instanceDescriptor = notification["instance"]
        for item in list(self.instances.list):
            if item["object"] == instanceDescriptor:
                self.instances.list.remove(item)
                return

    @notificationConductor
    def designspaceEditorInstancesDidChange(self, notification):
        if len(self.operator.instances) == len(self.instances.list):
            for item, instanceDescriptor in zip(self.instances.list, self.operator.instances):
                item.update(self.wrapInstanceDescriptor(instanceDescriptor))
        else:
            self.instances.list.set([self.wrapInstanceDescriptor(instanceDescriptor) for instanceDescriptor in self.operator.instances])

    @notificationConductor
    def designspaceEditorRulesDidChange(self, notification):
        self.rules.editor.set(rulesParser.extractRules(self.operator))

    @notificationConductor
    def designspaceEditorLocationLabelsDidChange(self, notification):
        print(self.locationLabels)
        self.locationLabels.editor.set(labelsParser.extractLocationLabels(self.operator))

    @notificationConductor
    def designspaceEditorVariableFontsDidChange(self, notification):
        self.variableFonts.editor.set(variableFontsParser.extractVariableFonts(self.operator))


if __name__ == '__main__':
    pathForBundle = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    designspaceBundle = ExtensionBundle(path=pathForBundle)

    path = "/Users/frederik/Documents/dev/letterror/mutatorSans/MutatorSans.designspace"
    # path = "/Users/frederik/Documents/fontsGit/RoboType/RF.designspace"
    path = None
    DesignspaceEditorController(path)
