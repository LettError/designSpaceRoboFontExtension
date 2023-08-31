import os
import weakref
import AppKit

import vanilla

from fontTools import designspaceLib
from ufoProcessor import ufoOperator

from mojo.UI import CodeEditor, SliderEditStepper
from mojo.events import addObserver, removeObserver
from mojo.subscriber import WindowController
from mojo.extensions import getExtensionDefault, ExtensionBundle
from mojo.roboFont import AllFonts, OpenFont, RFont, internalFontClasses

from lib.tools.debugTools import ClassNameIncrementer
from lib.tools.misc import coalescingDecorator
from lib.cells.doubleClickCell import RFDoubleClickCell

from designspaceProblems import DesignSpaceChecker

from designspaceEditor.designspaceLexer import DesignspaceLexer, TextLexer
from designspaceEditor.parsers import mapParser, rulesParser, labelsParser, glyphNameParser, variableFontsParser
from designspaceEditor.parsers.parserTools import numberToString
from designspaceEditor.tools import holdRecursionDecorator, addToolTipForColumn, TryExcept, HoldChanges, symbolImage, NumberListFormatter, SendNotification
from designspaceEditor.instancesPreview import InstancesPreview
from designspaceEditor.designspaceSubscribers import registerOperator, unregisterOperator


designspaceBundle = ExtensionBundle("DesignspaceEditor2")

registeredAxisTags = [
    ("italic", "ital"),
    ("optical", "opsz"),
    ("slant", "slnt"),
    ("width", "wdth"),
    ("weight", "wght"),
]

preferredAxes = [
    ("weight", "wght", 400, 700, 400),
    ("width", "wdth", 50, 100, 100),
    ("optical", "opsz", 10, 16, 10),
    # ("italic", "ital", 0, 0, 0),  # must be a discrete axis
    # ("slant", "slnt", -90, 0, 90),
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


class DesingspaceEditorOperator(ufoOperator.UFOOperator):

    def _instantiateFont(self, path):
        return internalFontClasses.createFontObject(path)


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

    def controleEditCallback(self, sender=None):
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
        SendNotification.single("AxisMap", designspace=self.operator)
        self.controleEditCallback(sender)

    def axisLabelsEditorCallback(self, sender):
        SendNotification.single("AxisLabels", designspace=self.operator)
        self.controleEditCallback(sender)

    def close(self):
        if not self.isDiscreteAxis:
            self.axisDescriptor.map = mapParser.parseMap(self.axisMap.editor.get())

        labelNames, axisLabels = labelsParser.parseAxisLabels(self.axisLabels.editor.get())
        self.axisDescriptor.labelNames = labelNames
        self.axisDescriptor.axisLabels = axisLabels


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
            callback=self.controleEditCallback
        )

        self.sourceMutedGlyphNames.editor = CodeEditor(
            (10, 10, -10, -10),
            glyphNameParser.dumpGlyphNames(self.sourceDescriptor.mutedGlyphNames),
            lexer=TextLexer(),
            showLineNumbers=False,
            callback=self.controleEditCallback
        )

    def close(self):
        labels, _ = labelsParser.parseAxisLabels(self.sourceLocalisedFamilyName.editor.get())
        self.sourceDescriptor.localisedFamilyName = labels
        self.sourceDescriptor.mutedGlyphNames = glyphNameParser.parseGlyphNames(self.sourceMutedGlyphNames.editor.get())


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


class LocationLabelsPreview(BaseNotificationObserver):

    notifications = [
        ("designspaceEditorDidChange", "designspaceEditorDidChange"),
        ("designspaceEditorLabelsDidChange", "designspaceEditorLabelsDidChange")
    ]

    def __init__(self, operator):
        self.w = vanilla.FloatingWindow((250, 300), "Labels Preview")
        self.operator = operator
        self.w.languages = vanilla.PopUpButton((10, 10, 80, 22), [], self.controlEdited)
        self.w.previewText = vanilla.TextBox((100, 10, -10, 22))
        self.build()
        self.w.bind("close", self.windowCloseCallback)
        self.observeNotifications()
        self.w.open()

    def windowCloseCallback(self, sender):
        self.removeObserverNotifications()
        self.operator = None

    def build(self):
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

    def designspaceEditorDidChange(self, info):
        self.build()

    def designspaceEditorLabelsDidChange(self, info):
        self.controlEdited(setLanguages=self.w.languages.getItem())


