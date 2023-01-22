# with a wink to https://nl.wikipedia.org/wiki/Yaacov_Agam
# generated in 2017
# then I lost the script
# so, rebuilt in 2023.

iconSize = (30,30)
output = ".pdf"

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

# some basic values for all icons
clr1 = aiColor(217, 87, 204)
clr3 = aiColor(217, 87, 126)
clr2 = aiColor(38, 15, 22)
clr4 = aiColor(38, 15, 36)

# adjusted colors
r = 157
g = 97
clr1 = aiColor(r, g, 204)
clr3 = aiColor(r, g, 126)
clr2 = aiColor(38, 15, 22)
clr4 = aiColor(38, 15, 36)

tp = 0.8    # transparency for some things
m = 1.5    # outside margin
d = 6.2    # line diameter
fs = 6.5    # text button font size

forReals = True    # set to True to make individual files
if forReals:
    # save individual files in the resources folder
    folder = "../resources/"
    #folder = "../DesignspaceEditor2.roboFontExt/resources/"
else:
    # save one pdf preview in the folder with this drawbot script
    folder = ""

# axes icon
if forReals:
    newDrawing()
newPage(*iconSize)
left, right = m+.5*d, width()-m-0.5*d
top, bottom = height()-m-.5*d, m+0.5*d
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
    name = f"{folder}toolbar_icon_axes{output}"
    saveImage(name)

# instances icon
if forReals:
    newDrawing()
newPage(*iconSize)
with savedState():
    steps = 4
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
if forReals:
    name = f"{folder}toolbar_icon_instances{output}"
    saveImage(name)

# sources icon
if forReals:
    newDrawing()
newPage(*iconSize)
with savedState():
    steps = 4
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
            else:
                tps = 0.7
            fill(*c, tps)    # transparency
            oval(p[0]-.5*d,p[1]-.5*d, d, d)
if forReals:
    name = f"{folder}toolbar_icon_sources{output}"
    saveImage(name)

# labels icon
# defines groups and relations between locations
if forReals:
    newDrawing()
newPage(*iconSize)
with savedState():
    steps = 4
    stops = {}
    fills = {}
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
    ltp = 0.5
    stroke(*fills[(0,0)],ltp)
    line(stops[(0,0)], stops[(0,1)])
    stroke(*fills[(1,1)],ltp)
    line(stops[(1,1)], stops[(1,3)])
    stroke(*fills[(2,3)],ltp)
    line(stops[(2,1)], stops[(2,3)])
    stroke(*fills[(1,0)],ltp)
    line(stops[(1,0)], stops[(1,0)])
    stroke(*fills[(3,0)],ltp)
    line(stops[(2,1)], stops[(3,1)])
if forReals:
    name = f"{folder}toolbar_icon_labels{output}"
    saveImage(name)

# problems icon
if forReals:
    newDrawing()
newPage(*iconSize)
with savedState():
    # gridlines
    strokeWidth(d)
    lineCap("round")
    stroke(*clr1, tp)
    line((left, top), (right, top))
    stroke(*clr2, tp)
    line((left, top), (left, bottom))
    stroke(*clr2, tp)
    line((right, top), (right, bottom))
    stroke(*clr3, tp)
    line((left, bottom), (right, bottom))
    steps = 4
    # white rects
    fill(1)
    stroke(None)
    rd = 0.4*d
    for y in range(steps):
        fy = y / (steps-1)
        p1 = ip2((left, top), (right, top), fy)
        p2 = ip2((left, bottom), (right, bottom), fy)
        for x in range(steps):
            fx = x / (steps-1)
            p = ip2(p1, p2, fx)
            if 0 < fx < 1 and 0 < fy < 1:
                fill(*clr3)    # transparency
            else:
                fill(1)
            rect(p[0]-.5*rd,p[1]-.5*rd, rd, rd)        
if forReals:
    name = f"{folder}toolbar_icon_problems{output}"
    saveImage(name)

# rules icon
if forReals:
    newDrawing()
newPage(*iconSize)
with savedState():
    steps = 4
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
    name = f"{folder}toolbar_icon_rules{output}"
    saveImage(name)

textX = 2
textY = 12.7

# rules icon
if forReals:
    newDrawing()
newPage(*iconSize)
with savedState():
    pass
    font("ActionTextDark-Bold")
    fontSize(fs)
    fill(*clr2)
    text("Save", (textX,textY))
if forReals:
    name = f"{folder}toolbar_icon_save{output}"
    saveImage(name)

# rules icon
if forReals:
    newDrawing()
newPage(*iconSize)
with savedState():
    pass
    font("ActionTextDark-Bold")
    fontSize(fs)
    fill(*clr2)
    text("Settings", (textX,textY))
if forReals:
    name = f"{folder}toolbar_icon_settings{output}"
    saveImage(name)

if not forReals:
    saveImage("all_icons_preview.pdf")