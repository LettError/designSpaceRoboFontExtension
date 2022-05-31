# DesignSpaceEditor

![Icon](assets/designSpaceFileIcon.png)

A RoboFont extension to create and edit designspace version 5 files. For a specification of the **designspace** format go [to the designspace specification at the FontTools repository](https://fonttools.readthedocs.io/en/latest/designspaceLib/readme.html).

* Open, edit and save existing designspace files.
* Start new designspace files.
* Open source UFOs

## Usage
1. Open an existing designspace file or start a new one.
1. Define some axes. Give them useful names.
1. Then load some source UFOs.
1. Then save the document in the same folder as your sources, or one level up. The document will store a relative path to the sources and instances.
1. Define instances and whatever else you need to do.
1. Save. 

Yes, I know you can write the xml by hand, 
but ¯\\\_(ツ)__/¯.


## Toolbar


## Sources

## Rules

## Problems

## History

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
* 2.0 Rewrite with designpspace 5.0 spec
