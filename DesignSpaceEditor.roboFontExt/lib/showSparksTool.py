# -*- coding: utf-8 -*-

from AppKit import NSColor, NSFont, NSFontAttributeName, NSForegroundColorAttributeName, NSCursor
from mojo.events import installTool, EditingTool, BaseEventTool, setActiveEventTool
from defconAppKit.windows.baseWindow import BaseWindowController
from robofab.pens.digestPen import DigestPointPen
from robofab.world import *

from mojo.drawingTools import *
from mojo.UI import UpdateCurrentGlyphView
from mojo.events import installTool

import colorsys

def getColor(steps, index, saturation=1):
    return colorsys.hsv_to_rgb(index/(steps*1.0), saturation, 1)

class SparkDigestPen(DigestPointPen):

    # ['beginPath',
    #  ((169, 126), 'line'),
    #  ((169, 97), None),
    #  ((163, 86), None),
    #  ((148, 86), 'curve'),
    #  ((132, 86), None),
    #  ((126, 97), None),
    #  ((126, 126), 'curve'),
    #  ((126, 578), 'line'),
    #  ((126, 607), None),
    #  ((132, 618), None),
    #  ((148, 618), 'curve'),
    #  ((163, 618), None),
    #  ((169, 607), None),
    #  ((169, 578), 'curve'),
    #  'endPath',
    #  'beginPath',
    #  ((292, 32), 'line'),
    #  ((151, 58), 'line'),
    #  ((148, 20), 'line'),
    #  ((236, 20), None),
    #  ((277, 62), None),
    #  ((277, 171), 'curve'),
    #  ((277, 569), 'line'),
    #  ((277, 678), None),
    #  ((235, 720), None),
    #  ((148, 720), 'curve'),
    #  ((60, 720), None),
    #  ((18, 678), None),
    #  ((18, 569), 'curve'),
    #  ((18, 141), 'line'),
    #  ((18, 53), None),
    #  ((47, -6), None),
    #  ((172, -6), 'curve'),
    #  ((285, -40), 'line'),
    #  'endPath']
    def getDigest(self, center=None):
        if center is None:
            return tuple(self._data)
        newData = []
        for item in self._data:
            if type(item)==tuple:
                if type(item[0])==str:
                    # component
                    newData.append(item)
                else:
                    newData.append(((item[0][0]+center,item[0][1]), item[1]))
            else:
                newData.append(item)
        return newData
        

import vanilla

from mojo.extensions import ExtensionBundle
shapeBundle = ExtensionBundle("DesignSpaceEditor")
toolbarIcon = shapeBundle.get("showSparkToolIcon")

"""


    Show Sparks Tool
    
    Let the points of the other masters shine in the background.


"""


