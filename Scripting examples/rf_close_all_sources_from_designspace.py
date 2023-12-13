
# save and close all open fonts that belong
# to the current designspace.

ds = CurrentDesignspace()

dsFontPaths = [f.path for f, l in ds.getFonts()]

for f in AllFonts():
    if f.path in dsFontPaths:
        f.save()
        f.close()