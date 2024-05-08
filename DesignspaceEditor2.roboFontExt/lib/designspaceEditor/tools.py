import AppKit
from contextlib import contextmanager
from vanilla.vanillaBase import osVersionCurrent, osVersion12_0

from mojo.events import postEvent
from mojo.extensions import ExtensionBundle


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
    def single(self, who="", prefix="Did", action="Change", **kwargs):
        postEvent(f"{self.notificationPrefix}{who}{prefix}{action}", **kwargs)


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
