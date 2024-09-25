from operator import itemgetter

import vanilla
import ezui

import mojo.drawingTools as ctx

from mojo.UI import MultiLineView, splitText, GlyphRecord, StatusBar
from mojo.extensions import getExtensionDefault, setExtensionDefault
from mojo.subscriber import WindowController, Subscriber
from mojo.events import addObserver, removeObserver
from mojo.roboFont import RFont, internalFontClasses, CurrentFont, CurrentGlyph

from designspaceEditor.tools import UseVarLib, symbolImage
from designspaceEditor.parsers.parserTools import numberToString

from mutatorMath import Location

from designspaceEditor import extensionIdentifier


skateboardPreviewTextLibKey = "com.letterror.skateboard.previewText"
previewTextLibKey = f"{extensionIdentifier}.previewText"

inverseDefaultKey = f"{extensionIdentifier}.inverse"
singleLineDefaultKey = f"{extensionIdentifier}.singleLine"
showSourcesDefaultKey = f"{extensionIdentifier}.showSources"
showInstancesDefaultKey = f"{extensionIdentifier}.showInstances"
shouldSortByDefaultKey = f"{extensionIdentifier}.shouldSortBy"


previewLocationButtonImage = symbolImage("mappin.and.ellipse", "primary")

indicatorImageMap = dict(
    source=symbolImage("smallcircle.filled.circle.fill", (1, .5, 0, 1)),
    instance=symbolImage("smallcircle.filled.circle", (0, 0, 1, 1)),
    previewLocation=symbolImage("mappin.and.ellipse", (1, 0, 0, 1), flipped=True)
)


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
                ---X--- [__]     @{axisDescriptor.name}
                """
                minimum, default, maximum = operator.getAxisExtremes(axisDescriptor)
                descriptionData[axisDescriptor.name] = dict(
                    minValue=minimum,
                    maxValue=maximum,
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
            self.operator.setPreviewLocation(location=self.getLocation())

    def addAsInstanceCallback(self, sender):
        self.operator.addInstanceDescriptor(
            designLocation=self.getLocation()
        )

    def showPreviewLocationCallback(self, sender):
        if sender.get():
            self.operator.setPreviewLocation(location=self.getLocation())
        else:
            self.operator.setPreviewLocation(location=None)


class PreviewInstance:

    flavor = "previewLocation"

    def __init__(self, designLocation):
        self.designLocation = designLocation

    def getFullDesignLocation(self, doc):
        return self.designLocation


class LocationPreview(Subscriber, WindowController):

    debug = True

    def build(self, operator=None, selectedSources=None, selectedInstances=None, previewString=None):
        self.operator = operator

        self.dummyFont = RFont(showInterface=False)

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

        self.dummyFont.info.unitsPerEm = max(upms) if upms else 1000

        self.displayPrefs = {}
        self.displayPrefs['Inverse'] = getExtensionDefault(inverseDefaultKey, False)
        self.displayPrefs['Beam'] = False
        self.displayPrefs['displayMode'] = "Single Line" if getExtensionDefault(singleLineDefaultKey, False) else "Multi Line"
        self.displayPrefs['Stroke'] = False
        self.displayPrefs['Fill'] = True

        self.shouldShowSources = getExtensionDefault(showSourcesDefaultKey, False)
        self.shouldShowInstances = getExtensionDefault(showInstancesDefaultKey, True)
        self.shouldShowPreviewLocation = operator.getPreviewLocation()

        self.shouldSortBy = set(getExtensionDefault(shouldSortByDefaultKey, []))

        self.w = vanilla.FloatingWindow((700, 400), "Location Preview", minSize=(500, 300))
        self.w.input = vanilla.EditText((10, 10, -80, 22), callback=self.inputCallback)
        self.w.options = vanilla.ActionButton(
            (-80, 10, 30, 22),
            [
                dict(title="Single Line", callback=self.singleLineMenuItemCallback, state=self.displayPrefs['displayMode'] == "Single Line"),
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
        self.w.currentLocation = vanilla.Button((-40, 10, 30, 22), "", callback=self.currentLocationCallback)
        self.w.currentLocation.getNSButton().setImage_(previewLocationButtonImage)
        self.w.hl = vanilla.HorizontalLine((0, 41, 0, 1))
        self.w.preview = MultiLineView(
            (0, 42, 0, -20),
            pointSize=60,
            displayOptions=self.displayPrefs,
            selectionCallback=self.previewSelectionCallback
        )
        self.w.infoText = StatusBar((0, -20, -0, 20))
        self.w.preview.setFont(self.dummyFont)

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
        addObserver(self, "locationPreviewLineViewDidDrawGlyph", "spaceCenterDraw")
        self.setPreviewString(previewString)

    def started(self):
        self.w.open()

    def destroy(self):
        removeObserver(self, "spaceCenterDraw")
        self.operator = None
        self.selectedInstances = None
        self.selectedSources = None

    def setPreviewString(self, value):
        self.w.input.set(value)
        self.updatePreview()

    def updatePreview(self):
        self.inputCallback(self.w.input)
        self.populateInfoStatusBar()

    def inputCallback(self, sender):
        previewString = sender.get()
        self.operator.lib[previewTextLibKey] = previewString
        glyphNames = []
        for glyphName in splitText(previewString, self.operator.getCharacterMapping()):
            if glyphName == "/?":
                currentGlyph = CurrentGlyph()
                if currentGlyph is not None:
                    glyphNames.append(currentGlyph.name)
            elif glyphName == "/!":
                currentFont = CurrentFont()
                if currentFont is not None:
                    glyphNames.extend(currentFont.selectedGlyphNames)
            else:
                glyphNames.append(glyphName)

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
            try:
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
                            else:
                                # mark the first glyph
                                dest.tempLib["indicator"] = descriptor.flavor

                            lineItem["glyphRecords"].append(glyphRecord)

                            lineItem["length"] += dest.width
                            lineItem["area"] += dest.area

                        previousGlyphName = glyphName

                    if lineItem["length"] != 0:
                        lineItem["density"] = lineItem["area"] / lineItem["length"]
                    lines.append(lineItem)
            except Exception:
                lines = []
                self.w.infoText.set(["This designspace may not work as expected, check the Designspace Problems."], warning=True)

        glyphRecords = []
        iterator = lines
        if self.shouldSortBy:
            iterator = sorted(lines, key=itemgetter(*self.shouldSortBy))
        for line in iterator:
            glyphRecords.extend(line["glyphRecords"])
            glyphRecords.append(GlyphRecord(self.w.preview.createNewLineGlyph()))

        self.w.preview.setGlyphRecords(glyphRecords)
        # hacking into the multiline view
        self.w.preview._glyphLineView._shouldSendEvents = True

    def previewSelectionCallback(self, sender):
        self.populateInfoStatusBar()

    def populateInfoStatusBar(self):
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

    # menu callbacks

    def invertMenuItemCallback(self, sender):
        choice = not sender.state()
        sender.setState_(choice)
        setExtensionDefault(inverseDefaultKey, choice)
        if choice:
            self.displayPrefs['Inverse'] = True
        else:
            self.displayPrefs['Inverse'] = False
        self.w.preview.setDisplayStates(self.displayPrefs)

    def singleLineMenuItemCallback(self, sender):
        choice = not sender.state()
        sender.setState_(choice)
        setExtensionDefault(singleLineDefaultKey, choice)
        if choice:
            self.displayPrefs['displayMode'] = "Single Line"
        else:
            self.displayPrefs['displayMode'] = "Multi Line"
        self.w.preview.setDisplayStates(dict(displayMode=self.displayPrefs['displayMode']))

    def showSourcesMenuItemCallback(self, sender):
        self.shouldShowSources = not sender.state()
        setExtensionDefault(showSourcesDefaultKey, self.shouldShowSources)
        sender.setState_(self.shouldShowSources)
        self.updatePreview()

    def showInstancesMenuItemCallback(self, sender):
        self.shouldShowInstances = not sender.state()
        setExtensionDefault(showInstancesDefaultKey, self.shouldShowInstances)
        sender.setState_(self.shouldShowInstances)
        self.updatePreview()

    def _resolveSortBy(self, sender, key):
        choice = not sender.state()
        sender.setState_(choice)
        if choice:
            self.shouldSortBy.add(key)
        elif not choice and key in self.shouldSortBy:
            self.shouldSortBy.remove(key)
        setExtensionDefault(shouldSortByDefaultKey, list(self.shouldSortBy))
        self.updatePreview()

    def sortByLineAreaMenuItemCallback(self, sender):
        self._resolveSortBy(sender, "area")

    def sortByLineLengthMenuItemCallback(self, sender):
        self._resolveSortBy(sender, "length")

    def sortByLineDensityMenuItemCallback(self, sender):
        self._resolveSortBy(sender, "density")

    # robofont notifications

    def locationPreviewLineViewDidDrawGlyph(self, notification):
        # old style drawing!
        glyph = notification["glyph"]
        if "indicator" in glyph.tempLib:
            indicator = indicatorImageMap[glyph.tempLib["indicator"]]
            ctx.save()
            if self.displayPrefs['displayMode'] == "Single Line":
                ctx.translate(glyph.width / 2, self.dummyFont.info.descender)
                x = -indicator.size().width / 2
            else:
                ctx.translate(0, self.dummyFont.info.unitsPerEm * .4)
                x = 0
            ctx.scale(-notification["scale"])
            ctx.image(indicator, (x, 0))
            ctx.restore()

    # subscriber notifications

    designspaceEditorInstancesDidChangeDelay = 0.1

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

    designspaceEditorPreviewLocationDidChangeDelay = 0.01

    def designspaceEditorPreviewLocationDidChange(self, notification):
        self.shouldShowPreviewLocation = notification["location"]
        self.updatePreview()

    def designspaceEditorInstancesDidChangeSelection(self, notification):
        self.selectedInstances = notification["selectedItems"]
        self.updatePreview()

    def designspaceEditorSourcesDidChangeSelection(self, notification):
        self.selectedSources = notification["selectedItems"]
        self.updatePreview()

    def roboFontDidSwitchCurrentGlyph(self, notification):
        if not self.w.getNSWindow().isKeyWindow():
            self.updatePreview()


if __name__ == '__main__':
    designspace = CurrentDesignspace()
    if designspace is None:
        print("Open a design space!")
    else:
        c = LocationPreview(operator=designspace)
        # c.setPreviewString("HELLOVAH")
