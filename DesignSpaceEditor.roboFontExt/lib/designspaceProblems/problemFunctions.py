# generated from problems.py
from errors import DesignSpaceProblem
def fileCorruptProblem(**kwargs):
    # file corrupt, (0, 0)
    return DesignSpaceProblem(0,0,data=kwargs)

def noAxesDefinedProblem(**kwargs):
    # no axes defined, (1, 0)
    return DesignSpaceProblem(1,0,data=kwargs)

def axisMissingProblem(**kwargs):
    # axis missing, (1, 1)
    return DesignSpaceProblem(1,1,data=kwargs)

def axisMaximumMissingProblem(**kwargs):
    # axis maximum missing, (1, 2)
    return DesignSpaceProblem(1,2,data=kwargs)

def axisMinimumMissingProblem(**kwargs):
    # axis minimum missing, (1, 3)
    return DesignSpaceProblem(1,3,data=kwargs)

def axisDefaultMissingProblem(**kwargs):
    # axis default missing, (1, 4)
    return DesignSpaceProblem(1,4,data=kwargs)

def axisNameMissingProblem(**kwargs):
    # axis name missing, (1, 5)
    return DesignSpaceProblem(1,5,data=kwargs)

def axisTagMissingProblem(**kwargs):
    # axis tag missing, (1, 6)
    return DesignSpaceProblem(1,6,data=kwargs)

def axisTagMismatchProblem(**kwargs):
    # axis tag mismatch, (1, 7)
    return DesignSpaceProblem(1,7,data=kwargs)

def mappingTableHasOverlapsProblem(**kwargs):
    # mapping table has overlaps, (1, 8)
    return DesignSpaceProblem(1,8,data=kwargs)

def minimumAndMaximumValueAreTheSameProblem(**kwargs):
    # minimum and maximum value are the same, (1, 9)
    return DesignSpaceProblem(1,9,data=kwargs)

def defaultNotBetweenMinimumAndMaximumProblem(**kwargs):
    # default not between minimum and maximum, (1, 10)
    return DesignSpaceProblem(1,10,data=kwargs)

def noSourcesDefinedProblem(**kwargs):
    # no sources defined, (2, 0)
    return DesignSpaceProblem(2,0,data=kwargs)

def sourceUFOMissingProblem(**kwargs):
    # source UFO missing, (2, 1)
    return DesignSpaceProblem(2,1,data=kwargs)

def sourceUFOFormatTooOldProblem(**kwargs):
    # source UFO format too old, (2, 2)
    return DesignSpaceProblem(2,2,data=kwargs)

def sourceLayerMissingProblem(**kwargs):
    # source layer missing, (2, 3)
    return DesignSpaceProblem(2,3,data=kwargs)

def sourceLocationMissingProblem(**kwargs):
    # source location missing, (2, 4)
    return DesignSpaceProblem(2,4,data=kwargs)

def sourceLocationHasValueForUndefinedAxisProblem(**kwargs):
    # source location has value for undefined axis, (2, 5)
    return DesignSpaceProblem(2,5,data=kwargs)

def sourceLocationHasOutOfBoundsValueProblem(**kwargs):
    # source location has out of bounds value, (2, 6)
    return DesignSpaceProblem(2,6,data=kwargs)

def noSourceOnDefaultLocationProblem(**kwargs):
    # no source on default location, (2, 7)
    return DesignSpaceProblem(2,7,data=kwargs)

def multipleSourcesOnDefaultLocationProblem(**kwargs):
    # multiple sources on default location, (2, 8)
    return DesignSpaceProblem(2,8,data=kwargs)

def multipleSourcesOnLocationProblem(**kwargs):
    # multiple sources on location, (2, 9)
    return DesignSpaceProblem(2,9,data=kwargs)

def sourceLocationIsAnisotropicProblem(**kwargs):
    # source location is anisotropic, (2, 10)
    return DesignSpaceProblem(2,10,data=kwargs)

def instanceLocationMissingProblem(**kwargs):
    # instance location missing, (3, 1)
    return DesignSpaceProblem(3,1,data=kwargs)

def instanceLocationHasValueForUndefinedAxisProblem(**kwargs):
    # instance location has value for undefined axis, (3, 2)
    return DesignSpaceProblem(3,2,data=kwargs)

def instanceLocationHasOutOfBoundsValueProblem(**kwargs):
    # instance location has out of bounds value, (3, 3)
    return DesignSpaceProblem(3,3,data=kwargs)

def multipleInstancesOnLocationProblem(**kwargs):
    # multiple instances on location, (3, 4)
    return DesignSpaceProblem(3,4,data=kwargs)

def instanceLocationIsAnisotropicProblem(**kwargs):
    # instance location is anisotropic, (3, 5)
    return DesignSpaceProblem(3,5,data=kwargs)

def missingFamilyNameProblem(**kwargs):
    # missing family name, (3, 6)
    return DesignSpaceProblem(3,6,data=kwargs)

def missingStyleNameProblem(**kwargs):
    # missing style name, (3, 7)
    return DesignSpaceProblem(3,7,data=kwargs)

def missingOutputPathProblem(**kwargs):
    # missing output path, (3, 8)
    return DesignSpaceProblem(3,8,data=kwargs)

def duplicateInstancesProblem(**kwargs):
    # duplicate instances, (3, 9)
    return DesignSpaceProblem(3,9,data=kwargs)

def noInstancesDefinedProblem(**kwargs):
    # no instances defined, (3, 10)
    return DesignSpaceProblem(3,10,data=kwargs)

