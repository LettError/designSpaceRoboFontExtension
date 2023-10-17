from operator import itemgetter

import vanilla
import ezui

from mojo.UI import MultiLineView, splitText, GlyphRecord, StatusBar
from mojo.subscriber import WindowController, Subscriber

from mojo.roboFont import RFont, RGlyph, internalFontClasses

from designspaceEditor.tools import UseVarLib, SendNotification
from designspaceEditor.parsers.parserTools import numberToString

from mutatorMath import Location

skateboardPreviewTextLibKey = "com.letterror.skateboard.previewText"
previewTextLibKey = "com.letterror.designspaceEditor.previewText"


class PreviewLocationFinder(ezui.WindowController):

    def build(self, parent, operator, previewLocation):
        self.operator = operator
        content = """
        = TwoColumnForm
        :
        [ ] Show Preview Location   @showPreviewLocation
        """
        descriptionData = dict(
            content=dict(
                itemColumnWidth=200
            ),
            showPreviewLocation=dict(
                value=bool(previewLocation)
            )
        )

        for axisDescriptor in operator.axes:
            value = axisDescriptor.default
            if previewLocation:
                value = previewLocation.get(axisDescriptor.name, value)

            if hasattr(axisDescriptor, "values"):
                # discrete axis
                content += f"""
                : {axisDescriptor.name}:
                ( ...)         @{axisDescriptor.name}
                """
                descriptionData[axisDescriptor.name] = dict(
                    items=[numberToString(value) for value in axisDescriptor.values]
                )
            else:
                content += f"""
                : {axisDescriptor.name}:
                ---X---         @{axisDescriptor.name}
                """
                descriptionData[axisDescriptor.name] = dict(
                    minValue=axisDescriptor.minimum,
                    maxValue=axisDescriptor.maximum,
                    value=value
                )

        content += """
        =====
        ( Add as Instance )   @addAsInstance
        """
        self.w = ezui.EZPopover(
            content=content,
            descriptionData=descriptionData,
            parent=parent,
            parentAlignment="bottom",
            behavior="transient",
            size="auto",
            controller=self
        )

    def started(self):
        self.w.open()

    def destroy(self):
        self.operator = None

    def getLocation(self):
        location = self.w.getItemValues()
        for axisDescriptor in self.operator.axes:
            if hasattr(axisDescriptor, "values"):
                index = location[axisDescriptor.name]
                location[axisDescriptor.name] = axisDescriptor.values[index]
        del location["showPreviewLocation"]
        return location

    def contentCallback(self, sender):
        if self.w.getItemValue("showPreviewLocation"):
            SendNotification.single(who="PreviewLocation", designspace=self.operator, location=self.getLocation())

    def addAsInstanceCallback(self, sender):
        print

    def showPreviewLocationCallback(self, sender):
        if sender.get():
            SendNotification.single(who="PreviewLocation", designspace=self.operator, location=self.getLocation())
        else:
            SendNotification.single(who="PreviewLocation", designspace=self.operator, location=None)


class PreviewInstance:

    def __init__(self, designLocation):
        self.designLocation = designLocation

    def getFullDesignLocation(self, doc):
        return self.designLocation


