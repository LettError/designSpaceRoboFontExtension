import os
import weakref
import AppKit

import vanilla

from fontTools import designspaceLib
import ufoProcessor

from mojo.UI import CodeEditor
from mojo.events import postEvent
from mojo.subscriber import WindowController
from mojo.extensions import getExtensionDefault, ExtensionBundle
from mojo.roboFont import AllFonts, OpenFont

from lib.tools.debugTools import ClassNameIncrementer
from lib.tools.misc import coalescingDecorator
from lib.cells.doubleClickCell import RFDoubleClickCell

from designspaceProblems import DesignSpaceChecker

from designspaceEditor.designspaceLexer import DesignspaceLexer, TextLexer
from designspaceEditor.parsers import mapParser, rulesParser, labelsParser, glyphNameParser
from designspaceEditor.parsers.parserTools import numberToSTring
from designspaceEditor.tools import holdRecursionDecorator, addToolTipForColumn, TryExcept, HoldChanges


designspaceBundle = ExtensionBundle("DesignspaceEditor2")


registeredAxisTags = [
    ("italic", "ital"),
    ("optical", "opsz"),
    ("slant", "slnt"),
    ("width", "wdth"),
    ("weight", "wght"),
]


preferredAxes = [
    ("weight", "wght", 0, 1000, 0),
    ("width", "wdth", 0, 1000, 0),
    ("optical", "opsz", 3, 1000, 16),
    # ("italic", "ital", 0, 0, 1),  # must be a discrete axis
    # ("slant", "slnt", -90, 0, 90),
]

numberFormatter = AppKit.NSNumberFormatter.alloc().init()
numberFormatter.setNumberStyle_(AppKit.NSNumberFormatterDecimalStyle)
numberFormatter.setAllowsFloats_(True)

checkSymbol = "✓"
defaultSymbol = "🔹"
dotSymbol = "⚬"

try:
    infoImage = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_("info.circle.fill", None)
except Exception:
    # older systems
    infoImage = AppKit.NSImage.imageNamed_(AppKit.NSImageNameInfo)


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
            print(f"Duplicate axis: '{value}'")

    def axisTag(self):
        return self.axisDescriptor.tag

    def setAxisTag_(self, value):
        self.axisDescriptor.tag = str(value)

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
            return " ".join([numberToSTring(value) for value in self.axisDescriptor.values])
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

    def __init__(self, listView, closeCallback=None):
        tableView = listView.getNSTableView()
        index = listView.getSelection()[0]
        item = listView[index]
        relativeRect = tableView.rectOfRow_(index)
        self.closeCallback = closeCallback
        self.popover = self.popover = vanilla.Popover((400, 300))
        self.build(item)
        self.popover.bind("will close", self.popoverWillCloseCallback)
        self.popover.open(parentView=tableView, preferredEdge='bottom', relativeRect=relativeRect)

    def popoverWillCloseCallback(self, sender):
        self.close()
        if self.closeCallback is not None:
            if isinstance(self.closeCallback, (list, tuple)):
                for callback in self.closeCallback:
                    callback()
            else:
                self.closeCallback()

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

        self.popover.tabs = vanilla.Tabs((0, 15, -0, -0), ["Map", "Labels"])

        self.axisMap = self.popover.tabs[0]
        self.axisLabels = self.popover.tabs[1]

        self.axisMap.editor = CodeEditor(
            (10, 10, -10, -10),
            mapParser.dumpMap(self.axisDescriptor.map),
            lexer=DesignspaceLexer(),
            showLineNumbers=False
        )

        self.axisLabels.editor = CodeEditor(
            (10, 10, -10, -10),
            labelsParser.dumpAxisLabels(self.axisDescriptor.labelNames, self.axisDescriptor.axisLabels),
            lexer=DesignspaceLexer(),
            showLineNumbers=False
        )

    def close(self):
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
            showLineNumbers=False
        )

        self.sourceMutedGlyphNames.editor = CodeEditor(
            (10, 10, -10, -10),
            glyphNameParser.dumpGlyphNames(self.sourceDescriptor.mutedGlyphNames),
            lexer=TextLexer(),
            showLineNumbers=False
        )

    def close(self):
        labels, _ = labelsParser.parseAxisLabels(self.sourceLocalisedFamilyName.editor.get())
        self.sourceDescriptor.localisedFamilyName = labels
        self.sourceDescriptor.mutedGlyphNames = glyphNameParser.parseGlyphNames(self.sourceMutedGlyphNames.editor.get())


