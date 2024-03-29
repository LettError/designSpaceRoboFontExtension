# open all the ufos used in the current designspace
# See how DSE2 keeps track of which fonts are open
# and that edits in the fonts are reflected in the previews.
ds = CurrentDesignspace()
done = []

discreteLocation = {'slab': 0}
discreteLocation = None

for font, loc in ds.getFonts():
    if discreteLocation is not None:
        if loc | discreteLocation != loc:
            continue
    if font.path not in done:
        font.asFontParts().openInterface()
        # a ufo can appear multiple times in the designspace
        # and we don't want to open duplicate font windows
        # so, keep track of what fonts we've opened.
        done.append(font.path)