class LocationPreview(Subscriber, WindowController):

    debug = True

    def build(self, operator=None, selectedSources=None, selectedInstances=None, previewString=None):
        self.operator = operator

        dummyFont = RFont(showInterface=False)

        upms = set()
        for font in self.operator.fonts.values():
            if font is not None:
                upms.add(font.info.unitsPerEm)

        with UseVarLib(self.operator, useVarLib=False):
            for instance in self.operator.instances:
                #continuousLocation, discreteLocation = self.operator.splitLocation(instance.location)
                #infoMutator = self.operator.getInfoMutator(discreteLocation)
                #info = infoMutator.makeInstance(continuousLocation)
                info = self.operator.makeOneInfo(instance.getFullDesignLocation(self.operator))
                upms.add(info.unitsPerEm)

        dummyFont.info.unitsPerEm = max(upms) if upms else 1000

        self.displayPrefs = {}
        self.displayPrefs['Inverse'] = False
        self.displayPrefs['Beam'] = False
        self.displayPrefs['displayMode'] = "Multi Line"
        self.displayPrefs['Stroke'] = False
        self.displayPrefs['Fill'] = True

        self.shouldShowSources = False
        self.shouldShowInstances = True
        self.shouldShowPreviewLocation = operator.lib.get("com.letterror.designspaceEditor.previewLocation")

        self.shouldSortBy = set()

        self.w = vanilla.FloatingWindow((700, 400), "Instances Preview", minSize=(500, 300))
        self.w.input = vanilla.EditText((10, 10, -80, 22), callback=self.inputCallback)
        self.w.options = vanilla.ActionButton(
            (-80, 10, 30, 22),
            [
                dict(title="Single Line", callback=self.singleLineMenuItemCallback, state=False),
                dict(title="Invert", callback=self.invertMenuItemCallback, state=self.displayPrefs['Inverse']),
                "----",
                dict(title="Show Sources", callback=self.showSourcesMenuItemCallback, state=self.shouldShowSources),
                dict(title="Show Instances", callback=self.showInstancesMenuItemCallback, state=self.shouldShowInstances),
                "----",
                dict(title="Sort Line by Area", callback=self.sortByLineAreaMenuItemCallback, state="area" in self.shouldSortBy),
                dict(title="Sort Line by Length", callback=self.sortByLineLengthMenuItemCallback, state="length" in self.shouldSortBy),
                dict(title="Sort Line by Density", callback=self.sortByLineDensityMenuItemCallback, state="density" in self.shouldSortBy),
            ],
            bordered=False
        )
        self.w.currentLocation = vanilla.Button((-40, 10, 30, 22), "📍", callback=self.currentLocationCallback)
        self.w.hl = vanilla.HorizontalLine((0, 41, 0, 1))
        self.w.preview = MultiLineView(
            (0, 42, 0, -20),
            pointSize=60,
            displayOptions=self.displayPrefs,
            selectionCallback=self.previewSelectionCallback
        )
        self.w.infoText = StatusBar((0, -20, -0, 20))
        self.w.preview.setFont(dummyFont)

        self.selectedSources = selectedSources or []
        self.selectedInstances = selectedInstances or []
        self.previewLocation = None

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
        self.selectedSources = None

    def setPreviewString(self, value):
        self.w.input.set(value)
        self.updatePreview()

    def updatePreview(self):
        self.inputCallback(self.w.input)

    def inputCallback(self, sender):
        previewString = sender.get()
        self.operator.lib[previewTextLibKey] = previewString
        glyphNames = splitText(previewString, self.operator.getCharacterMapping())
        possibleKerningPairs = ((side1, side2) for side1, side2 in zip(glyphNames[:-1], glyphNames[1:]))
        possibleKerningPairs = list(possibleKerningPairs)

        selectedDescriptors = []
        if self.shouldShowSources:
            if self.selectedSources:
                selectedDescriptors.extend(self.selectedSources)
            else:
                selectedDescriptors.extend(self.operator.sources)

        if self.shouldShowInstances:
            if self.selectedInstances:
                selectedDescriptors.extend(self.selectedInstances)
            else:
                selectedDescriptors.extend(self.operator.instances)

        if self.shouldShowPreviewLocation is not None:
            selectedDescriptors.append(PreviewInstance(self.shouldShowPreviewLocation))

        lines = []

        with UseVarLib(self.operator, useVarLib=False):
            for descriptor in selectedDescriptors:
                lineItem = dict(
                    area=0,
                    length=0,
                    density=0,
                    glyphRecords=[]
                )

                previousGlyphName = None
                fullDesignLocation = descriptor.getFullDesignLocation(self.operator)
                kerningObject = self.operator.makeOneKerning(fullDesignLocation, pairs=possibleKerningPairs)
                for glyphName in glyphNames:
                    # do not bend, reasoning: the descriptor locations are in designspace values.
                    mathGlyph = self.operator.makeOneGlyph(glyphName, fullDesignLocation, decomposeComponents=True)
                    if mathGlyph is not None:
                        dest = internalFontClasses.createGlyphObject()
                        mathGlyph.extractGlyph(dest)
                        dest.tempLib['designLocation'] = Location(fullDesignLocation).asString()
                        dest.tempLib['descriptor'] = descriptor

                        glyphRecord = GlyphRecord(dest)

                        if previousGlyphName and lineItem["glyphRecords"]:
                            lineItem["glyphRecords"][-1].xAdvance = kerningObject.get((previousGlyphName, glyphName))

                        lineItem["glyphRecords"].append(glyphRecord)

                        lineItem["length"] += dest.width
                        lineItem["area"] += dest.area

                    previousGlyphName = glyphName

                if lineItem["length"] != 0:
                    lineItem["density"] = lineItem["area"] / lineItem["length"]
                lines.append(lineItem)

        glyphRecords = []
        iterator = lines
        if self.shouldSortBy:
            iterator = sorted(lines, key=itemgetter(*self.shouldSortBy))
        for line in iterator:
            glyphRecords.extend(line["glyphRecords"])
            glyphRecords.append(GlyphRecord(self.w.preview.createNewLineGlyph()))

        self.w.preview.setGlyphRecords(glyphRecords)

    designspaceEditorInstancesDidChangeDelay = 0.1

    def previewSelectionCallback(self, sender):
        selection = self.w.preview.getSelectedGlyph()
        if selection:
            # selection.removeOverlap()
            self.w.infoText.set([
                f"location: {selection.tempLib['designLocation']}",
                f"glyph: {selection.name}",
                f"width: {selection.width:3.1f}",
                f"area: {selection.area:3.1f}"
            ])
        else:
            self.w.infoText.set([])

    def currentLocationCallback(self, sender):
        PreviewLocationFinder(sender, self.operator, self.shouldShowPreviewLocation)

    def invertMenuItemCallback(self, sender):
        choice = not sender.state()
        sender.setState_(choice)
        if choice:
            self.displayPrefs['Inverse'] = True
        else:
            self.displayPrefs['Inverse'] = False
        self.w.preview.setDisplayStates(self.displayPrefs)

    def singleLineMenuItemCallback(self, sender):
        choice = not sender.state()
        sender.setState_(choice)
        if choice:
            self.w.preview.setDisplayStates(dict(displayMode="Single Line"))
        else:
            self.w.preview.setDisplayStates(dict(displayMode="Multi Line"))

    def showSourcesMenuItemCallback(self, sender):
        self.shouldShowSources = not sender.state()
        sender.setState_(self.shouldShowSources)
        self.updatePreview()

    def showInstancesMenuItemCallback(self, sender):
        self.shouldShowInstances = not sender.state()
        sender.setState_(self.shouldShowInstances)
        self.updatePreview()

    def _resolveSortBy(self, sender, key):
        choice = not sender.state()
        sender.setState_(choice)
        if choice:
            self.shouldSortBy.add(key)
        elif not choice and key in self.shouldSortBy:
            self.shouldSortBy.remove(key)
        self.updatePreview()

    def sortByLineAreaMenuItemCallback(self, sender):
        self._resolveSortBy(sender, "area")

    def sortByLineLengthMenuItemCallback(self, sender):
        self._resolveSortBy(sender, "length")

    def sortByLineDensityMenuItemCallback(self, sender):
        self._resolveSortBy(sender, "density")

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

    def designspaceEditorPreviewLocationDidChange(self, notification):
        if self.operator == notification["designspace"]:
            self.shouldShowPreviewLocation = notification["location"]
            self.operator.lib["com.letterror.designspaceEditor.previewLocation"] = self.shouldShowPreviewLocation
            self.updatePreview()

    def designspaceEditorInstancesDidChangeSelection(self, notification):
        if self.operator == notification["designspace"]:
            self.selectedInstances = notification["selectedItems"]
            self.updatePreview()

    def designspaceEditorSourcesDidChangeSelection(self, notification):
        if self.operator == notification["designspace"]:
            self.selectedSources = notification["selectedItems"]
            self.updatePreview()


if __name__ == '__main__':
    designspace = CurrentDesignspace()
    if designspace is None:
        print("Open a design space!")
    else:
        c = LocationPreview(operator=designspace)
        # c.setPreviewString("HELLOVAH")
