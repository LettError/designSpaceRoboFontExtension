import AppKit
import ezui

from lib.cells.doubleClickCell import RFDoubleClickCell

from mojo.extensions import getExtensionDefault, ExtensionBundle


designspaceBundle = ExtensionBundle("DesignspaceEditor2")

numberFormatter = AppKit.NSNumberFormatter.alloc().init()
numberFormatter.setNumberStyle_(AppKit.NSNumberFormatterDecimalStyle)
numberFormatter.setAllowsFloats_(True)
numberFormatter.setLocalizesFormat_(False)
numberFormatter.setUsesGroupingSeparator_(False)

infoImage = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_("info.circle.fill", None)


def doubleClickCell(callback, image=None):
    cell = RFDoubleClickCell.alloc().init()
    cell.setDoubleClickCallback_(callback)
    cell.setImage_(image)
    return cell


class Controller(ezui.WindowController):

    def build(self):
        content = """
        = ToolbarTabs
        * ToolbarTab: Axis                  @axisTab
        > |---|                             @axisTable
        > * HorizontalStack                 @axisStack
        >> (+-)
        >> (...)                            @axisActions

        * ToolbarTab: Sources               @sourcesTab
        >|---|                              @sourcesTable
        > * HorizontalStack                 @sourcesStack
        >> (+-)
        >> (...)                            @sourcesActions

        * ToolbarTab: Intances              @instancesTab
        > |---|                             @instancesTable
        > * HorizontalStack                 @instancesStack
        >> (+-)
        >> ( Preview Instances )            @instancesPreview
        >> (...)                            @instancesActions

        * ToolbarTab: Rules                 @rulesTab
        > * CodeEditor                      @rulesEditor

        * ToolbarTab: Labels                @labelsTab
        > * CodeEditor                      @labelsEditor
        > * HorizontalStack                 @labelsStack
        >> ( Preview Labels )               @labelsPreviewButton


        * ToolbarTab: Problems              @problemsTab
        > |---|                             @problemsTable
        > * HorizontalStack                 @problemsStack
        >> ( Validate Designspace )         @problemsValidateButton

        * ToolbarTab: Notes                 @notesTab
        > [[__]]                            @notesEditor
        """

        marginDescriptions = dict(margins=(10, 0, 10, 10))
        descriptionData = dict(
            axisTab=dict(
                image=designspaceBundle.getResourceImage("toolbar_30_30_icon_axes")
            ),
            axisStack=marginDescriptions,
            axisTable=dict(
                width="fill",
                height="fill",
                columnDescriptions=[
                    dict(title="", identifier="genericInfoButton", width=20, editable=False, cell=doubleClickCell(self.axisListDoubleClickCallback, infoImage)),#, cell=axisDoubleClickCell),
                    dict(title="Ⓡ", identifier="axisRegisterd", width=20, allowsSorting=False, editable=False),
                    dict(title="Name", identifier="axisName", allowsSorting=False, editable=True),
                    dict(title="Tag", identifier="axisTag", width=70, allowsSorting=False, editable=True),
                    dict(title="Minimum", identifier="axisMinimum", width=70, allowsSorting=False, editable=True, formatter=numberFormatter),
                    dict(title="Default", identifier="axisDefault", width=70, allowsSorting=False, editable=True, formatter=numberFormatter),
                    dict(title="Maximum", identifier="axisMaximum", width=70, allowsSorting=False, editable=True, formatter=numberFormatter),
                    dict(title="Discrete Values", identifier="axisDiscreteValues", width=100, allowsSorting=False, editable=True),

                    dict(title="Hidden", identifier="axisHidden", width=50, cellType="Checkbox", allowsSorting=False, editable=True),
                    dict(title="📈", identifier="axisHasMap", width=20, allowsSorting=False, editable=False),
                    dict(title="🏷️", identifier="axisHasLabels", width=20, allowsSorting=False, editable=False),
                ]
            ),
            axisActions=dict(
                itemDescriptions=[
                    dict(identifier="axisAddWeightAxis", text="Add Weight Axis"),
                    dict(identifier="axisAddWidthAxis", text="Add Width Axis"),
                    dict(identifier="axisAddOpticalAxis", text="Add Optical Axis"),
                ]
            ),

            sourcesTab=dict(
                image=designspaceBundle.getResourceImage("toolbar_30_30_icon_sources")
            ),
            sourcesStack=marginDescriptions,
            sourcesTable=dict(
                width="fill",
                height="fill",
                columnDescriptions=[
                    dict(title="", identifier="genericInfoButton", width=20, editable=False, cell=doubleClickCell(self.sourceListDoubleClickCallback, infoImage)),
                    dict(title="💾", identifier="sourceHasPath", width=20, editable=False),
                    dict(title="📍", identifier="sourceIsDefault", width=20, editable=False),
                    dict(title="UFO", identifier="sourceUFOFileName", width=200, minWidth=100, maxWidth=350, editable=False),
                    dict(title="Family Name", identifier="sourceFamilyName", editable=True, width=130, minWidth=130, maxWidth=250),
                    dict(title="Style Name", identifier="sourceStyleName", editable=True, width=130, minWidth=130, maxWidth=250),
                    dict(title="Layer Name", identifier="sourceLayerName", editable=True, width=130, minWidth=130, maxWidth=250),
                    dict(title="🌐", identifier="sourceHasLocalisedFamilyNames", width=20, allowsSorting=False, editable=False),
                    dict(title="🔕", identifier="sourceHasMutedGlyphs", width=20, allowsSorting=False, editable=False),
                ]
            ),
            sourcesActions=dict(
                itemDescriptions=[
                    dict(identifier="basicItem", text="Open source UFO"),
                    "----",
                    dict(identifier="basicItem", text="Add Open UFOs"),
                    dict(identifier="basicItem", text="Replace UFO"),
                ]
            ),

            instancesTab=dict(
                image=designspaceBundle.getResourceImage("toolbar_30_30_icon_instances")
            ),
            instancesStack=marginDescriptions,
            instancesTable=dict(
                width="fill",
                height="fill",
                columnDescriptions=[
                    dict(title="UFO", identifier="instanceUFOFileName", width=200, minWidth=100, maxWidth=350, editable=False),
                    dict(title="Family Name", identifier="instanceFamilyName", editable=True, width=130, minWidth=130, maxWidth=250),
                    dict(title="Style Name", identifier="instanceStyleName", editable=True, width=130, minWidth=130, maxWidth=250),
                ]
            ),
            instancesActions=dict(
                itemDescriptions=[
                    dict(identifier="basicItem", text="Duplicate Instance"),
                    dict(identifier="basicItem", text="Add Sources as Instances"),
                    "----",
                    dict(identifier="basicItem", text="Generate With MutatorMath"),
                    dict(identifier="basicItem", text="Generate With VarLib"),
                ]
            ),

            rulesTab=dict(
                image=designspaceBundle.getResourceImage("toolbar_30_30_icon_rules")
            ),
            rulesEditor=dict(
                width="fill",
                height="fill",
                showLineNumbers=False
            ),

            labelsTab=dict(
                image=designspaceBundle.getResourceImage("toolbar_30_30_icon_labels")
            ),
            labelsStack=marginDescriptions,
            labelsEditor=dict(
                width="fill",
                height="fill",
                showLineNumbers=False
            ),
            labelsActions=dict(
                itemDescriptions=[
                    dict(identifier="basicItem", text="Preview Labels"),
               ]
            ),

            problemsTab=dict(
                image=designspaceBundle.getResourceImage("toolbar_30_30_icon_problems")
            ),
            problemsStack=marginDescriptions,
            problemsTable=dict(
                width="fill",
                height="fill",
                columnDescriptions = [
                    dict(title="", identifier="problemIcon", width=20),
                    dict(title="Where", identifier="problemClass", width=130),
                    dict(title="What", identifier="problemDescription", minWidth=200, width=200, maxWidth=1000),
                    dict(title="Specifically", identifier="problemData", minWidth=200, width=200, maxWidth=1000),
                ]
            ),

            notesTab=dict(
                image=designspaceBundle.getResourceImage("toolbar_30_30_icon_notes")
            ),
            notesEditor=dict(
                width="fill",
                height="fill",
            ),


        )
        self.w = ezui.EZWindow(
            title="Title",
            content=content,
            descriptionData=descriptionData,
            size=(800, 500),
            minSize=(800, 500),
            controller=self,
            margins=0
        )

        self.w.addToolbarItem(dict(itemIdentifier=AppKit.NSToolbarSpaceItemIdentifier))
        self.w.addToolbarItem(dict(
            itemIdentifier="save",
            label="Save",
            imageObject=ezui.makeImage(symbolName="square.and.arrow.down", symbolConfiguration=dict(renderingMode="hierarchical", colors=[(1, 0, 1, 1), ])),
            callback=self.toobarSaveCallback
        ))
        self.w.addToolbarItem(dict(
            itemIdentifier="help",
            label="Help",
            imageObject=ezui.makeImage(symbolName="questionmark.circle", symbolConfiguration=dict(renderingMode="hierarchical", colors=[(1, 0, 1, 1), ])),
            callback=self.toolbarHelpCallback
        ))

    def started(self):
        self.w.open()

    # axis

    def axisListDoubleClickCallback(self, sender):
        print("axisListDoubleClickCallback")

    def axisAddWeightAxisCallback(self, sender):
        print("axisAddWeightAxisCallback")

    def axisAddWidthAxisCallback(self, sender):
        print("axisAddWidthAxisCallback")

    def axisAddOpticalAxisCallback(self, sender):
        print("axisAddOpticalAxisCallback")

    # sources

    def sourceListDoubleClickCallback(self, sender):
        print("sourceListDoubleClickCallback")

    # instances


    # toolbar

    def toobarSaveCallback(self, sender):
        print("save")

    def toolbarHelpCallback(self, sender):
        print("help")


Controller()
