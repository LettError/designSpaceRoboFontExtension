import vanilla
from mojo.UI import MultiLineView, splitText, GlyphRecord
from mojo.subscriber import WindowController, Subscriber

from mojo.roboFont import RFont, RGlyph, internalFontClasses

from designspaceEditor.tools import UseVarLib


class InstancesPreview(Subscriber, WindowController):

    debug = True

    def build(self, operator=None, selectedInstances=None, previewString=""):
        self.operator = operator

        dummyFont = RFont(showInterface=False)

        upms = set()
        with UseVarLib(self.operator, useVarLib=False):
            for instance in self.operator.instances:
                #continuousLocation, discreteLocation = self.operator.splitLocation(instance.location)
                #infoMutator = self.operator.getInfoMutator(discreteLocation)
                #info = infoMutator.makeInstance(continuousLocation)
                info = self.operator.makeOneInfo(instance.location)
                upms.add(info.unitsPerEm)

        dummyFont.info.unitsPerEm = max(upms) if upms else 1000

        self.w = vanilla.FloatingWindow((700, 400), "Instances Preview", minSize=(500, 300))
        self.w.input = vanilla.EditText((10, 10, -120, 22), callback=self.inputCallback)
        self.w.singleLine = vanilla.CheckBox((-100, 10, 100, 22), "Single line", value=0, callback=self.singleLineCheckboxCallback)
        self.w.hl = vanilla.HorizontalLine((0, 41, 0, 1))
        self.w.preview = MultiLineView((0, 42, 0, 0), pointSize=60, displayOptions=dict(Beam=False, displayMode="Multi Line", Stroke=False, Fill=True))
        self.w.preview.setFont(dummyFont)
        self.selectedInstances = selectedInstances or []
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
        glyphNames = splitText(sender.get(), self.operator.getCharacterMapping())
        glyphRecords = []
        possibleKerningPairs = ((side1, side2) for side1, side2 in zip(glyphNames[:-1], glyphNames[1:]))
        possibleKerningPairs = list(possibleKerningPairs)
        if not self.selectedInstances:
            self.selectedInstances = self.operator.instances

        with UseVarLib(self.operator, useVarLib=False):
            for instance in self.selectedInstances:
                previousGlyphName = None
                kerningObject = self.operator.makeOneKerning(instance.location, pairs=possibleKerningPairs)
                for glyphName in glyphNames:
                    # do not bend, reasoning: the instance locations are in designspace values.
                    mathGlyph = self.operator.makeOneGlyph(glyphName, instance.location, decomposeComponents=True)
                    if mathGlyph is not None:
                        dest = internalFontClasses.createGlyphObject()
                        mathGlyph.extractGlyph(dest)

                        glyphRecord = GlyphRecord(dest)

                        if previousGlyphName and glyphRecords:
                            glyphRecords[-1].xAdvance = kerningObject.get((previousGlyphName, glyphName))
                            #print("\t\tkerningObject.get((previousGlyphName, glyphName))", (previousGlyphName, glyphName), kerningObject.get((previousGlyphName, glyphName)))

                        glyphRecords.append(glyphRecord)

                    previousGlyphName = glyphName

                glyphRecords.append(GlyphRecord(self.w.preview.createNewLineGlyph()))

        self.w.preview.setGlyphRecords(glyphRecords)

    designspaceEditorInstancesDidChangeDelay = 0.1

    def singleLineCheckboxCallback(self, sender):
        if sender.get()==0:
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
