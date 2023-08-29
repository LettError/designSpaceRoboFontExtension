import vanilla
from mojo.UI import MultiLineView, splitText, GlyphRecord
from mojo.subscriber import WindowController, Subscriber, registerRoboFontSubscriber

from mojo.roboFont import RFont, RGlyph


class InstancesPreview(Subscriber, WindowController):

    debug = True

    def build(self, operator=None):
        self.operator = operator
        dummyFont = RFont(showInterface=False)

        self.w = vanilla.FloatingWindow((700, 400), "Instances Preview", minSize=(500, 300))
        self.w.input = vanilla.EditText((10, 10, -120, 22), callback=self.inputCallback)
        self.w.singleLine = vanilla.CheckBox((-100, 10, 100, 22), "Single line", value=True, callback=self.singleLineCheckboxCallback)
        self.w.hl = vanilla.HorizontalLine((0, 41, 0, 1))
        self.w.preview = MultiLineView((0, 42, 0, 0), pointSize=60, displayOptions=dict(Beam=False, displayMode="Multi Line", Stroke=False, Fill=True))
        self.w.preview.setFont(dummyFont)

    def started(self):
        self.w.open()

    def inputCallback(self, sender):
        glyphNames = splitText(sender.get(), self.operator.getCharacterMapping())
        glyphRecords = []
        possibleKerningPairs = ((side1, side2) for side1, side2 in zip(glyphNames[:-1], glyphNames[1:]))
        for instance in self.operator.instances:
            previousGlyphName = None
            continuousLocation, discreteLocation = self.operator.splitLocation(instance.location)
            kerningMutator = self.operator.getKerningMutator(possibleKerningPairs, discreteLocation=discreteLocation)
            kerningObject = kerningMutator.makeInstance(continuousLocation)
            for glyphName in glyphNames:
                # do not bend, reasoning: the instance locations are in designspace values.
                glyph = self.operator.makeOneGlyph(glyphName, instance.location, decomposeComponents=True)
                if glyph is not None:
                    dest = RGlyph()
                    dest.fromMathGlyph(glyph)
                    dest.name = glyph.name

                    glyphRecord = GlyphRecord(dest.asDefcon())

                    if previousGlyphName:
                        glyphRecords[-1].xAdvance = kerningObject.get((previousGlyphName, glyphName))

                    glyphRecords.append(glyphRecord)

                previousGlyphName = glyphName

            glyphRecords.append(GlyphRecord(self.w.preview.createNewLineGlyph()))

        self.w.preview.setGlyphRecords(glyphRecords)

    designspaceEditorInstancesDidChangeDelay = 0.1

    def singleLineCheckboxCallback(self, sender):
        if sender.get():
            self.w.preview.setDisplayStates(dict(displayMode="Multi Line"))
        else:
            self.w.preview.setDisplayStates(dict(displayMode="Single Line"))

    def designspaceEditorInstancesDidChange(self, notification):
        self.inputCallback(self.w.input)

    #def designspaceEditorInstancesDidChangeSelection(self, notification):
    #    print("designspaceEditorInstancesDidChangeSelection")
    #    print(notification)

    def designspaceEditorSourcesDidChanged(self, notification):
        self.inputCallback(self.w.input)

    def designspaceEditorAxesDidChange(self, notification):
        self.inputCallback(self.w.input)



if __name__ == '__main__':
    c = InstancesPreview(operator=CurrentDesignspace())
    c.w.input.set("HELLOVAH")
    c.inputCallback(c.w.input)