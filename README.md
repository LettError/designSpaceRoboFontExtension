# DesignSpaceEditor

![Icon](assets/designSpaceFileIcon.png)

A RoboFont extension to create and edit designspace version 5.0 files. For a specification of the **designspace** 5 format go [to the designspace specification at the FontTools repository](https://fonttools.readthedocs.io/en/latest/designspaceLib/index.html).

The extension is capable of:

* Opening, editing and saving existing designspace format 4 and format 5 files.
* Starting new designspace files.
* Opening source UFOs

## Usage

1. Open an existing designspace file or start a new one.
1. Define some axes. Give them useful names.
1. Then load some source UFOs.
1. Then save the document in the same folder as your sources, or one level up. The document will store a relative path to the sources and instances.
1. Define instances and whatever else you need to do.
1. Save.

Yes, I know you can write the xml by hand, but ¯\\\_(ツ)__/¯.


## Toolbar


### Axes
![DSE2 axes icon](assets/toolbar_100_100_icon_axes.png)

Map syntax:

```
# input value > output value
50 > 10
100 > 20
125 > 66
150 > 990
```

Labels syntax:

```
# if it start with ? it will be a localised axis name
# starts with a ? <language tag> <localised string>
? fr 'Chasse'

# <label name> <value>
'Condensed' 50

# optionally add (elidable) or (olderSibling)
'Normal' 100 (elidable) (olderSibling)

# set a range for a label name
# <label name> <min value> <default value> <max value>
'Extra Wide' 150 150 300

# set a range for a label name
'Extra Light' 200 200 250
# add localisations for this 'Extra Light' label
? de 'Extraleicht'
? fr 'Extra léger'
```

### Sources
![DSE2 axes icon](assets/toolbar_100_100_icon_sources.png)

Localised Family Name syntax:

```
# starts with a ? <language tag> <localised string>
? fr 'Montserrat'
? ja 'モンセラート'
```

Muted Glyph syntax:

```
# a space separated list of glyph names
a b c d
```

### Rules
![DSE2 axes icon](assets/toolbar_100_100_icon_rules.png)

Rules syntax:

```
# a comment
# name of the rule
switching a's
	# a list of source glyph > substituted glyph	a > a.alt
	agrave > agrave.alt
	
	# conditions
	# <axis name> startRange-endRange
	# a condition set with two conditions
	weight 800-1000 width 200-1000
	optical 500-1000	
```

### Labels
![DSE2 axes icon](assets/toolbar_100_100_icon_labels.png)

Location Labels syntax:

```
# styleName
Some Style
	# optionally localisation
	# starts with a ? <language tag> <localised string>
	?  fr  "Un Style"
	# optionally translation
	?  fr  "Un Style"
	# location name if the axis and value
	weight 300
	width 40
	Italic 1
	boldness 30
```

### Problems
![DSE2 axes icon](assets/toolbar_100_100_icon_problems.png)

### History

* 1.0 Initial commit
* 1.1 Fixes a mistake with packaging.
* 1.3.2 UFO paths are editable.
* 1.3.3 Updated designSpaceDocument.
* 1.3.5 Updated designSpaceDocument. ShowSparksTool added.
* 1.3.6 Updated designSpaceDocument. ShowSparksTool made independent.
* 1.9.6
	* Update of this readme
	* Resizable columns thanks [@ryanbugden](https://github.com/ryanbugden)!
	* Quick defaults for axes
	* Replace UFO button
	* Automatic update of UFO name based on `familyName-styleName.ufo`
* 2.0 Rewrite for designspace 5.0 specification
