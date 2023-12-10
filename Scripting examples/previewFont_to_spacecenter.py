from fontTools.designspaceLib import InstanceDescriptor
from mojo.UI import CurrentSpaceCenter

# Scripting with live designspaces
# demo erik@letterror.com 8.12.2023

# have a desigspace open in DSE2
d = CurrentDesignspace()

# have a spacecenter open
sp = CurrentSpaceCenter()

# you probably want more control over what axis values to look at
# and maybe even a fancy interface
# but that is beyond the scope of this demo
# so for now, a random location
loc = d.randomLocation()

# see the location is just a dict with axisName: axisValue pairs,
print(loc)

# make an "instance descriptor" object to specify what we want to see
preview = InstanceDescriptor()
#preview.familyName = "MyPreview"
#preview.styleName = "MyStyle"
preview.designLocation = loc

# now we're asking the designspace to make a font object with these specs
r = d.makeInstance(preview)
print(r)

# finally, we give the resulting font to the space center.
sp.setFont(r)