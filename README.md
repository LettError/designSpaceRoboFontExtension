
![DSE2 location labels icon](assets/toolbar_500_500_icon_location_labels.png)

DesignSpaceEditor2
==================

An extension for RoboFont 4.4+ to create and edit designspaces format 4 and 5. Labels, variable fonts, mappings can be edited in a compact syntax, examples on this page. For the **designspace** 5 format go [to the specification at FontTools](https://fonttools.readthedocs.io/en/latest/designspaceLib/index.html).

This extension can:

*   DesignSpaceEditor2 is for very recent RoboFont 4.4+ only.
*   Open, edit and save existing designspace format 4 and format 5 files.
*   Support discrete axes.
*   You can start a new designspace.
*   You can edit all sorts of labels and localisations.
*   You can open source UFOs.
*   Validate designspaces and point out compatibility and structural issues.
*   DesignspaceEditor2 sends designspace-related notifications.

Please refer to the documentation in the DSE extension. Click the (?) button
![](DesignspaceEditor2.roboFontExt/resources/anisotropic_instance_marked.jpg).

```python
# example of CurrentDesignspace()
```

## Scripting with the current designspace

With a document open in DesignspaceEditor you can call `CurrentDesignspace()`, similar to `CurrentFont()` and `CurrentGlyph()``. This returns the designspace wrapped in a `UFOOperator` object that can handle all the glyph interpolations, font info, kerning etc.

### Calculating a glyph

The example below calculates a single glyph at the default location. It returns a mathGlyph.

```python
d = CurrentDesignspace()
d.loadFonts()
loc = d.newDefaultLocation()
g = d.makeOneGlyph("A", location=loc)
```

### Calculating kerning and info

The example below calculates a single kerning pair and an info object. The `makeOneKerning` method accepts a list of pairs to calculate. If no pairs are given, all pairs will be calculated.

```python
d = CurrentDesignspace()
d.loadFonts()
loc = d.newDefaultLocation()

pairs = [('public.kern1.i', 'public.kern2.b')]
kern = d.makeOneKerning(loc, pairs)
print(kern.items())

info = d.makeOneInfo(loc)
print(info)
```
### Calculating an instance and drawing in Drawbot

With the Drawbot extension in RoboFont, you can call `CurrentDesignspace()` and draw interpolated glyphs. 

```python
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
        g = d.makeOneGlyph("A", location=loc)
        bp = BezierPath()
        g.draw(bp)
        drawPath(bp)
```

[more examples to follow]
