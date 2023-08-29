# with a wink to https://nl.wikipedia.org/wiki/Yaacov_Agam
# generated in 2017
# then I lost the script
# so, rebuilt in 2023.

from roundedRect import roundedRect

forReals = True    # set to True to make individual files

#iconSize = (30,30)
iconSize = (100,100)
#iconSize = (1000,1000)
output = ".pdf"
output = ".png"

stops = {}
fills = {}
destinations = [
    (30,30, ".pdf", "../DesignspaceEditor2.roboFontExt/resources/", True),
    (30,30, ".png", "../DesignspaceEditor2.roboFontExt/resources/", True),
    (500,500, ".png", "../DesignspaceEditor2.roboFontExt/resources/", True),
    (100,100, ".png", "../assets/", True),
    (500,500, ".png", "../assets/", True),
    (1000,1000, ".png", "../icons/", True),
    (1000,1000, ".pdf", "../icons/", False),
    ]

def aiColor(r, g, b):
    # convert color reported in illustrator to drawbot
    return (r/255, g/255, b/255)

def ip(a, b, f):
    # interpolate single value
    return a+f*(b-a)

def ip2(a, b, f):
    # interpolate 2 tuple
    return ip(a[0], b[0], f), ip(a[1], b[1], f)

def ip3(a, b, f):
    # interpolate 3-tuple
    # I'm sure this can be more effish, but it is cold
    # and I like the laptop warm. 
    return ip(a[0], b[0], f), ip(a[1], b[1], f), ip(a[2], b[2], f)

# color scheme of DSE 1
clr1 = aiColor(217, 87, 204)
clr3 = aiColor(217, 87, 126)
clr2 = aiColor(38, 15, 22)
clr4 = aiColor(38, 15, 36)

# slightly randomised + print, pick one you like!
def bright():
    return 255 * (0.85+0.15*random())
def dark():
    return 255 * (0.5*random())
clr1 = aiColor(bright(), bright(), dark())
clr2 = aiColor(dark(), bright(), bright())
clr3 = aiColor(bright(), bright(), dark())
clr4 = aiColor(bright(), dark(), dark())

print(f"clr1 = {clr1}\t#clr1")
print(f"clr2 = {clr2}\t#clr2")
print(f"clr3 = {clr3}\t#clr3")
print(f"clr4 = {clr4}\t#clr4")

# this is one I liked, yellowy / pinky
#clr1 = (0.9688909508398984, 0.7828135059070719, 0.10287814777035367)	#clr1
#clr2 = (0.1568901126980957, 0.030304283163796353, 0.15687865848043922)	#clr2
#clr3 = (0.9095971342391956, 0.05722834396389795, 0.8253066786292945)	#clr3
#clr4 = (0.23727920172787428, 0.11471895002167495, 0.06909423615700111)	#clr4

# reddish pinkish
#clr1 = (0.8667170913004896, 0.7609157785697633, 0.11981542934361156)	#clr1
#clr2 = (0.08753532445502746, 0.08598083773265949, 0.03144601823862467)	#clr2
#clr3 = (0.9660296604288963, 0.15837429135828235, 0.922434884401394)	#clr3
#clr4 = (0.9688990431243408, 0.15982308157810274, 0.191174059050476)	#clr4

# tunes to make 
clr1 = (1, .8, 0)	#clr1
clr2 = (1, .2, 0)	#clr2
clr3 = (1, .2, 0.75)	#clr4
clr4 = (.1, .1, .8)	#clr4


