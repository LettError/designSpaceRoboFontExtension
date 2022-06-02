from pygments.lexer import RegexLexer, include, bygroups
from pygments.lexers.special import TextLexer
from pygments.token import *


class DesignspaceLexer(RegexLexer):
    name = "Designspace"
    aliases = ['designspace']
    filenames = ['*.Designspace']

    tokens = {
        'root': [
            (r'\n', Text),
            (r'#.*$', Comment),
            (r'[\'|\"].*[\'|\"]', String),
            (r'(\?)\s+((?:[a-zA-Z0-9\-]+))\s+', bygroups(Name.Builtin, Name.Variable)),
            (r'\((elidable|olderSibling)\)', Name.Variable),
            (r'\[([0-9\.]+)\]', Name.Variable),
            (r'\>|\?|\-|\*', Name.Builtin),
            include('numbers'),
            (r'^[^\s].*$', Keyword.Namespace),  # Name.Class
            (r'(weight|width|italic|optical|slant)\b', Keyword),
            (r'[\w\.\*\+\-\:\^\|\~]+', Text),
        ],
        'numbers': [
            (r'(\d+\.\d*|\d*\.\d+)([eE][+-]?[0-9]+)?j?', Number.Float),
            (r'\d+[eE][+-]?[0-9]+j?', Number.Float),
            (r'0[0-7]+j?', Number.Oct),
            (r'0[xX][a-fA-F0-9]+', Number.Hex),
            (r'\d+L', Number.Integer.Long),
            (r'\d+j?', Number.Integer)
        ]
    }
