#drawbot
d = CurrentDesignspace()
if d is not None:
    previewLoc = d.randomLocation()
    d.setPreviewLocation(previewLoc)

    loc = dict(weight=800, width=800)
    r = d.makeOneGlyph("R", loc)

    translate(100, 100)
    scale(0.8)
    drawGlyph(r)