for w, h, output, folder, forReals in destinations:

    iconSize = w,h

    # axes icon
    if forReals:
        newDrawing()
    newPage(*iconSize)
    # first time we have a canvas size
    # we have to calculate the measurements
    # so that the icons will look the same
    # regardless of scale
    tp = 0.8    # transparency for some things
    m = 0.05 * width()
    d = 0.272 * width()
    fs = 0.44 * width()
    docLineWidth = 0.05*width()

    left, right = m+.5*d, width()-m-0.5*d
    top, bottom = height()-m-.5*d, m+0.5*d
    wdth = width()-2*m
    hght = height()-2*m
    steps = 103
    items = {}
    with savedState():
        for i in range(steps):
            f = i/steps
            c1 = ip3(clr1, clr2, f)
            c2 = ip3(clr3, clr4, f)
            p1 = ip2((left, top), (right,  bottom), f)
            p2 = ip2((right, top), (left, bottom), f)
            fill(*c1)
            oval(p1[0]-.5*d,p1[1]-.5*d, d, d)
            fill(*c2)
            oval(p2[0]-.5*d,p2[1]-.5*d, d, d)
    if forReals:
        name = f"{folder}toolbar_{w}_{h}_icon_axes{output}"
        saveImage(name)
    
    def under():
        steps = 3
        for y in range(steps):
            fy = y / (steps-1)
            p1 = ip2((left, top), (right, top), fy)
            p2 = ip2((left, bottom), (right, bottom), fy)
            c1 = ip3(clr1, clr3, fy)
            c2 = ip3(clr2, clr4, fy)
            fill(1,1,1,0.5)
            for x in range(steps):
                fx = x / (steps-1)
                p = ip2(p1, p2, fx)
                oval(p[0]-.5*d,p[1]-.5*d, d, d)
                stops[(x,y)] = p
        # remove before final XX
        #fill(0.4)
        #rect(0,0,width(),height())

    # instances icon
    instanceColors = {}
    if forReals:
        newDrawing()
    newPage(*iconSize)
    with savedState():
        # white underfills
        under()
        steps=3
        for y in range(steps):
            fy = y / (steps-1)
            p1 = ip2((left, top), (right, top), fy)
            p2 = ip2((left, bottom), (right, bottom), fy)
            c1 = ip3(clr1, clr3, fy)
            c2 = ip3(clr2, clr4, fy)
            for x in range(steps):
                fx = x / (steps-1)
                p = ip2(p1, p2, fx)
                c = ip3(c1, c2, fx)
                instanceColors[(x,y)] = c
                fill(*c, tp)    # transparency
                oval(p[0]-.5*d,p[1]-.5*d, d, d)
    if forReals:
        name = f"{folder}toolbar_{w}_{h}_icon_instances{output}"
        saveImage(name)

    # sources icon
    if forReals:
        newDrawing()
    newPage(*iconSize)
    with savedState():
        under()
        steps = 3
        for y in range(steps):
            fy = y / (steps-1)
            p1 = ip2((left, top), (right, top), fy)
            p2 = ip2((left, bottom), (right, bottom), fy)
            c1 = ip3(clr1, clr3, fy)
            c2 = ip3(clr2, clr4, fy)
            for x in range(steps):
                fx = x / (steps-1)
                p = ip2(p1, p2, fx)
                c = ip3(c1, c2, fx)
                if 0 < x < steps-1 or 0 < y < steps-1:
                    tps = 0.2
                    drawCenter=True
                else:
                    tps = 0.7
                    drawCenter=False
                fill(*c, tps)    # transparency
                oval(p[0]-.5*d,p[1]-.5*d, d, d)
                # if drawCenter:
                #     fill(1)
                #     dc = 0.5 * d
                #     oval(p[0]-.5*dc,p[1]-.5*dc, dc, dc)
    if forReals:
        name = f"{folder}toolbar_{w}_{h}_icon_sources{output}"
        saveImage(name)


    # variable fonts icon
    # axes icon
    if forReals:
        newDrawing()
    newPage(*iconSize)
    # first time we have a canvas size
    # we have to calculate the measurements
    # so that the icons will look the same
    # regardless of scale
    tp = 0.8    # transparency for some things
    m = 0.05 * width()
    d = 0.272 * width()
    fs = 0.44 * width()
    docLineWidth = 0.05*width()

    left, centerx, right = m+.5*d, .5*width(), width()-m-0.5*d
    top, centery, bottom = height()-m-.5*d, .5*height(),    m+0.5*d
    wdth = width()-2*m
    hght = height()-2*m
    steps = 50
    items = {}
    with savedState():
        for i in range(steps):
            f = i/steps
            #c1 = ip3(clr1, clr2, f)
            c1 = ip3(instanceColors[(0,0)], instanceColors[(2,0)], f)
            c2 = ip3(instanceColors[(0,2)], instanceColors[(2,2)], f)
            p1 = ip2((left, top), (centerx,  centery), f)
            p2 = ip2((centerx, top), (left, centery), f)
            fill(*c1)
            d2 = 0.8 * d    # kruisje iets dunner
            oval(p1[0]-.5*d2,p1[1]-.5*d2, d2, d2)
            fill(*c2)
            oval(p2[0]-.5*d2,p2[1]-.5*d2, d2, d2)
    with savedState():
        for i in range(steps):
            f = i/steps
            c1 = ip3(instanceColors[(0,0)], instanceColors[(2,0)], f)
            #c2 = ip3(instanceColors[(0,2)], instanceColors[(1,2)], f)
            gray = 0.79
            p1 = ip2((left, bottom), (right,  bottom), f)
            p2 = ip2((right, top), (right, centery), f)
            fill(*c1)
            oval(p1[0]-.5*d,p1[1]-.5*d, d, d)
            fill(gray)
            oval(p2[0]-.5*d,p2[1]-.5*d, d, d)
    if forReals:
        name = f"{folder}toolbar_{w}_{h}_icon_variable_fonts{output}"
        saveImage(name)



    # notifications icon
    # axes icon
    if forReals:
        newDrawing()
    newPage(*iconSize)
    # first time we have a canvas size
    # we have to calculate the measurements
    # so that the icons will look the same
    # regardless of scale
    tp = 0.8    # transparency for some things
    m = 0.05 * width()
    d = 0.272 * width()
    fs = 0.44 * width()
    docLineWidth = 0.05*width()

    left, centerx, right = m+.5*d, .5*width(), width()-m-0.5*d
    top, centery, bottom = height()-m-.5*d, .5*height(),    m+0.5*d
    wdth = width()-2*m
    hght = height()-2*m
    steps = 50
    items = {}
    with savedState():
        for i in range(steps):
            f = i/steps
            #c1 = ip3(clr1, clr2, f)
            c1 = ip3(instanceColors[(0,0)], instanceColors[(2,0)], f)
            c2 = ip3(instanceColors[(2,0)], instanceColors[(1,2)], f)
            c3 = ip3(instanceColors[(1,0)], instanceColors[(0,2)], f)
            p1 = ip2((left, top), (right,  top), f)
            p2 = ip2((left, centery), (right, centery), f)
            fill(*c1)
            p3 = ip2((left, bottom), (right,  bottom), f)
            oval(p1[0]-.5*d,p1[1]-.5*d, d, d)
            fill(*c2)
            oval(p2[0]-.5*d,p2[1]-.5*d, d, d)
            fill(*c3)
            oval(p3[0]-.5*d,p3[1]-.5*d, d, d)
    if forReals:
        name = f"{folder}toolbar_{w}_{h}_icon_notifications{output}"
        saveImage(name)





    # problems icon
    if forReals:
        newDrawing()
    newPage(*iconSize)
    windows = {}
    with savedState():
        # gridlines
        blendMode("multiply")
        under()
        strokeWidth(d)
        lineCap("round")
        stroke(*clr1, tp)
        line((left, top), (centerx, top))
        stroke(*clr2, tp)
        line((left, top), (left, bottom))
        stroke(*clr4, tp)
        line((right, top), (right, centery))
        stroke(*clr3, tp)
        line((left, bottom), (right, bottom))
        steps = 3
        # white rects
        fill(1)
        stroke(None)
        rd = 0.4*d
        blendMode("normal")
        skip = [(0,0),]
        for y in range(steps):
            fy = y / (steps-1)
            p1 = ip2((left, top), (right, top), fy)
            p2 = ip2((left, bottom), (right, bottom), fy)
            for x in range(steps):
                if (x,y) in skip:
                    continue
                fx = x / (steps-1)
                p = ip2(p1, p2, fx)
                if 0 < fx < 1 and 0 < fy < 1:
                    fill(*clr3)    # transparency
                else:
                    fill(1)
                rect(p[0]-.5*rd,p[1]-.5*rd, rd, rd)  
                windows[(y,x)] = (p[0]-.5*rd,p[1]-.5*rd, rd, rd) 
    if forReals:
        name = f"{folder}toolbar_{w}_{h}_icon_problems{output}"
        saveImage(name)

    # location labels icon
    # defines groups and relations between locations
    if forReals:
        newDrawing()
    newPage(*iconSize)
    blendMode("multiply")
    with savedState():
        under()
        steps = 3
        for y in range(steps):
            fy = y / (steps-1)
            p1 = ip2((left, top), (right, top), fy)
            p2 = ip2((left, bottom), (right, bottom), fy)
            c1 = ip3(clr1, clr3, fy)
            c2 = ip3(clr2, clr4, fy)
            for x in range(steps):
                fx = x / (steps-1)
                p = ip2(p1, p2, fx)
                c = ip3(c1, c2, fx)
                fill(*c, 0.7*tp)    # transparency
                oval(p[0]-.5*d,p[1]-.5*d, d, d)
                stops[(y, x)] = p
                fills[(y, x)] = c
    with savedState():
        fill(None)
        strokeWidth(d)
        lineCap("round")
        ltp = 1
        stroke(*fills[(0,0)],ltp)
        line(stops[(0,0)], stops[(0,1)])
        stroke(*fills[(0,1)],ltp)
        line(stops[(1,0)], stops[(1,2)])
        stroke(*fills[(2,1)],ltp)
        line(stops[(2,1)], stops[(2,2)])
    blendMode("normal")
    with savedState():
        holes = [(0,0), (2,1), (1,1), (0,2), (2,0)]
        fill(1)
        for p in holes:
            if p in windows:
                rect(*windows[p])
    if forReals:
        name = f"{folder}toolbar_{w}_{h}_icon_location_labels{output}"
        saveImage(name)

    # rules icon
    if forReals:
        newDrawing()
    newPage(*iconSize)
    with savedState():
        under()
        steps = 3
        for y in range(steps):
            fy = y / (steps-1)
            p1 = ip2((left, top), (right, top), fy)
            p2 = ip2((left, bottom), (right, bottom), fy)
            c1 = ip3(clr1, clr3, fy)
            c2 = ip3(clr2, clr4, fy)
            for x in range(steps):
                fx = x / (steps-1)
                p = ip2(p1, p2, fx)
                c = ip3(c1, c2, fx)
                fill(*c, tp)    # transparency
                oval(p[0]-.5*d,p[1]-.5*d, d, d)

        # white rects
        fill(1)
        stroke(None)
        rd = 0.4*d
        for y in range(2, steps):
            fy = y / (steps-1)
            p1 = ip2((left, top), (right, top), fy)
            p2 = ip2((left, bottom), (right, bottom), fy)
            for x in range(steps):
                fx = x / (steps-1)
                p = ip2(p1, p2, fx)
                fill(1)
                rect(p[0]-.5*rd,p[1]-.5*rd, rd, rd)        
    if forReals:
        name = f"{folder}toolbar_{w}_{h}_icon_rules{output}"
        saveImage(name)



    # notes icon
    if forReals:
        newDrawing()
    newPage(*iconSize)
    blendMode("multiply")
    stops = {}
    fills = {}
    with savedState():
        #under()
        steps = 3
        y = 0
        fy = y / (steps-1)
        p1 = ip2((left, top), (right, top), fy)
        p2 = ip2((left, bottom), (right, bottom), fy)
        c1 = ip3(clr1, clr3, fy)
        c2 = ip3(clr2, clr4, fy)
        for x in range(steps):
            fx = x / (steps-1)
            p = ip2(p1, p2, fx)
            c = ip3(c1, c2, fx)
            fill(*c, tp)    # transparency
            oval(p[0]-.5*d,p[1]-.5*d, d, d)
            stops[(y, x)] = p
        
        with savedState():
            # draw a document
            gray = 0.79
            fill(gray, gray, gray, 0.5)
            colMargin = 0.09*width()
            colLeft = left+.68*d + colMargin
            colRight = left+.68*d + wdth-1.22*d - colMargin
            mm = 0.08
            ccl = ip(colLeft, colRight, mm)
            ccr = ip(colLeft, colRight, 1-mm)
            colTop = bottom-.5*d + hght
            colBottom = bottom-.5*d
            colWidth = colRight-colLeft
            colHeight = colTop-colBottom
            roundedRect(left+.68*d, bottom-.5*d, wdth-1.22*d, hght, .4*d )
            stroke(0.4)
            strokeWidth(docLineWidth)
            colLines = 10
            for i in range(2, colLines-3):
                factor = i/(colLines-2)
                y = ip(colTop, colBottom, factor)
                stroke(0)
                lim = 1
                if i%6==0:
                    lim = .79
                line((ccl, y), (lim*ccr, y))
            
    if forReals:
        name = f"{folder}toolbar_{w}_{h}_icon_notes{output}"
        saveImage(name)
    print('stops', stops)


    textX = 0.05 * width()
    textY = 0.38 * width()

    # # save icon
    # if forReals:
    #     newDrawing()
    # newPage(*iconSize)
    # with savedState():
    #     font("ActionTextDark-Bold")
    #     fontSize(fs)
    #     fill(*clr3)
    #     text("Save", (textX,textY))
    # if forReals:
    #     name = f"{folder}toolbar_{w}_{h}_icon_save{output}"
    #     saveImage(name)

    # # settings icon
    # if forReals:
    #     newDrawing()
    # newPage(*iconSize)
    # with savedState():
    #     font("ActionTextDark-Bold")
    #     fontSize(fs)
    #     fill(*clr1)
    #     text("#", (textX,textY))
    # if forReals:
    #     name = f"{folder}toolbar_{w}_{h}_icon_settings{output}"
    #     saveImage(name)

    if not forReals:
        saveImage(f"all_icons_{w}_{h}_dse2_preview.pdf")



    names = [
        ("􀅴", "SFPro-Regular", "info.circle"),
        ("􀈄", "SFPro-Regular", "square.and.arrow.down"),
        ("􀁜", "SFPro-Regular", "questionmark.circle"),
        ("􀅵", "SFPro-Regular", "info.circle.fill"),
        ("􁌵", "SFPro-Regular", "info.bubble.fill"),
        ]
        


if forReals:
    destinations = [
        (30,30, ".pdf", "../DesignspaceEditor2.roboFontExt/resources/", True),
        (25,25, ".png", "../DesignspaceEditor2.roboFontExt/resources/", True),
        (25,25, ".svg", "../DesignspaceEditor2.roboFontExt/resources/", True),
        ]

    for w, h, output, folder, forReals in destinations:

        # items based on SFSymbols
        # width and height of the square output document
        dim = min(w, h)


        for sym, fontName, symbolName in names:
            newDrawing()
            newPage(dim,dim)
            blendMode("multiply")
            margin = 85/325 * width()
            bp = BezierPath()
            fs = FormattedString()
            fs.font(fontName)
            fs.fontSize(219/275 * width())
            fs.append(sym)
            bp.text(fs)
            xMin, yMin, xMax, yMax = bp.bounds()
            ws = xMax-xMin
            hs = yMax-yMin
            ss = w/(width()-2*margin)
            with savedState():
                fill(0)
                translate(width()*.5, height()*.5)
                translate(-xMin, -yMin)
                translate(-.5*ws, -.5*hs)
                drawPath(bp)
            saveImage(f"{folder}toolbar_{w}_{h}_{symbolName}{output}")
    