def differentNumberOfContoursInGlyphProblem(**kwargs):
    # different number of contours in glyph, (4, 0)
    return DesignSpaceProblem(4,0,data=kwargs)

def differentNumberOfComponentsInGlyphProblem(**kwargs):
    # different number of components in glyph, (4, 1)
    return DesignSpaceProblem(4,1,data=kwargs)

def differentNumberOfAnchorsInGlyphProblem(**kwargs):
    # different number of anchors in glyph, (4, 2)
    return DesignSpaceProblem(4,2,data=kwargs)

def differentNumberOfOncurvePointsOnContourProblem(**kwargs):
    # different number of on-curve points on contour, (4, 3)
    return DesignSpaceProblem(4,3,data=kwargs)

def differentNumberOfOffcurvePointsOnContourProblem(**kwargs):
    # different number of off-curve points on contour, (4, 4)
    return DesignSpaceProblem(4,4,data=kwargs)

def curveHasWrongTypeProblem(**kwargs):
    # curve has wrong type, (4, 5)
    return DesignSpaceProblem(4,5,data=kwargs)

def nondefaultGlyphIsEmptyProblem(**kwargs):
    # non-default glyph is empty, (4, 6)
    return DesignSpaceProblem(4,6,data=kwargs)

def defaultGlyphIsEmptyProblem(**kwargs):
    # default glyph is empty, (4, 7)
    return DesignSpaceProblem(4,7,data=kwargs)

def contourHasWrongDirectionProblem(**kwargs):
    # contour has wrong direction, (4, 8)
    return DesignSpaceProblem(4,8,data=kwargs)

def incompatibleConstructionsForGlyphProblem(**kwargs):
    # incompatible constructions for glyph, (4, 9)
    return DesignSpaceProblem(4,9,data=kwargs)

def noKerningInSourceProblem(**kwargs):
    # no kerning in source, (5, 0)
    return DesignSpaceProblem(5,0,data=kwargs)

def noKerningInDefaultProblem(**kwargs):
    # no kerning in default, (5, 1)
    return DesignSpaceProblem(5,1,data=kwargs)

def kerningGroupMembersDoNotMatchProblem(**kwargs):
    # kerning group members do not match, (5, 2)
    return DesignSpaceProblem(5,2,data=kwargs)

def kerningGroupMissingInDefaultProblem(**kwargs):
    # kerning group missing in default, (5, 3)
    return DesignSpaceProblem(5,3,data=kwargs)

def kerningPairMissingProblem(**kwargs):
    # kerning pair missing, (5, 4)
    return DesignSpaceProblem(5,4,data=kwargs)

def noKerningGroupsInDefaultProblem(**kwargs):
    # no kerning groups in default, (5, 5)
    return DesignSpaceProblem(5,5,data=kwargs)

def noKerningGroupsInSourceProblem(**kwargs):
    # no kerning groups in source, (5, 6)
    return DesignSpaceProblem(5,6,data=kwargs)

def defaultFontInfoMissingValueForUnitsPerEmProblem(**kwargs):
    # default font info missing value for units per em, (6, 0)
    return DesignSpaceProblem(6,0,data=kwargs)

def defaultFontInfoMissingValueForAscenderProblem(**kwargs):
    # default font info missing value for ascender, (6, 1)
    return DesignSpaceProblem(6,1,data=kwargs)

def defaultFontInfoMissingValueForDescenderProblem(**kwargs):
    # default font info missing value for descender, (6, 2)
    return DesignSpaceProblem(6,2,data=kwargs)

def defaultFontInfoMissingValueForXheightProblem(**kwargs):
    # default font info missing value for xheight, (6, 3)
    return DesignSpaceProblem(6,3,data=kwargs)

def sourceFontUnitsPerEmValueDifferentFromDefaultUnitsPerEmProblem(**kwargs):
    # source font unitsPerEm value different from default unitsPerEm, (6, 4)
    return DesignSpaceProblem(6,4,data=kwargs)

def sourceGlyphMissingProblem(**kwargs):
    # source glyph missing, (7, 0)
    return DesignSpaceProblem(7,0,data=kwargs)

def destinationGlyphMissingProblem(**kwargs):
    # destination glyph missing, (7, 1)
    return DesignSpaceProblem(7,1,data=kwargs)

def sourceAndDestinationGlyphsTheSameProblem(**kwargs):
    # source and destination glyphs the same, (7, 2)
    return DesignSpaceProblem(7,2,data=kwargs)

def noSubstitionGlyphsDefinedProblem(**kwargs):
    # no substition glyphs defined, (7, 3)
    return DesignSpaceProblem(7,3,data=kwargs)

def noConditionsetDefinedProblem(**kwargs):
    # no conditionset defined, (7, 4)
    return DesignSpaceProblem(7,4,data=kwargs)

def conditionValuesOnUnknownAxisProblem(**kwargs):
    # condition values on unknown axis, (7, 5)
    return DesignSpaceProblem(7,5,data=kwargs)

def conditionValuesOutOfAxisBoundsProblem(**kwargs):
    # condition values out of axis bounds, (7, 6)
    return DesignSpaceProblem(7,6,data=kwargs)

def conditionValuesAreTheSameProblem(**kwargs):
    # condition values are the same, (7, 7)
    return DesignSpaceProblem(7,7,data=kwargs)

def duplicateConditionsProblem(**kwargs):
    # duplicate conditions, (7, 8)
    return DesignSpaceProblem(7,8,data=kwargs)
