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
        * ToolbarTab: Axis              @axisTab
        > |---|                         @axisTable
        > * HorizontalStack             @axisActions  
        >> (+-)
        >> ( Add Weight Axis )
        >> ( Add Width )
        >> ( Add Axis ) 
        >> ( Add Optical Axis )        
        
        * ToolbarTab: Sources  @sourcesTab
        >|---|      @sourcesTable
        > * HorizontalStack         @sourcesActions
        >> (+-)
        >> ((( Open UFO | Add Open UFO's | Replace UFO )))        
        """
        marginDescriptions = dict(margins=(10, 0, 10, 10))
        helpDescriptions = dict(gravity="trailing")
        
        
        descriptionData = dict(
            axisTab=dict(
                image=designspaceBundle.getResourceImage("toolbar_30_30_icon_axes")
            ),
            sourcesTab=dict(
                image=designspaceBundle.getResourceImage("toolbar_30_30_icon_sources")
            ),
            axisActions=marginDescriptions,                        
            axisTable=dict(
                width="fill",
                height="fill",
                columnDescriptions = [
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
            axisHelp=helpDescriptions,
            
            sourcesActions=marginDescriptions,
            sourcesHelp=helpDescriptions
        )
        self.w = ezui.EZWindow(
            title="Title",
            content=content,
            descriptionData=descriptionData,
            size=(500, 400),
            minSize=(500, 400),
            controller=self,
            margins=0
        )
    
    def started(self):
        self.w.open()
    
    def axisListDoubleClickCallback(self, sender):
        print("axisListDoubleClickCallback")


Controller()    
