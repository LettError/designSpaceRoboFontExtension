# -*- coding: utf-8 -*-

from AppKit import NSColor, NSFont, NSFontAttributeName, NSForegroundColorAttributeName, NSCursor
from mojo.events import installTool, EditingTool, BaseEventTool, setActiveEventTool
from defconAppKit.windows.baseWindow import BaseWindowController
from robofab.pens.digestPen import DigestPointPen
from robofab.world import *

from mojo.drawingTools import *
from mojo.UI import UpdateCurrentGlyphView
from mojo.events import installTool



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
        self.thisColor = self.okColor
        self.points = []
        self.stuff = []
        self.anchors = {}
        self.currentGlyph = None
        self.otherDigests = None
        self.thisDigest = None
            
    def findAllPoints(self):
        # line up the points on the outline
        self.anchors = {}
        self.stuff = []
        self.points = []
        _allFonts = AllFonts()
        g = CurrentGlyph()
        if g is None:
            return
        if g != self.currentGlyph:
            self.currentGlyph = g
            self.otherDigests = []
        f = CurrentFont()
        p = DigestPointPen(f)
        g.drawPoints(p)
        self.thisDigest = p.getDigest()
        if not self.otherDigests:
            for this in _allFonts:
                if this == f:
                    continue
                p = DigestPointPen(this)
                if not g.name in this:
                    continue
                this[g.name].drawPoints(p) 
                self.otherDigests.append(p.getDigest())
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
            nextPoint = None
            for cmd in [a[i] for a in allDigests]:
                if cmd == "beginPath":
                    continue
                elif cmd == "endPath":
                    continue
                if isinstance(cmd, tuple):
                    pt, what = cmd
                    if isinstance(pt, tuple):
                        cluster.append((pt,cmd,nextPoint))
                        nextPoint = None
                    else:
                        name = cmd[0]
                        deltaCoord = cmd[1][-2:]
                        boxCoord = (0,0)
                        self.stuff.append((name, deltaCoord, boxCoord))
            self.points.append(cluster)
        
        # check the anchors
        for a in g.anchors:
            if not a.name in self.anchors:
                self.anchors[a.name] = []
            self.anchors[a.name].append(a)
            # check for anchors with duplicate names?
        for this in _allFonts:
            if this == f:
                continue
            for a in this[g.name].anchors:
                if not a.name in self.anchors:
                    self.anchors[a.name] = []
                self.anchors[a.name].append(a)
        #print self.stuff

            
    def draw(self, scale):
        self.findAllPoints()
        if not self.points: return
        if scale == 0:
            return
        save()
        shift = 100
        fill(None)
        for cluster in self.points:
            if len(cluster)>1:
                for i in range(1, len(cluster)):
                    strokeWidth(scale*1)
                    dashLine(2*scale,2*scale)
                    stroke(self.thisColor[0],self.thisColor[1],self.thisColor[2],0.7)
                    fill(None)
                    lineJoin('round')
                    try:
                        line(cluster[0][0], cluster[i][0])
                    except:
                        pass
                    stroke(None)
                    fill(self.thisColor[0],self.thisColor[1],self.thisColor[2],0.7)
                    pt = cluster[i][0]
                    d = scale * self.otherHandleSize
                    oval(pt[0]-d, pt[1]-d, d*2, d*2)
        pos = {}
        yOffset = 100
        for item in self.stuff:
            if item[1] not in pos:
                pos[item[1]] = []
            pos[item[1]].append(item[0])
            yOffset+=20
        yOffset = 100
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
            fill(self.thisColor[0],self.thisColor[1],self.thisColor[2],0.7)
            d = scale * self.anchorDotSize
            anchorDotSize = 10
            oval(k[0]-d, k[1]-d, d*2, d*2)
            yOffset+=20
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
        restore()
        # UpdateCurrentGlyphView()
        
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
    