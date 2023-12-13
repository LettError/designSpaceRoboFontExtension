#drawbot

# choose a random glyph
# and a random designspace location
# and be surprised!

size(1000, 600)
d = CurrentDesignspace()
fill(.5)
stroke(None)
blendMode("multiply")
names = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "arrowdown", "arrowleft", "arrowright", "arrowup"]

clr = [(1,0,0), (0,0,1), (1,.9,0)]

with savedState():
    translate(0, 100)
    for c in clr:
        with savedState():
            translate(.5 * width(), 0)
            scale(0.5)
            fill(*c)
            loc = d.randomLocation()    
            glyphName = choice(names)
            g = d.makeOneGlyph(glyphName, decomposeComponents=True, location=loc)
            if g is not None:
                translate(-.5*g.width,0)
                bp = BezierPath()
                g.draw(bp)
                drawPath(bp)