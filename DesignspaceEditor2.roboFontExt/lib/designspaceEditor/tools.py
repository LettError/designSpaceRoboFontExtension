import AppKit
import os
import unicodedata
from contextlib import contextmanager
from vanilla.vanillaBase import osVersionCurrent, osVersion12_0

from mojo.events import postEvent
from mojo.extensions import getExtensionDefault, ExtensionBundle


def holdRecursionDecorator(func):
    """
    A decorator preventing calling the same method inside itself.
    """
    func._holdRecursion = False
    def wrapper(*args, **kwargs):
        if func._holdRecursion:
            return
        func._holdRecursion = True
        func(*args, **kwargs)
        func._holdRecursion = False
    return wrapper


def notificationConductor(func):
    """
    A decorator checking if the controller is on hold and
    if the designspace from the notification is the same as the operator
    """
    def wrapper(self, notification):
        if self.holdChanges:
            return
        if notification["designspace"] == self.operator:
            with self.holdChanges:
                func(self, notification)
    return wrapper


def addToolTipForColumn(listObject, columnIdentifier, tooltip):
    """
    Add a tooltip in an nsColumn header
    """
    nsTableView = listObject.getNSTableView()
    column = nsTableView.tableColumnWithIdentifier_(columnIdentifier)
    column.setHeaderToolTip_(tooltip)


@contextmanager
def TryExcept(controller, action):
    """
    Usage:
    with TryExcept(aWindoController, "Describe the action"):
        # do something
        # when it fails it will show a message in the window controller
    """
    try:
        yield
    except Exception as e:
        controller.showMessage(
            f"{action} failed",
            informativeText=str(e)
        )
    finally:
        pass


class HoldChanges:

    def __init__(self):
        self._hold = 0

    def hold(self):
        self._hold += 1

    def release(self):
        assert self._hold >= 1, "Hold changes cannot be released, call hold() first."
        self._hold -= 1

    def __bool__(self):
        return bool(self._hold)

    def __enter__(self):
        self.hold()
        return self

    def __exit__(self, type, value, traceback):
        self.release()


class SendNotification:

    exitPrefix = {
        "Will": "Did"
    }
    notificationPrefix = "designspaceEditor"

    def __init__(self, who="", prefix="Will", action="Change", **kwargs):
        self.who = who
        self.prefix = prefix
        self.action = action
        self.kwargs = kwargs

    def __enter__(self):
        postEvent(f"{self.notificationPrefix}{self.who}{self.prefix}{self.action}", **self.kwargs)
        return self

    def __exit__(self, type, value, traceback):
        prefix = self.exitPrefix.get(self.prefix)
        if prefix is not None:
            postEvent(f"{self.notificationPrefix}{self.who}{prefix}{self.action}", **self.kwargs)

    def __setitem__(self, key, value):
        self.kwargs[key] = value

    @classmethod
    def single(cls, who="", prefix="Did", action="Change", **kwargs):
        postEvent(f"{cls.notificationPrefix}{who}{prefix}{action}", **kwargs)


class UseVarLib:

    def __init__(self, operator, useVarLib=True):
        self.operator = operator
        self.useVarLib = useVarLib

    def __enter__(self):
        self.previousModel = self.operator.useVarlib
        self.operator.useVarlib = self.useVarLib

    def __exit__(self, type, value, traceback):
        self.operator.useVarlib = self.previousModel


symbolColorMap = dict(
    primary=AppKit.NSColor.labelColor,
    secondary=AppKit.NSColor.secondaryLabelColor
)


def symbolImage(symbolName, color, flipped=False):
    if osVersionCurrent >= osVersion12_0:
        image = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_(symbolName, "")
        if isinstance(color, tuple):
            color = AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(*color)
        else:
            color = symbolColorMap[color]()

        configuration = AppKit.NSImageSymbolConfiguration.configurationWithHierarchicalColor_(
            color
        )
        image = image.imageWithSymbolConfiguration_(configuration)
    else:
        # older systems
        bundle = ExtensionBundle("DesignspaceEditor2")
        image = bundle.getResourceImage(f"toolbar_30_30_{symbolName}")
    if flipped and image:
        image.setFlipped_(True)
    return image


