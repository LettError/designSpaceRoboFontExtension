
size(1000, 500)
d = CurrentDesignspace()
fill(None)
stroke(0)
strokeWidth(.5)
with savedState():
    translate(100, 100)
    scale(0.5)
    for i in range(20):
        loc = d.randomLocation()
        g = d.makeOneGlyph("logo", location=loc)
        bp = BezierPath()
        g.draw(bp)
        drawPath(bp)