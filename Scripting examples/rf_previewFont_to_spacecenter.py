from fontTools.designspaceLib import InstanceDescriptor
from mojo.UI import CurrentSpaceCenter, OpenSpaceCenter, splitText

# Scripting with live designspaces
# demo erik@letterror.com 12.12.2023

proofText = "DS FIVE"

# have a desigspace open in DSE2
ds = CurrentDesignspace()

# you probably want more control over what axis values to look at
# and maybe even a fancy interface
# but that is beyond the scope of this demo
# so for now, a random location
loc = ds.randomLocation()
# the location is just a dict with axisName: axisValue pairs.
print("location", loc)

# we can split this random location into its continuous and discrete parts
continuousPart, discretePart = ds.splitLocation(loc)
print("continuous part of the location:", continuousPart)
print("discrete part of the location:", discretePart)

# get the default font
# note we ask for the default of a specific discrete location here
defaultFont = ds.findDefaultFont(discreteLocation=discretePart)
glyphNames = splitText(proofText, defaultFont.asFontParts().getCharacterMapping())
print("glyphNames", glyphNames)

# make an "instance descriptor" object to specify what we want to see
preview = InstanceDescriptor()
preview.designLocation = loc
preview.familyName = defaultFont.info.familyName

# now we're asking the designspace to make a font object with these specs
# This makes the whole font. If you're just looking at a couple of characters
# there are faster ways to do that. 
previewFont = ds.makeInstance(preview, 
        glyphNames=set(glyphNames),
        decomposeComponents=True)
previewFont = previewFont.asFontParts()

# finally, we give the resulting font to the space center.
# have a spacecenter open
sp = CurrentSpaceCenter()
if sp is None:
    sp = OpenSpaceCenter(previewFont)

sp.setFont(previewFont)
spString = "/" + "/".join(glyphNames)
print('spString', spString)
sp.setRaw(spString)

# optionally, open the font window
#previewFont.openInterface()
