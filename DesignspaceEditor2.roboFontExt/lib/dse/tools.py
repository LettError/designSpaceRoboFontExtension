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
            f"{action} faild",
            informativeText=str(e)
        )
    finally:
        pass