class ShowSparksTool(EditingTool):

    showSparkToolPrefsLibKey = "com.letterror.showSparksTool.prefs"
    textAttributes = {
        NSFontAttributeName : NSFont.systemFontOfSize_(10),
        NSForegroundColorAttributeName : NSColor.whiteColor(),
    }
    otherHandleSize = 4
    anchorDotSize = 4
    margin = 3    # how far off are points?
    centeredOnWidth = True
    def setup(self):
        self.okColor = (      0/255.0,      0/255.0,    255/255.0,   0.8)
        self.errorColor = (      255/255.0,      0/255.0,    0/255.0,   0.8)
        self.markerTransparency = 0.5

        self.thisColor = self.okColor
        self.points = []
        self.stuff = []
        self.widths = {}
        self.currentGlyph = None
        self.otherDigests = None
        self.thisDigest = None
        self.presentationHeight = None
            
    def findAllPoints(self):
        # line up the points on the outline
        self.stuff = []
        self.points = []
        _allFonts = AllFonts()[:10]
        g = CurrentGlyph()
        if g is None:
            return
        if g != self.currentGlyph:
            self.currentGlyph = g
            self.otherDigests = []
        f = CurrentFont()
        if f.info.xHeight is not None:
            self.presentationHeight = 0.5*f.info.xHeight
        else:
            self.presentationHeight = 0
        p = SparkDigestPen(f)
        g.drawPoints(p)
        centerWidth = g.width*.5
        self.thisDigest = p.getDigest(center=0)
        if not self.otherDigests:
            for this in _allFonts:
                if this == f:
                    continue
                p = SparkDigestPen(this)
                if not g.name in this:
                    continue
                this[g.name].drawPoints(p) 
                self.otherDigests.append(p.getDigest(center=centerWidth-(this[g.name].width*.5)))
        pathCount = 0
        allDigests = [self.thisDigest]+self.otherDigests
        minLength = min([len(a) for a in allDigests])
        maxLength = max([len(a) for a in allDigests])
        if minLength == maxLength:
            self.thisColor = self.okColor
        else:
            self.thisColor = self.errorColor
        for i in range(minLength):
            cluster = []
            for cmd in [a[i] for a in allDigests]:
                if cmd == "beginPath":
                    continue
                elif cmd == "endPath":
                    continue
                if isinstance(cmd, tuple):
                    pt, what = cmd
                    if isinstance(pt, tuple):
                        cluster.append((pt,cmd,None))
                    else:
                        name = cmd[0]
                        deltaCoord = cmd[1][-2:]
                        boxCoord = (0,0)
                        self.stuff.append((name, deltaCoord, boxCoord))
            self.points.append(cluster)
        
        currentWidth = g.width
        for this in _allFonts:
            w = this[g.name].width
            diff = (currentWidth-w)*0.5
            self.widths[(-diff, 0)] = 1
            self.widths[(g.width+diff, 0)] = 1
                            
    def draw(self, scale):
        self.findAllPoints()
        if not self.points: return
        if scale == 0:
            return
        save()
        shift = 100
        fill(None)
        totalClusters = len(self.points)
        clusterIndex = 0
        for cluster in self.points:
            if len(cluster)>1:
                for i in range(1, len(cluster)):
                    strokeWidth(scale*1)
                    dashLine(2*scale,2*scale)
                    r,g,b = getColor(totalClusters, clusterIndex)
                    stroke(r,g,b,self.markerTransparency)
                    fill(None)
                    lineJoin('round')
                    markerSize = scale * self.otherHandleSize
                    try:
                        line(cluster[0][0], cluster[i][0])
                        if cluster[i][1][1] is None:
                            markerSize = scale * self.otherHandleSize * 2
                    except:
                        pass
                    stroke(None)
                    fill(r,g,b,0.6)
                    pt = cluster[i][0]
                    oval(pt[0]-markerSize, pt[1]-markerSize, markerSize*2, markerSize*2)
            clusterIndex += 1
        pos = {}
        yOffset = 100
        for item in self.stuff:
            if item[1] not in pos:
                pos[item[1]] = []
            pos[item[1]].append(item[0])
            yOffset+=20
        pointIndex = 0
        totalPoints = len(pos)
        for k, v in pos.items():
            # line between text label and anchor dot
            strokeWidth(scale*1.5)
            dashLine(2*scale, 2*scale)
            stroke(0.1,0.1,0.1,0.5)
            fill(None)
            lineJoin('round')
            line((k[0], k[1]+yOffset), (k[0], k[1]))
            # anchor dot
            stroke(None)
            r,g,b = getColor(totalPoints, pointIndex)
            fill(r, g, b, self.markerTransparency)
            d = scale * self.anchorDotSize
            anchorDotSize = 10
            oval(k[0]-d, k[1]-d, d*2, d*2)
            yOffset+=20
            pointIndex += 1
        yOffset = 100
        for k, v in pos.items():
            # text label
            if len(v)==1:
                t = "component: %s %3.0f %3.0f"%(v[0], k[0], k[1])
            else:
                t = "%d x component: %s"%(len(v), v[0])
            self.getNSView()._drawTextAtPoint(
                t,
                self.textAttributes,
                (k[0], k[1]+yOffset),
                0,
                drawBackground=True,
                backgroundColor=NSColor.grayColor())
            yOffset+=20
        # draw the widths at the center of the vertical bounds of the current glyph
        d = 10
        stroke(self.thisColor[0],self.thisColor[1],self.thisColor[2],self.markerTransparency)
        strokeWidth(scale*1)
        dashLine(2*scale, 2*scale)
        fill(None)
        for pt in self.widths.keys():
            line((pt[0], self.presentationHeight-30*scale), (pt[0], self.presentationHeight+30*scale))
        restore()
        
    def mouseDown(self, point, event): pass
        # mods = self.getModifiers()
        # cmd = mods['commandDown'] > 0
        # self.isResizing = False
        # if cmd:
        #     self.clear()
            
    def clear(self):
        self.marked = None
        pass
        # self.pts = []
        # self.dupes = set()
        # self.samples = {}
    
    def keyDown(self, event):
        pass
        # letter = event.characters()
        # if letter == "i":
        #     # invert the paint color on drawing
        #     self.prefs['invert'] = not self.prefs['invert']
        #     self.storePrefs()
        # UpdateCurrentGlyphView()
        
    def mouseDragged(self, point, delta):
        """ Calculate the blurred gray level for this point. """
        pass

    def getToolbarTip(self):
        return 'ShowSparkTool'

    def getToolbarIcon(self):
        ## return the toolbar icon
        return toolbarIcon

    
if __name__ == "__main__":
    from mojo.events import installTool
    p = ShowSparksTool()
    installTool(p)
    