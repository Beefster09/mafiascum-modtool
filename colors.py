
RED     = '\x1b[31m'
YELLOW  = '\x1b[33m'
GREEN   = '\x1b[32m'
CYAN    = '\x1b[36m'
BLUE    = '\x1b[34m'
MAGENTA = '\x1b[35m'

B_RED     = '\x1b[91m'
B_YELLOW  = '\x1b[93m'
B_GREEN   = '\x1b[92m'
B_CYAN    = '\x1b[96m'
B_BLUE    = '\x1b[94m'
B_MAGENTA = '\x1b[95m'

BLACK = '\x1b[30m'
GRAY1 = '\x1b[37m'
GRAY2 = '\x1b[90m'
WHITE = '\x1b[97m'

ALL_COLORS = {
    name.lower(): color
    for name, color in locals().items()
    if not name.startswith('__')
}

BOLD      = '\x1b[1m', '\x1b[21m'
DIM       = '\x1b[2m', '\x1b[22m'
UNDERLINE = '\x1b[4m', '\x1b[24m'
INVERTED  = '\x1b[7m', '\x1b[27m'

ALL_STYLES = {
    name.lower(): color
    for name, color in locals().items()
    if not (name.startswith('__')
            or name == 'ALL_COLORS'
            or name.lower() in ALL_COLORS)
}

CLEAR = '\x1b[0m'

def color(s, c):
    return ''.join([c, s, CLEAR])

class Style:
    __slots__ = '_style', '_close'
    def __init__(self, value='', close=''):
        self._style = value
        self._close = close

    def __call__(self, s, *args, **kwargs):
        if args or kwargs:
            return ''.join([self._style, s.format(*args, **kwargs), self._close])
        else:
            return ''.join([self._style, s, self._close])

    def __getitem__(self, attr):
        if attr in ALL_COLORS:
            return Style(self._style + ALL_COLORS[attr], CLEAR)
        elif attr in ALL_STYLES:
            start, end = ALL_STYLES[attr]
            return Style(self._style + start, end + self._close)
        else:
            raise KeyError(attr)

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(attr)

fmt = format = Style()
