ALL_COLORS = {
    'red':       '\x1b[31m',
    'yellow':    '\x1b[33m',
    'green':     '\x1b[32m',
    'cyan':      '\x1b[36m',
    'blue':      '\x1b[34m',
    'magenta':   '\x1b[35m',

    'b_red':     '\x1b[91m',
    'b_yellow':  '\x1b[93m',
    'b_green':   '\x1b[92m',
    'b_cyan':    '\x1b[96m',
    'b_blue':    '\x1b[94m',
    'b_magenta': '\x1b[95m',

    'black':     '\x1b[30m',
    'gray1':     '\x1b[37m',
    'gray2':     '\x1b[90m',
    'white':     '\x1b[97m',
}

ALL_STYLES = {
    'bold':      ('\x1b[1m', '\x1b[21m'),
    'dim':       ('\x1b[2m', '\x1b[22m'),
    'underline': ('\x1b[4m', '\x1b[24m'),
    'inverted':  ('\x1b[7m', '\x1b[27m'),
}

for name, color in ALL_COLORS.items():
    globals()[name.upper()] = color

for name, (start, end) in ALL_STYLES.items():
    globals()[name.upper()] = start
    globals()[name.upper() + "_END"] = end

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