class DesignspaceEditorController(WindowController, BaseNotificationObserver):

    notifications = [
        ("fontDidOpen", "roboFontFontDidOpen"),
        ("fontWillClose", "roboFontFontWillClose"),
    ]

    def __init__(self, path=None):
        self.holdChanges = HoldChanges()
        with self.holdChanges:
            super().__init__()
            self.load(path)

    def build(self):
        self.operator = DesingspaceEditorOperator()

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
        ) for tabItem in self.tabItems]

        toolbarItems.extend([
            dict(itemIdentifier=AppKit.NSToolbarSpaceItemIdentifier),
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
            segmentDescriptions=[dict(title=f"Add {preferredAxis[0].title()} Axis") for preferredAxis in preferredAxes]
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
            dict(title="Open UFO"),
            dict(title="Add Open UFOs"),
            # dict(title="Load Names"),
            dict(title="Replace UFO"),
        ]
        self.sources.editorTools = vanilla.SegmentedButton(
            (72, 5, 400, 22),
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
            dict(title="UFO", key="sourceUFOFileName", width=200, minWidth=100, maxWidth=350, editable=False),
            dict(title="Famiy Name", key="sourceFamilyName", editable=True, width=130, minWidth=130, maxWidth=250),
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
            dict(title="Generate with MutatorMath"),
            dict(title="Generate with VarLib")
        ]
        self.instances.generateTools = vanilla.SegmentedButton(
            (330, 5, 320, 22),
            selectionStyle="momentary",
            callback=self.instancesEditorGenerateToolsCallback,
            segmentDescriptions=instancesEditorGenerateToolsSsegmentDescriptions
        )

        self.instances.previewTools = vanilla.SegmentedButton(
            (660, 5, 130, 22),
            selectionStyle="momentary",
            callback=self.instancesEditorPreviewToolsCallback,
            segmentDescriptions=[dict(title="Instances Preview")]
        )


        # instancesDoubleClickCell = RFDoubleClickCell.alloc().init()
        # instancesDoubleClickCell.setDoubleClickCallback_(self.instancesListDoubleClickCallback)
        # instancesDoubleClickCell.setImage_(infoImage)

        instancesColumnDescriptions = [
            # dict(title="", key="genericInfoButton", width=20, editable=False, cell=instancesDoubleClickCell),
            dict(title="UFO", key="instanceUFOFileName", width=200, minWidth=100, maxWidth=350, editable=False),
            dict(title="Famiy Name", key="instanceFamilyName", editable=True, width=130, minWidth=130, maxWidth=250),
            dict(title="Style Name", key="instanceStyleName", editable=True, width=130, minWidth=130, maxWidth=250),
        ]

        self.instances.list = vanilla.List(
            (0, 30, 0, 0),
            [],
            editCallback=self.instancesListEditCallback,
            columnDescriptions=instancesColumnDescriptions,
            menuCallback=self.listMenuCallack,
            selectionCallback=self.instancesListSelectionCallback,
            dragSettings=dict(type="sourcesListDragAndDropType", callback=self.dragCallback),
            selfDropSettings=dict(type="sourcesListDragAndDropType", operation=AppKit.NSDragOperationMove, callback=self.dropCallback),
        )
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
        self.variableFonts.editor = CodeEditor((0, 30, 0, 0), lexer=DesignspaceLexer(), showLineNumbers=False, callback=self.variableFontsEditorCallback)

        # PROBLEMS
        self.problems.tools = vanilla.SegmentedButton(
            (10, 5, 90, 22),
            selectionStyle="momentary",
            callback=self.problemsToolsCallback,
            segmentDescriptions=[dict(title="Validate")]
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
        for controller in [self.locationLabelsPreview, self.instancesPreview]:
            try:
                controller.w.close()
            except Exception:
                pass

        SendNotification.single(action="CloseDesignspace", designspace=self.operator)
        unregisterOperator(self.operator)
        del self.operator
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

    def loadObjects(self):
        with self.holdChanges:
            self.axes.list.set([AxisListItem(axisDescriptor, self) for axisDescriptor in self.operator.axes])
            self.sources.list.set([self.wrapSourceDescriptor(sourceDescriptor) for sourceDescriptor in self.operator.sources])
            self.instances.list.set([self.wrapInstanceDescriptor(instanceDescriptor) for instanceDescriptor in self.operator.instances])
            self.rules.editor.set(rulesParser.dumpRules(self.operator.rules))
            self.locationLabels.editor.set(labelsParser.dumpLocationLabels(self.operator.locationLabels))
            self.notes.editor.set(self.operator.lib.get(designspacenotesLibKey, ""))
            self.updateColumnHeadersFromAxes()

    # AXES

    def axisToolsCallback(self, sender):
        with self.holdChanges:
            value = sender.get()
            if value == 1:
                # remove
                for index in reversed(self.axes.list.getSelection()):
                    item = self.axes.list[index]
                    with SendNotification("Axes", action="RemoveAxis", designspace=self.operator):
                        self.operator.axes.remove(item.axisDescriptor)
                    self.axes.list.remove(item)
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
        value = sender.get()
        name, tag, minimum, maximum, default = preferredAxes[value]
        self._addAxis(name, tag, minimum, maximum, default)

        self.setDocumentNeedSave(True, who="Axes")
        self.updateColumnHeadersFromAxes()

    def _addAxis(self, name, tag, minimum, maximum, default):
        if self.validateAxisName(name) and self.validateAxisTag(tag):
            with SendNotification("Axes", action="AddAxis", designspace=self.operator) as notification:
                axisDescriptor = self.operator.addAxisDescriptor(
                    name=name,
                    tag=tag,
                    minimum=minimum,
                    maximum=maximum,
                    default=default
                )
                notification["axis"] = axisDescriptor
            self.axes.list.append(AxisListItem(axisDescriptor, self))
        else:
            print(f"Duplicate axis: '{name}'")

    def axisListDoubleClickCallback(self, sender):
        self.axisPopover = AxisAttributesPopover(self.axes.list, self.operator, closeCallback=self.axesChangedCallback)

    def axesListEditCallback(self, sender):
        self.axesChangedCallback()

    def axesChangedCallback(self):
        self.setDocumentNeedSave(True, who="Axes")

    def axesListSelectionCallback(self, sender):
        if self.holdChanges:
            return
        selectedItems = [sender[index]["object"] for index in sender.getSelection()]
        SendNotification.single("Axes", action="ChangeSelection", selectedItems=selectedItems, designspace=self.operator)

    # SOURCES

    def sourcesToolsCallback(self, sender):

        def addSourceCallback(paths):
            for path in paths:
                self.addSourceFromPath(path)
            # TODO self.enableInstanceList()
            # TODO  self.updatePaths()

        with self.holdChanges:
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
                    with SendNotification("Sources", action="RemoveSource", designspace=self.operator):
                        sourceDescriptor = item["object"]
                        self.operator.sources.remove(sourceDescriptor)
                        if sourceDescriptor.name in self.operator.fonts:
                            del self.operator.fonts[sourceDescriptor.name]
                    self.sources.list.remove(item)
        self.setDocumentNeedSave(True, who="Sources")

    def sourcesEditorToolsCallback(self, sender):
        value = sender.get()
        if value == 0:
            # Open UFO
            self.openSelectedItem(self.sources.list)
        elif value == 1:
            # Add Open UFOs
            existingSourcePaths = [sourceDescriptor.path for sourceDescriptor in self.operator.sources]
            for font in AllFonts():
                if font.path not in existingSourcePaths:
                    self.addSourceFromFont(font)
        elif value == 2:
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
                        self.setDocumentNeedSave(True)

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
        with SendNotification("Sources", action="AddSource", designspace=self.operator) as notification:
            sourceDescriptor = self.operator.addSourceDescriptor(
                path=font.path,
                filename=filename,
                familyName=font.info.familyName,
                styleName=font.info.styleName,
                location=defaultLocation
            )
            notification["source"] = sourceDescriptor
        self.operator.fonts[sourceDescriptor.name] = font.asDefcon()
        self.sources.list.append(self.wrapSourceDescriptor(sourceDescriptor))
        self.setDocumentNeedSave(True)

    def wrapSourceDescriptor(self, sourceDescriptor):
        wrapped = dict(
            sourceHasPath=checkSymbol if sourceDescriptor.path and os.path.exists(sourceDescriptor.path) else "",
            sourceIsDefault=defaultSymbol if sourceDescriptor == self.operator.findDefault() else "",
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
        sourceDescriptor.familyName = wrappedSourceDescriptor["sourceFamilyName"] if wrappedSourceDescriptor["sourceFamilyName"] else None
        sourceDescriptor.styleName = wrappedSourceDescriptor["sourceStyleName"] if wrappedSourceDescriptor["sourceStyleName"] else None
        sourceDescriptor.layerName = wrappedSourceDescriptor["sourceLayerName"] if wrappedSourceDescriptor["sourceLayerName"] else None
        for axis in self.operator.axes:
            sourceDescriptor.location[axis.name] = wrappedSourceDescriptor.get(f"axis_{axis.name}", axis.default)
        return sourceDescriptor

    def sourcesListDoubleClickCallback(self, sender):
        self.sourcePopover = SourceAttributesPopover(self.sources.list, self.operator, closeCallback=[self.updateSources, self.setDocumentNeedSave])

    def sourcesListEditCallback(self, sender):
        self.updateSources()
        self.setDocumentNeedSave(True, who="Sources")

    def sourceListSelectionCallback(self, sender):
        if self.holdChanges:
            return
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
                if self.operator.instances:
                    familyName = self.operator.instances[0].familyName
                elif self.operator.sources:
                    familyName = self.operator.sources[0].familyName
                else:
                    familyName = "NewFamily"
                styleName = f"Style_{len(self.operator.instances)}"
                with SendNotification("Instances", action="AddInstance", designspace=self.operator) as notification:
                    instanceDescriptor = self.operator.addInstanceDescriptor(
                        familyName=familyName,
                        designLocation=self.operator.newDefaultLocation(),
                        styleName=styleName,
                        filename=os.path.join(getExtensionDefault('instanceFolderName', 'instances'), f"{familyName}-{styleName}.ufo")
                    )
                    notification["instance"] = instanceDescriptor

                    self.instances.list.append(self.wrapInstanceDescriptor(instanceDescriptor))
            elif value == 1:
                # remove
                for index in reversed(self.instances.list.getSelection()):
                    item = self.instances.list[index]
                    with SendNotification("Instances", action="RemoveInstance", designspace=self.operator):
                        self.operator.instances.remove(item["object"])
                    self.instances.list.remove(item)
        self.setDocumentNeedSave(True, who="Instances")

    def wrapInstanceDescriptor(self, instanceDescriptor):
        wrapped = dict(
            instanceUFOFileName=instanceDescriptor.filename if instanceDescriptor.filename is not None else os.path.join(getExtensionDefault('instanceFolderName', 'instances'), f"{instanceDescriptor.familyName}-{instanceDescriptor.styleName}.ufo"),
            instanceFamilyName=instanceDescriptor.familyName or "",
            instanceStyleName=instanceDescriptor.styleName or "",
            object=instanceDescriptor
        )
        for axis, value in instanceDescriptor.designLocation.items():
            wrapped[f"axis_{axis}"] = value
        return wrapped

    def unwrapInstanceDescriptor(self, wrappedInstanceDescriptor):
        instanceDescriptor = wrappedInstanceDescriptor["object"]
        instanceDescriptor.familyName = wrappedInstanceDescriptor["instanceFamilyName"]
        instanceDescriptor.styleName = wrappedInstanceDescriptor["instanceStyleName"]
        for axis in self.operator.axes:
            instanceDescriptor.designLocation[axis.name] = wrappedInstanceDescriptor.get(f"axis_{axis.name}", axis.default)
        return instanceDescriptor

    def instancesListDoubleClickCallback(self, sender):
        pass

    def instancesEditorToolsCallback(self, sender):
        value = sender.get()
        if value == 0:
            # duplicate
            for index in self.instances.list.getSelection():
                item = self.instances.list[index]
                instanceDescriptor = item["object"]
                with SendNotification("Instances", action="AddInstance", designspace=self.operator) as notification:
                    newInstanceDescriptor = self.operator.addInstanceDescriptor(**instanceDescriptor.asdict())
                    notification["instance"] = newInstanceDescriptor
                with self.holdChanges:
                    self.instances.list.append(self.wrapInstanceDescriptor(newInstanceDescriptor))
        elif value == 1:
            # Add Sources as Instances
            existingLocations = [instanceDescriptor.designLocation for instanceDescriptor in self.operator.instances]
            for sourceDescriptor in self.operator.sources:
                if sourceDescriptor.location not in existingLocations:
                    with SendNotification("Instances", action="AddInstance", designspace=self.operator) as notification:
                        newInstanceDescriptor = self.operator.addInstanceDescriptor(
                            familyName=sourceDescriptor.familyName,
                            styleName=sourceDescriptor.styleName,
                            designLocation=sourceDescriptor.location,
                            filename=os.path.join(getExtensionDefault('instanceFolderName', 'instances'), f"{sourceDescriptor.familyName}-{sourceDescriptor.styleName}.ufo")
                        )
                        notification["instance"] = newInstanceDescriptor
                    with self.holdChanges:
                        self.instances.list.append(self.wrapInstanceDescriptor(newInstanceDescriptor))

    def instancesEditorGenerateToolsCallback(self, sender):
        if self.operator.path is None:
            self.showMessage("Save the designspace first.", "Instances are generated in a relative path next to the designspace file.")
            return

        value = sender.get()

        self.operator.useVarlib = value == 1
        self.operator.roundGeometry = True
        self.operator.loadFonts()
        self.operator.findDefault()
        selection = self.instances.list.getSelection()
        if selection:
            items = [self.instances.list[index] for index in selection]
        else:
            items = self.instances.list
        for item in items:
            instanceDescriptor = item["object"]
            with TryExcept(self, "Generate Instance"):
                font = self.operator.makeInstance(instanceDescriptor)
                if not os.path.exists(os.path.dirname(instanceDescriptor.path)):
                    os.makedirs(os.path.dirname(instanceDescriptor.path))
                font.save(path=instanceDescriptor.path)

    instancesPreview = None

    def instancesEditorPreviewToolsCallback(self, sender):
        try:
            self.instancesPreview.w.show()
        except Exception:
            self.instancesPreview = InstancesPreview(
                operator=self.operator,
                selectedInstances=[self.instances.list[index]["object"] for index in self.instances.list.getSelection()],
                previewString="HELLO"
            )

    def instancesListEditCallback(self, sender):
        for wrappedInstanceDescriptor in sender:
            self.unwrapInstanceDescriptor(wrappedInstanceDescriptor)
        self.setDocumentNeedSave(True, who="Instances")

    def instancesListSelectionCallback(self, sender):
        if self.holdChanges:
            return
        selectedItems = [sender[index]["object"] for index in sender.getSelection()]
        SendNotification.single("Instances", action="ChangeSelection", selectedItems=selectedItems, designspace=self.operator)

    # rules

    @coalescingDecorator(delay=0.2)
    def rulesEditorCallback(self, sender):
        rules = rulesParser.parseRules(sender.get(), self.operator.writerClass.ruleDescriptorClass)
        self.operator.rules.clear()
        self.operator.rules.extend(rules)
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
        locationLabels = labelsParser.parseLocationLabels(sender.get(), self.operator.writerClass.locationLabelDescriptorClass)
        self.operator.locationLabels.clear()
        self.operator.locationLabels.extend(locationLabels)
        self.setDocumentNeedSave(True, who="Labels")

    @coalescingDecorator(delay=0.2)
    def variableFontsEditorCallback(self, sender):
        variableFonts = variableFontsParser.parseVariableFonts(sender.get(), self.operator.writerClass.variableFontDescriptorClass)
        self.operator.variableFonts.clear()
        self.operator.variableFonts.extend(variableFonts)
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
                data = ", ".join([f"{key}: {value}" for key, value in problem.data.items()])
            d = dict(problemIcon=icon, problemClass=cat, problemDescription=desc, problemData=data)
            report.append(d)
        self.problems.list.set(report)

    # tools

    def listMenuCallack(self, sender):
        tableView = sender.getNSTableView()
        point = AppKit.NSEvent.mouseLocation()
        point = tableView.window().convertPointFromScreen_(point)
        point = tableView.convertPoint_fromView_(point, None)
        columnIndex = tableView.columnAtPoint_(point)
        rowIndex = tableView.rowAtPoint_(point)

        column = tableView.tableColumns()[columnIndex]
        columnIdentifier = column.identifier()
        axisName = column.title()
        item = tableView.dataSource().arrangedObjects()[rowIndex]

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
            self.operator.changed()
            SendNotification.single("Sources", designspace=self.operator)

        def sliderCallback(slider):
            item[columnIdentifier] = slider.get()

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
            menu.append("----")
            menu.append(dict(title="Make Default", callback=menuMakeDefaultCallback))
            if item["object"].path and os.path.exists(item["object"].path):
                menu.append("----")
                menu.append(dict(title="Reveal in Finder", callback=revealInFinderCallback))

            menu.append("----")
            menu.append(dict(title="Force Sources Change", callback=forceSourcesChangeCallback))

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
                SendNotification.single(designspace=self.operator, **notificationsKwargs)
            SendNotification.single(designspace=self.operator)
            self.w.getNSWindow().setDocumentEdited_(True)
        else:
            self.w.getNSWindow().setDocumentEdited_(False)

    def setWindowTitleFromPath(self, path):
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
                column.bind_toObject_withKeyPath_options_("value", listObject._arrayController, f"arrangedObjects.{identifier}", None)
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
            for font in toMove:
                items.insert(rowIndex, font)
                rowIndex += 1
            sender.set(items)
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

    def toolbarSelectTab(self, sender):
        selectedTab = sender.label()
        # if selectedTab == "Problems":
        #     self.validate()
        if selectedTab == "Sources":
            self.updateSources()
        self.w.tabs.set(self.tabItems.index(selectedTab))

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
                    instanceDescriptor.filename = os.path.join(getExtensionDefault('instanceFolderName', 'instances'), f"{instanceDescriptor.familyName}-{instanceDescriptor.styleName}.ufo")
                instanceDescriptor.path = os.path.abspath(os.path.join(root, instanceDescriptor.filename))

            # TODO self.operator.lib[self.mathModelPrefKey] = self.mathModelPref
            self.operator.write(path)
            self.updateSources()
            self.setWindowTitleFromPath(path)
            self.setDocumentNeedSave(False)

        if len(self.operator.axes) == 0:
            self.showMessage(
                messageText="No axes defined!",
                informativeText="The designspace needs at least one axis before saving."
            )

        elif self.operator.path is None or AppKit.NSEvent.modifierFlags() & AppKit.NSAlternateKeyMask:
            if self.operator.path is None:
                # check if w have defined any axes
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
        designspaceBundle.openHelp()

    def toolbarSettings(self, sender):
        pass

    # notifications

    def roboFontFontDidOpen(self, notification):
        font = notification["font"]
        for sourceDescriptor in self.operator.sources:
            if sourceDescriptor.path == font.path:
                SendNotification.single("Sources", action="OpenUFO", designspace=self.operator, font=font)
                break

    def roboFontFontWillClose(self, notification):
        font = notification["font"]
        for sourceDescriptor in self.operator.sources:
            if sourceDescriptor.path == font.path:
                SendNotification.single("Sources", action="CloseUFO", designspace=self.operator, font=font)
                break


if __name__ == '__main__':
    pathForBundle = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    designspaceBundle = ExtensionBundle(path=pathForBundle)

    path = "/Users/frederik/Documents/dev/JustVanRossum/fontgoggles/Tests/data/MutatorSans/MutatorSans.designspace"
    #path = '/Users/frederik/Documents/dev/fonttools/Tests/designspaceLib/data/test_v4_original.designspace'
    #path = "/Users/frederik/Desktop/designSpaceEditorText/testFiles/Untitled.designspace"
    #path = None
    #path = '/Users/frederik/Documents/dev/letterror/ufoProcessor/Tests/202206 discrete spaces/test.ds5.designspace'
    #path = '/Users/frederik/Documents/dev/fonttools/Tests/designspaceLib/data/test_v5.designspace'
    DesignspaceEditorController(path)