class NumberListFormatter(AppKit.NSFormatter):

    def __new__(cls, *arg, **kwrags):
        self = cls.alloc().init()
        return self

    def stringForObjectValue_(self, obj):
        def formatNumber(value):
            if value == "":
                return ""
            value = float(value)
            if value.is_integer():
                return f"{int(value)}"
            else:
                return f"{value:.3f}"

        if obj is None or isinstance(obj, AppKit.NSNull):
            return " "
        if isinstance(obj, (tuple, list)) and len(obj) == 2:
            # anisotropic
            x, y = obj
            return f"{formatNumber(x)} {formatNumber(y)}"
        return formatNumber(obj)

    def getObjectValue_forString_errorDescription_(self, value, string, error):
        string = str(string)
        string = string.strip()
        if not string:
            return True, 0, error
        try:
            if " " in string:
                parts = string.split(" ")
                if len(parts) == 2:
                    x, y = parts
                    return True, (float(x), float(y)), error
            else:
                return True, float(string), error
        except Exception:
            pass
        return False, string, error


def postScriptNameTransformer(familyName, styleName):
    if familyName is None:
        familyName = ""
    if styleName is None:
        styleName = ""
    def filterPSName(name):
        # Define the set of forbidden characters
        forbidden_chars = set('-[](){}<>/%% ')

        # Normalize the Unicode string to NFKD form
        name = unicodedata.normalize('NFKD', name)

        # Ensure the name is encoded as ASCII
        name = name.encode("ascii", errors="ignore").decode()

        # Filter out forbidden characters
        filtered_name = ''.join(c for c in name if 33 <= ord(c) <= 126 and c not in forbidden_chars)

        return filtered_name

    front = filterPSName(familyName)
    back = filterPSName(styleName)

    # Check if the combined length of front and back exceeds 62 characters
    if len(front) + len(back) >= 62:
        # Reduce the length of front and back to meet the requirement, starting with the front
        while len(front) + len(back) >= 62:
            if len(front) > 31:
                front = front[:-1]  # Remove the last character from front
            elif len(back) > 31: # If the length of front is at least 31, reduce the length of back then
                back = back[:-1]  # Remove the last character from back
            else:
                break

    return "-".join((front, back))

# def identifyingNameTransformer(familyName, styleName):
#     return " ".join((familyName, styleName))


def styleMapNameTransformer(familyName, styleName):
    keyNames = ["Regular", "Italic", "Bold", "Bold Italic"]

    # Check if the styleName ends with any of the keyNames
    for keyName in reversed(keyNames):
        if styleName.endswith(keyName):
            # Check if the preceding word is "Extra", "Semi", or "Demi"... others could be added, but this is a start
            preceding_words = styleName[:-len(keyName)].strip().split()
            if preceding_words and preceding_words[-1] in ["Extra", "Semi", "Demi"]: #TODO: list not exhaustive
                continue
            # Remove the keyName from the styleName
            styleName = styleName[:-len(keyName)].strip()
            # Set the styleMapStyleName to the keyName
            styleMapStyleName = keyName
            break
    else:
        # If no keyName is found, set the styleMapStyleName to "Regular"
        styleMapStyleName = "Regular"

    # Combine the familyName and styleName to create the new familyName
    familyName = f"{familyName} {styleName}".strip()

    return familyName, styleMapStyleName.lower()


def fileNameForInstance(instanceDescriptor):
    filename = postScriptNameTransformer(instanceDescriptor.familyName, instanceDescriptor.styleName)
    return os.path.join(getExtensionDefault('instanceFolderName', 'instances'), f"{filename}.ufo")
