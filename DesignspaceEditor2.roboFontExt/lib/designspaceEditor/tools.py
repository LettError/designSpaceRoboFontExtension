from contextlib import contextmanager


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
