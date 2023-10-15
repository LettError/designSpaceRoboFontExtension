import vanilla
from mojo.UI import MultiLineView, splitText, GlyphRecord
from mojo.subscriber import WindowController, Subscriber

from mojo.roboFont import RFont, RGlyph, internalFontClasses

from designspaceEditor.tools import UseVarLib
from mutatorMath import Location

skateboardPreviewTextLibKey = "com.letterror.skateboard.previewText"
previewTextLibKey = "com.letterror.designspaceEditor.previewText"


class InstancesPreview(Subscriber, WindowController):

    debug = True

    def build(self, operator=None, selectedInstances=None, previewString=None):
        self.operator = operator

        dummyFont = RFont(showInterface=False)

        upms = set()
        with UseVarLib(self.operator, useVarLib=False):
            for instance in self.operator.instances:
                #continuousLocation, discreteLocation = self.operator.splitLocation(instance.location)
                #infoMutator = self.operator.getInfoMutator(discreteLocation)
                #info = infoMutator.makeInstance(continuousLocation)
                info = self.operator.makeOneInfo(instance.getFullDesignLocation(self.operator))
                upms.add(info.unitsPerEm)

        dummyFont.info.unitsPerEm = max(upms) if upms else 1000

        self.displayPrefs = {}
        self.displayPrefs['Inverse'] = True
        self.displayPrefs['Beam'] = False
        self.displayPrefs['displayMode'] = "Multi Line"
        self.displayPrefs['Stroke'] = False
        self.displayPrefs['Fill'] = True

        self.w = vanilla.FloatingWindow((700, 400), "Instances Preview", minSize=(500, 300))
        self.w.input = vanilla.EditText((10, 10, -170, 22), callback=self.inputCallback)
        self.w.singleLine = vanilla.CheckBox((-100, 10, 100, 22), "Single line", value=False, callback=self.singleLineCheckboxCallback)
        self.w.invert = vanilla.CheckBox((-160, 10, 60, 22), "Invert", value=self.displayPrefs['Inverse'], callback=self.colorModeCallback)
        self.w.hl = vanilla.HorizontalLine((0, 41, 0, 1))
        self.w.preview = MultiLineView((0, 42, 0, -22), 
            pointSize=60, 
            displayOptions=self.displayPrefs,
            selectionCallback=self.previewSelectionCallback
            )
        self.w.infoText = vanilla.TextBox((10,-21,-10,22), "DSE2")
        self.w.preview.setFont(dummyFont)
        self.selectedInstances = selectedInstances or []

        if previewString is None:
            # check if there is an old skateboard previewtext
            if skateboardPreviewTextLibKey in self.operator.lib:
                previewString = self.operator.lib[previewTextLibKey] = self.operator.lib[skateboardPreviewTextLibKey]
                del self.operator.lib[skateboardPreviewTextLibKey]
            else:
                previewString = self.operator.lib.get(previewTextLibKey, "Abc")
        self.setPreviewString(previewString)

    def started(self):
        self.w.open()

    def destroy(self):
        self.operator = None
        self.selectedInstances = None

    def setPreviewString(self, value):
        self.w.input.set(value)
        self.updatePreview()

    def updatePreview(self):
        self.inputCallback(self.w.input)

    def inputCallback(self, sender):
        previewString = sender.get()
        self.operator.lib[previewTextLibKey] = previewString
        glyphNames = splitText(previewString, self.operator.getCharacterMapping())
        glyphRecords = []
        possibleKerningPairs = ((side1, side2) for side1, side2 in zip(glyphNames[:-1], glyphNames[1:]))
        possibleKerningPairs = list(possibleKerningPairs)
        if not self.selectedInstances:
            self.selectedInstances = self.operator.instances

        with UseVarLib(self.operator, useVarLib=False):
            for instance in self.selectedInstances:
                previousGlyphName = None
                fullDesignLocation = instance.getFullDesignLocation(self.operator)
                kerningObject = self.operator.makeOneKerning(fullDesignLocation, pairs=possibleKerningPairs)
                for glyphName in glyphNames:
                    # do not bend, reasoning: the instance locations are in designspace values.
                    mathGlyph = self.operator.makeOneGlyph(glyphName, fullDesignLocation, decomposeComponents=True)
                    if mathGlyph is not None:
                        dest = internalFontClasses.createGlyphObject()
                        mathGlyph.extractGlyph(dest)
                        dest.lib['designLocation'] = Location(fullDesignLocation).asString()
                        
                        glyphRecord = GlyphRecord(dest)

                        if previousGlyphName and glyphRecords:
                            glyphRecords[-1].xAdvance = kerningObject.get((previousGlyphName, glyphName))
                            #print("\t\tkerningObject.get((previousGlyphName, glyphName))", (previousGlyphName, glyphName), kerningObject.get((previousGlyphName, glyphName)))

                        glyphRecords.append(glyphRecord)

                    previousGlyphName = glyphName

                glyphRecords.append(GlyphRecord(self.w.preview.createNewLineGlyph()))

        self.w.preview.setGlyphRecords(glyphRecords)

    designspaceEditorInstancesDidChangeDelay = 0.1

    def previewSelectionCallback(self, sender):
        selection = self.w.preview.getSelectedGlyph()
        if selection:
            selection.removeOverlap()
            self.w.infoText.set(f"loc: {selection.lib['designLocation']}\tglyph: {selection.name}\twidth: {selection.width:3.1f}\tarea: {selection.area:3.1f}")
        else:
            self.w.infoText.set("DSE2")

    def colorModeCallback(self, sender):
        choice = sender.get()
        if choice == 0:
            self.displayPrefs['Inverse'] = False
        elif choice == 1:
            self.displayPrefs['Inverse'] = True
        self.w.preview.setDisplayStates(self.displayPrefs)

    def singleLineCheckboxCallback(self, sender):
        if not sender.get():
            self.w.preview.setDisplayStates(dict(displayMode="Multi Line"))
        else:
            self.w.preview.setDisplayStates(dict(displayMode="Single Line"))

    def designspaceEditorInstancesDidChange(self, notification):
        self.updatePreview()

    def designspaceEditorSourcesDidChanged(self, notification):
        self.updatePreview()

    def designspaceEditorAxesDidChange(self, notification):
        self.updatePreview()

    def designspaceEditorSourceGlyphDidChange(self, notification):
        self.updatePreview()

    def designspaceEditorInfoKerningDidChange(self, notification):
        self.updatePreview()

    def designspaceEditorSourceKerningDidChange(self, notification):
        self.updatePreview()

    def designspaceEditorGroupsKerningDidChange(self, notification):
        self.updatePreview()

    def designspaceEditorGroupsFontDidChangedExternally(self, notification):
        self.updatePreview()

    def designspaceEditorInstancesDidChangeSelection(self, notification):
        if self.operator == notification["designspace"]:
            self.selectedInstances = notification["selectedItems"]
            self.updatePreview()


if __name__ == '__main__':
    c = InstancesPreview(operator=CurrentDesignspace())
    c.setPreviewString("HELLOVAH")
