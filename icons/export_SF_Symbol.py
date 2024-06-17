#for n in installedFonts():
#    if "SF" in n:
#        print(n)
        

# width and height of the square output document
dim = 275

names = [
    ("􀅴", "SFPro-Regular", "info.circle"),
    ("􀈄", "SFPro-Regular", "square.and.arrow.down"),
    ("􀁜", "SFPro-Regular", "questionmark.circle"),
    ("􀅵", "SFPro-Regular", "info.circle.fill"),
    ("􁌵", "SFPro-Regular", "info.bubble.fill"),
    ("􀜍", "SFPro-Regular", "wand.and.stars"),
    ]

for sym, fontName, symbolName in names:
    newDrawing()
    newPage(dim,dim)
    margin = 54/325 * width()
    bp = BezierPath()
    fs = FormattedString()
    fs.font(fontName)
    fs.fontSize(250/275 * width())
    fs.append(sym)
    bp.text(fs)
    xMin, yMin, xMax, yMax = bp.bounds()
    w = xMax-xMin
    h = yMax-yMin
    s = w/(width()-2*margin)
    with savedState():
        fill(0)
        translate(width()*.5, height()*.5)
        translate(-xMin, -yMin)
        translate(-.5*w, -.5*h)
        drawPath(bp)
    saveImage(f"{symbolName}_{symbolName}.svg")
    