class DesignspaceEditorController(WindowController):

    def __init__(self, path=None):
        self.holdChanges = HoldChanges()
        with self.holdChanges:
            super().__init__()
            self.load(path)

    def build(self):
        self.document = ufoProcessor.DesignSpaceProcessor()

        self.w = vanilla.Window((850, 500), "Designspace Editor", minSize=(720, 400))
        self.w.vanillaWrapper = weakref.ref(self)
        self.w.bind("should close", self.windowShouldClose)

        self.tabItems = ["Axes", "Sources", "Instances", "Rules", "Labels", "Problems"]
        self.w.tabs = vanilla.Tabs((0, 0, 0, 0), self.tabItems, showTabs=False)

        self.axes = self.w.tabs[0]
        self.sources = self.w.tabs[1]
        self.instances = self.w.tabs[2]
        self.rules = self.w.tabs[3]
        self.labels = self.w.tabs[4]
        self.problems = self.w.tabs[5]

        toolbarItems = [dict(
            itemIdentifier=tabItem.lower(),
            label=tabItem,
            callback=self.toolbarSelectTab,
            imageObject=designspaceBundle.getResourceImage(f"toolbar_icon_{tabItem.lower()}"),
            selectable=True,
        ) for tabItem in self.tabItems]

        toolbarItems.extend([
            dict(
                itemIdentifier="save",
                label="Save",
                callback=self.toolbarSave,
                imageObject=designspaceBundle.getResourceImage("toolbar_icon_save"),
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
            #     imageObject=designspaceBundle.getResourceImage("toolbar_icon_settings"),
            # ),
        ])
        self.w.addToolbar("DesignSpaceToolbar", toolbarItems)

        # AXES
        axesToolsSsegmentDescriptions = [
            dict(title="+", width=20),
            dict(title="-", width=20),
        ]
        axesToolsSsegmentDescriptions.extend([dict(title=f"Add {preferredAxis[0].title()} Axis") for preferredAxis in preferredAxes])

        self.axes.tools = vanilla.SegmentedButton(
            (10, 5, 400, 22),
            selectionStyle="momentary",
            callback=self.axisToolsCallback,
            segmentDescriptions=axesToolsSsegmentDescriptions
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
            dragSettings=dict(type="sourcesListDragAndDropType", callback=self.dragCallback),
            selfDropSettings=dict(type="sourcesListDragAndDropType", operation=AppKit.NSDragOperationMove, callback=self.dropCallback),
        )
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
            dict(title="Add Open UFO's"),
            # dict(title="Load Names"),
            dict(title="Replace UFO")
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
            otherApplicationDropSettings=dict(type=AppKit.NSFilenamesPboardType, operation=AppKit.NSDragOperationCopy, callback=self.sourcesListDropCallback),
        )
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
            dict(title="Add Sources as Instances"),
            dict(title="Generate with MutatorMath"),
            dict(title="Generate with VarLib")
        ]
        self.instances.editorTools = vanilla.SegmentedButton(
            (72, 5, 570, 22),
            selectionStyle="momentary",
            callback=self.instancesEditorToolsCallback,
            segmentDescriptions=instancesEditorToolsSsegmentDescriptions
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
        )

        # RULES
        self.rules.editor = CodeEditor((0, 0, 0, 0), lexer=DesignspaceLexer(), showLineNumbers=False, callback=self.rulesEditorCallback)

        # LABELS
        self.labels.editor = CodeEditor((0, 0, 0, 0), lexer=DesignspaceLexer(), showLineNumbers=False, callback=self.locationLabelsEditorCallback)

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

        # self.w.tabs.set(3)
        self.w.getNSWindow().toolbar().setSelectedItemIdentifier_("axes")

    def started(self):
        postEvent("designspaceEditorWillOpenDesignspace", designspace=self.document)
        self.w.open()
        postEvent("designspaceEditorDidOpenDesignspace", designspace=self.document)

    def load(self, path):
        if path is not None:
            fileName = os.path.basename(path)
            try:
                self.document.read(path)
            except Exception as e:
                self.showMessage(
                    "DesignSpaceEdit can't open this file",
                    informativeText=f"Error reading {fileName}.\n{e}."
                )

            self.axes.list.set([AxisListItem(axisDescriptor, self) for axisDescriptor in self.document.axes])
            self.sources.list.set([self.wrapSourceDescriptor(sourceDescriptor) for sourceDescriptor in self.document.sources])
            self.instances.list.set([self.wrapInstanceDescriptor(instanceDescriptor) for instanceDescriptor in self.document.instances])
            self.rules.editor.set(rulesParser.dumpRules(self.document.rules))
            self.labels.editor.set(labelsParser.dumpLocationLabels(self.document.locationLabels))

            self.setWindowTitleFromPath(path)
            self.updateColumnHeadersFromAxes()

    # AXES

    def axisToolsCallback(self, sender):
        value = sender.get()
        if value == 1:
            # remove
            for index in reversed(self.axes.list.getSelection()):
                item = self.axes.list[index]
                self.document.axes.remove(item.axisDescriptor)
                self.axes.list.remove(item)
        else:
            if value == 0:
                # add
                name = f"newAxis{len(self.document.axes) + 1}"
                tag = f"nwx{len(self.document.axes) + 1}"
                minimum = 0
                maximum = 1000
                default = 0
            else:
                name, tag, minimum, maximum, default = preferredAxes[value - 2]

            if self.validateAxisName(name):
                axisDescriptor = self.document.writerClass.axisDescriptorClass()
                axisDescriptor.name = name
                axisDescriptor.tag = tag
                axisDescriptor.minimum = minimum
                axisDescriptor.maximum = maximum
                axisDescriptor.default = default
                self.document.axes.append(axisDescriptor)
                self.axes.list.append(AxisListItem(axisDescriptor, self))
            else:
                print(f"Duplicate axis: '{name}'")

        self.setDocumentNeedSave(True)
        self.updateColumnHeadersFromAxes()
        # TODO self.updateLocations()

    def axisListDoubleClickCallback(self, sender):
        self.axisPopover = AxisAttributesPopover(self.axes.list, closeCallback=self.setDocumentNeedSave)

    def axesListEditCallback(self, sender):
        self.setDocumentNeedSave(True)

    # SOURCES

    def sourcesToolsCallback(self, sender):

        def addSourceCallback(paths):
            for path in paths:
                self.addSourceFromPath(path)
            # TODO self.enableInstanceList()
            # TODO  self.updatePaths()

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
                self.document.sources.remove(item["object"])
                self.sources.list.remove(item)

    def sourcesEditorToolsCallback(self, sender):
        value = sender.get()
        if value == 0:
            # Open UFO
            self.openSelectedItem(self.sources.list)
        elif value == 1:
            # Add Open UFO's
            existingSourcePaths = [sourceDescriptor.path for sourceDescriptor in self.document.sources]
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
                        if self.document.path is not None:
                            sourceDescriptor.filename = os.path.relpath(font.path, os.path.dirname(self.document.path))
                        else:
                            sourceDescriptor.filename = font.path
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
                    messageText="Cannot replace source UFO's",
                    informativeText="Selection only one source item to be replace"
                )

    def addSourceFromPath(self, path):
        font = OpenFont(path, showInterface=False)
        self.addSourceFromFont(font)

    def addSourceFromFont(self, font):
        defaults = {}
        for axisDescriptor in self.document.axes:
            defaults[axisDescriptor.name] = axisDescriptor.default
        sourceDescriptor = self.document.writerClass.sourceDescriptorClass()
        sourceDescriptor.path = font.path
        if self.document.path is not None:
            sourceDescriptor.filename = os.path.relpath(font.path, os.path.dirname(self.document.path))
        else:
            sourceDescriptor.filename = font.path
        sourceDescriptor.familyName = font.info.familyName
        sourceDescriptor.styleName = font.info.styleName
        sourceDescriptor.location.update(defaults)

        self.document.addSource(sourceDescriptor)
        self.sources.list.append(self.wrapSourceDescriptor(sourceDescriptor))
        self.setDocumentNeedSave(True)

    def wrapSourceDescriptor(self, sourceDescriptor):
        wrapped = dict(
            sourceHasPath=checkSymbol if sourceDescriptor.path and os.path.exists(sourceDescriptor.path) else "",
            sourceIsDefault=defaultSymbol if sourceDescriptor == self.document.findDefault() else "",
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
        for axis in self.document.axes:
            sourceDescriptor.location[axis.name] = wrappedSourceDescriptor.get(f"axis_{axis.name}", axis.default)
        return sourceDescriptor

    def sourcesListDoubleClickCallback(self, sender):
        self.sourcePopover = SourceAttributesPopover(self.sources.list, closeCallback=[self.updateSources, self.setDocumentNeedSave])

    def sourcesListEditCallback(self, sender):
        self.updateSources()
        self.setDocumentNeedSave(True)

    def sourcesListDropCallback(self, sender, dropInfo):
        isProposal = dropInfo["isProposal"]
        existingUFOPaths = [sourceDescriptor.path for sourceDescriptor in self.document.sources]

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
        value = sender.get()
        if value == 0:
            # add
            if self.document.instances:
                familyName = self.document.instances[0].familyName
            elif self.document.sources:
                familyName = self.document.sources[0].familyName
            else:
                familyName = "NewFamily"
            styleName = f"Style_{len(self.document.instances)}"
            instanceDescriptor = self.document.addInstanceDescriptor(
                familyName=familyName,
                designLocation=self.document.newDefaultLocation(),
                styleName=styleName,
                filename=os.path.join(getExtensionDefault('instanceFolderName', 'instances'), f"{familyName}-{styleName}.ufo")
            )
            self.instances.list.append(self.wrapInstanceDescriptor(instanceDescriptor))
        elif value == 1:
            # remove
            for index in reversed(self.instances.list.getSelection()):
                item = self.instances.list[index]
                self.document.instances.remove(item["object"])
                self.instances.list.remove(item)
        self.setDocumentNeedSave(True)

    def wrapInstanceDescriptor(self, instanceDescriptor):
        wrapped = dict(
            instanceUFOFileName=instanceDescriptor.filename if instanceDescriptor.filename is not None else os.path.join(getExtensionDefault('instanceFolderName', 'instances'), f"{instanceDescriptor.familyName}-{instanceDescriptor.styleName}.ufo"),
            instanceFamilyName=instanceDescriptor.familyName or "",
            instanceStyleName=instanceDescriptor.styleName or "",
            object=instanceDescriptor
        )
        for axis, value in instanceDescriptor.designLocation.items():
            if isinstance(value, tuple):
                # with anisotropic coordinates take the the horizontal one
                value = value[0]
            wrapped[f"axis_{axis}"] = value
        return wrapped

    def unwrapInstanceDescriptor(self, wrappedInstanceDescriptor):
        instanceDescriptor = wrappedInstanceDescriptor["object"]
        instanceDescriptor.familyName = wrappedInstanceDescriptor["instanceFamilyName"]
        instanceDescriptor.styleName = wrappedInstanceDescriptor["instanceStyleName"]
        for axis in self.document.axes:
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
                newInstanceDescriptor = self.document.addInstanceDescriptor(**instanceDescriptor.asdict())
                self.instances.list.append(self.wrapInstanceDescriptor(newInstanceDescriptor))
        elif value == 1:
            # Add Sources as Instances
            existingLocations = [instanceDescriptor.designLocation for instanceDescriptor in self.document.instances]
            for sourceDescriptor in self.document.sources:
                if sourceDescriptor.location not in existingLocations:
                    newInstanceDescriptor = self.document.addInstanceDescriptor(
                        familyName=sourceDescriptor.familyName,
                        styleName=sourceDescriptor.styleName,
                        designLocation=sourceDescriptor.location,
                        filename=os.path.join(getExtensionDefault('instanceFolderName', 'instances'), f"{sourceDescriptor.familyName}-{sourceDescriptor.styleName}.ufo")
                    )
                    self.instances.list.append(self.wrapInstanceDescriptor(newInstanceDescriptor))

        elif value in (2, 3):
            # Generate with MutatorMath or VarLib
            if self.document.path is None:
                self.showMessage("Save the designspace first.", "Instances are generated in a relative path next to the designspace file.")
            else:
                self.document.useVarlib = value == 3
                self.document.roundGeometry = True
                self.document.loadFonts()
                self.document.findDefault()
                selection = self.instances.list.getSelection()
                if selection:
                    items = [self.instances.list[index] for index in selection]
                else:
                    items = self.instances.list
                for item in items:
                    instanceDescriptor = item["object"]
                    with TryExcept(self, "Generate Instance"):
                        font = self.document.makeInstance(instanceDescriptor)
                        if not os.path.exists(os.path.dirname(instanceDescriptor.path)):
                            os.makedirs(os.path.dirname(instanceDescriptor.path))
                        font.save(path=instanceDescriptor.path)

    def instancesListEditCallback(self, sender):
        self.setDocumentNeedSave(True)

    # rules

    @coalescingDecorator(delay=0.2)
    def rulesEditorCallback(self, sender):
        rules = rulesParser.parseRules(sender.get(), self.document.writerClass.ruleDescriptorClass)
        self.document.rules = rules
        self.setDocumentNeedSave(True)

    # labels

    @coalescingDecorator(delay=0.2)
    def locationLabelsEditorCallback(self, sender):
        locationLabels = labelsParser.parseLocationLabels(sender.get(), self.document.writerClass.locationLabelDescriptorClass)
        self.document.locationLabels = locationLabels
        self.setDocumentNeedSave(True)

    # problems

    def problemsToolsCallback(self, sender):
        value = sender.get()
        if value == 0:
            # validate
            self.validate()

    def validate(self):
        # validate with the designspaceProblems checker
        checker = DesignSpaceChecker(self.document)
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
        item = sender[rowIndex]

        def menuCallback(sender):
            item[columnIdentifier] = float(sender.title())

        def sliderCallback(sender):
            item[columnIdentifier] = sender.get()

        menu = []
        for axisDescriptor in self.document.axes:
            if axisDescriptor.name == axisName:
                if hasattr(axisDescriptor, "values"):
                    menu.extend([dict(title=numberToSTring(value), callback=menuCallback) for value in axisDescriptor.values])
                else:
                    menu.append(dict(title=numberToSTring(axisDescriptor.minimum), callback=menuCallback))
                    if axisDescriptor.minimum != axisDescriptor.default and axisDescriptor.maximum != axisDescriptor.default:
                        menu.append(dict(title=numberToSTring(axisDescriptor.default), callback=menuCallback))
                    menu.append(dict(title=numberToSTring(axisDescriptor.maximum), callback=menuCallback))
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

        return menu

    def convertAxisTo(self, axisDescriptor, destinationClass, **kwargs):
        index = self.document.axes.index(axisDescriptor)
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
        self.document.axes[index] = newAxisDescriptor
        return newAxisDescriptor

    def convertContinuousAxisToDiscreteAxis(self, axisDescriptor):
        return self.convertAxisTo(
            axisDescriptor,
            self.document.writerClass.discreteAxisDescriptorClass
        )

    def convertDiscreteAxisToContinuousAxis(self, axisDescriptor):
        return self.convertAxisTo(
            axisDescriptor,
            self.document.writerClass.axisDescriptorClass,
            minimum=min(0, axisDescriptor.default),
            maximum=max(1000, axisDescriptor.default)
        )

    def openSelectedItem(self, listObject):
        selection = listObject.getSelection()
        if selection:
            progress = self.startProgress("Opening UFO...", len(selection))
            for index in selection:
                item = listObject[index]
                descriptor = item["object"]
                path = descriptor.path
                if path is None:
                    continue
                try:
                    OpenFont(path, showInterface=True)
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

    def setDocumentNeedSave(self, state=True):
        if self.holdChanges:
            return
        if state:
            postEvent("designspaceEditorDidChange", designspace=self.document)
            self.w.getNSWindow().setDocumentEdited_(True)
        else:
            self.w.getNSWindow().setDocumentEdited_(False)

    def setWindowTitleFromPath(self, path):
        self.w.getNSWindow().setRepresentedURL_(AppKit.NSURL.fileURLWithPath_(path))
        self.w.setTitle(os.path.basename(path))

    def updateColumnHeadersFromAxes(self):
        for listObject in [self.sources.list, self.instances.list]:
            tableView = listObject.getNSTableView()
            for column in tableView.tableColumns():
                if column.identifier().startswith("axis_"):
                    tableView.removeTableColumn_(column)

            for axis in self.document.axes:
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
                cell.setFormatter_(numberFormatter)

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
        for axisDescriptor in self.document.axes:
            if axisDescriptor.name == name:
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
            # so we have the path for this document
            # we need to make sure the sources and instances are all in the right place
            root = os.path.dirname(path)
            for wrappedSourceDescriptor in self.sources.list:
                sourceDescriptor = self.unwrapSourceDescriptor(wrappedSourceDescriptor)
                sourceDescriptor.filename = os.path.relpath(sourceDescriptor.path, root)
            for wrappedInstanceDescriptor in self.instances.list:
                instanceDescriptor = self.unwrapInstanceDescriptor(wrappedInstanceDescriptor)
                instanceDescriptor.path = os.path.abspath(os.path.join(root, instanceDescriptor.filename))

            # TODO self.document.lib[self.mathModelPrefKey] = self.mathModelPref
            self.document.write(path)
            self.updateSources()
            self.setWindowTitleFromPath(path)
            self.setDocumentNeedSave(False)

        if len(self.document.axes) == 0:
            self.showMessage(
                messageText="No axes defined!",
                informativeText="The designspace needs at least one axis before saving."
            )

        elif self.document.path is None or AppKit.NSEvent.modifierFlags() & AppKit.NSAlternateKeyMask:
            # check if w have defined any axes
            # can't save without axes
            # get a filepath first
            sourcePaths = set([os.path.dirname(source.path) for source in self.document.sources if source.path])
            saveToDir = None
            if sourcePaths:
                saveToDir = sorted(sourcePaths)[0]

            self.showPutFile(
                messageText="Save designspace:",
                directory=saveToDir,
                canCreateDirectories=True,
                fileTypes=['designspace'],
                callback=saveDesignspace
            )
        else:
            saveDesignspace(self.document.path)

    def toolbarSettings(self, sender):
        pass


if __name__ == '__main__':
    pathForBundle = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    designspaceBundle = ExtensionBundle(path=pathForBundle)

    path = "/Users/frederik/Documents/dev/JustVanRossum/fontgoggles/Tests/data/MutatorSans/MutatorSans.designspace"
    path = '/Users/frederik/Documents/dev/fonttools/Tests/designspaceLib/data/test_v4_original.designspace'
    #path = "/Users/frederik/Desktop/designSpaceEditorText/testFiles/Untitled.designspace"
    path = None
    #path = '/Users/frederik/Documents/dev/fonttools/Tests/designspaceLib/data/test_v5.designspace'
    DesignspaceEditorController(path)
