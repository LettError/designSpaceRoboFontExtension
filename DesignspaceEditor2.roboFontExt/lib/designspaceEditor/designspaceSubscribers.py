import AppKit
from objc import python_method, super

from lib.tools.debugTools import ClassNameIncrementer

from mojo.subscriber import Subscriber, registerGlyphEditorSubscriber, registerCurrentFontSubscriber, registerRoboFontSubscriber

from designspaceEditor.tools import SendNotification


class OperatorRegistry(AppKit.NSObject, metaclass=ClassNameIncrementer):

    def init(self):
        self = super().init()
        self.operators = []
        self.currentOperator = None

        center = AppKit.NSNotificationCenter.defaultCenter()
        center.addObserver_selector_name_object_(self, "windowBecomeMain:", AppKit.NSWindowDidBecomeMainNotification, None)
        center.addObserver_selector_name_object_(self, "windowResignMain:", AppKit.NSWindowDidResignMainNotification, None)
        return self

    @python_method
    def append(self, operator):
        if operator not in self.operators:
            self.operators.append(operator)

    @python_method
    def remove(self, operator):
        if operator in self.operators:
            self.operators.remove(operator)

    def windowBecomeMain_(self, notification):
        window = notification.object()
        delegate = window.delegate()
        if hasattr(delegate, "vanillaWrapper"):
            controller = delegate.vanillaWrapper()
            if controller.__class__.__name__ == "DesignspaceEditorController":
                self.updateCurrentDesignspace_(controller.operator)

    def windowResignMain_(self, notification):
        window = notification.object()
        delegate = window.delegate()
        if hasattr(delegate, "vanillaWrapper"):
            controller = delegate.vanillaWrapper()
            if controller.__class__.__name__ == "DesignspaceEditorController":
                self.updateCurrentDesignspace_(controller.operator)

    def updateCurrentDesignspace_(self, operator):
        if operator != self.currentOperator:
            if self.currentOperator is not None:
                SendNotification.single(action="ResignCurrent", designspace=self.currentOperator)
            if operator is not None:
                SendNotification.single(action="BecomeCurrent", designspace=operator)
            self.currentOperator = operator


_operatorRegistry = OperatorRegistry.alloc().init()


def registerOperator(operator):
    _operatorRegistry.append(operator)


def unregisterOperator(operator):
    _operatorRegistry.remove(operator)


def notifyOperator(font, who, action="Change", operatorMethod="changed", operatorKwargs=dict(), notificationKwargs=dict()):
    for operator in _operatorRegistry.operators:
        for sourceDescriptor in operator.sources:
            if sourceDescriptor.path == font.path:
                if operatorMethod:
                    callback = getattr(operator, operatorMethod)
                    callback(**operatorKwargs)
                SendNotification.single(who=who, action=action, designspace=operator, **notificationKwargs)
                return


class DesignspaceEditorPreviewGlyphSubscriber(Subscriber):

    debug = True

    operators = []

    def glyphDidChange(self, info):
        glyph = info["glyph"]
        font = glyph.font
        notifyOperator(
            font,
            who="SourceGlyph",
            operatorMethod="glyphChanged",
            operatorKwargs=dict(
                glyphName=glyph.name,
                includeDependencies=True
            ),
            notificationKwargs=dict(
                glyph=glyph
            )
        )


class DesignspaceEditorCurrentFontSubscriber(Subscriber):

    debug = True

    def currentFontInfoDidChange(self, info):
        font = info["font"]
        notifyOperator(
            font,
            who="SourceInfo",
            notificationKwargs=dict(
                font=font
            )
        )

    def currentFontKerningDidChange(self, info):
        font = info["font"]
        notifyOperator(
            font,
            who="SourceKerning",
            notificationKwargs=dict(
                font=font
            )
        )

    def currentFontGroupsDidChange(self, info):
        font = info["font"]
        notifyOperator(
            font,
            who="SourceGroups",
            notificationKwargs=dict(
                font=font
            )
        )


class DesignspaceEditorFontDocumentSubscriber(Subscriber):

    debug = True

    def fontDocumentDidChangeExternally(self, info):
        font = info["font"]
        notifyOperator(
            font,
            who="SourceFont",
            action="ChangedExternally",
            notificationKwargs=dict(
                font=font
            )
        )


registerGlyphEditorSubscriber(DesignspaceEditorPreviewGlyphSubscriber)
registerCurrentFontSubscriber(DesignspaceEditorCurrentFontSubscriber)
registerRoboFontSubscriber(DesignspaceEditorFontDocumentSubscriber)
