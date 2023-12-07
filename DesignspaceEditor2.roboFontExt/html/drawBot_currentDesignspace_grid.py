#drawbot

# draw a grid of interpolated glyphs
# along 2 continuous axes
# from the current designspace.

size(1159, 1070)

def ip(a, b, f):
    return a+f*(b-a)
    
def grid(ds, glyphName, horizontalAxis, verticalAxis, columns, rows):
    items = []
    for x in range(columns):
        xf = x/(columns-1)
        for y in range(rows):
            yf = y/(rows-1)
            # assume axes are continuous
            ah = ds.getAxis(horizontalAxis)
            ahValue = ip(ah.minimum, ah.maximum, xf)
            av = ds.getAxis(verticalAxis)
            avValue = ip(av.minimum, av.maximum, yf)
            loc = {horizontalAxis:ahValue, verticalAxis:avValue}
            glyph = ds.makeOneGlyph(glyphName, loc)
            items.append(((x, y), loc, glyph))
    return items

# parameters 
glyphName = "R"
horizontalAxis = "width"
verticalAxis = "weight"
columns = 8
rows = 9
margin = 100
xunit = (width()-2*margin)/columns
yunit = (height()-2*margin)/rows

d = CurrentDesignspace()
assert d is not None
fill(0)
stroke(None)
with savedState():
    translate(margin,margin)
    for (x,y), loc, glyph in grid(d, glyphName, horizontalAxis, verticalAxis, columns, rows):
        with savedState():
            translate(x*xunit, y*yunit)
            scale(0.09)
            bp = BezierPath()
            glyph.draw(bp)
            drawPath(bp)

# save the image
saveImage(f"grid_{horizontalAxis}_{columns}_{verticalAxis}_{rows}.png")
