from mojo.subscriber import Subscriber, registerGlyphEditorSubscriber, registerCurrentFontSubscriber, registerRoboFontSubscriber

from designspaceEditor.tools import SendNotification


_operatorRegistry = []


def registerOperator(operator):
    if operator not in _operatorRegistry:
        _operatorRegistry.append(operator)


def unregisterOperator(operator):
    if operator in _operatorRegistry:
        _operatorRegistry.remove(operator)


def notifyOperator(font, who, action="Change", operatorMethod="changed", operatorKwargs=dict(), notificationKwargs=dict()):
    for operator in _operatorRegistry:
        for sourceDescriptor in operator.sources:
            if sourceDescriptor.path == font.path:
                if operatorMethod:
                    callback = getattr(operator, operatorMethod)
                    callback(**operatorKwargs)
                SendNotification.single(who=who, action=action, **notificationKwargs)
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
