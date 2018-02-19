import colorsys

BASIC_COLORS = {
    # === FG COLORS ===
    'red':     '\x1b[31m',
    'yellow':  '\x1b[33m',
    'green':   '\x1b[32m',
    'cyan':    '\x1b[36m',
    'blue':    '\x1b[34m',
    'magenta': '\x1b[35m',

    'Red':     '\x1b[91m',
    'Yellow':  '\x1b[93m',
    'Green':   '\x1b[92m',
    'Cyan':    '\x1b[96m',
    'Blue':    '\x1b[94m',
    'Magenta': '\x1b[95m',

    'black':   '\x1b[30m',
    'vanilla': '\x1b[37m',
    'gray':    '\x1b[90m',
    'white':   '\x1b[97m',

    # === BG COLORS ===
    'bg_red':     '\x1b[41m',
    'bg_yellow':  '\x1b[43m',
    'bg_green':   '\x1b[42m',
    'bg_cyan':    '\x1b[46m',
    'bg_blue':    '\x1b[44m',
    'bg_magenta': '\x1b[45m',

    'bg_Red':     '\x1b[101m',
    'bg_Yellow':  '\x1b[103m',
    'bg_Green':   '\x1b[102m',
    'bg_Cyan':    '\x1b[106m',
    'bg_Blue':    '\x1b[104m',
    'bg_Magenta': '\x1b[105m',

    'bg_black':   '\x1b[40m',
    'bg_vanilla': '\x1b[47m',
    'bg_gray':    '\x1b[100m',
    'bg_white':   '\x1b[107m',
}

STYLES = {
    'bold':      ('\x1b[1m', '\x1b[21m'),
    'dim':       ('\x1b[2m', '\x1b[22m'),
    'underline': ('\x1b[4m', '\x1b[24m'),
    'inverted':  ('\x1b[7m', '\x1b[27m'),
}

CLEAR = '\x1b[0m'

def color(s, c):
    return ''.join([c, str(s), CLEAR])

def color256(s, c):
    return '\x1b[38;5;{}m{}\x1b[0m'.format(c, s)

def fg256(c):
    return '\x1b[38;5;{}m'.format(int(c))

def bg256(c):
    return '\x1b[48;5;{}m'.format(int(c))

def rgb6_to_256color_index(r, g, b):
    r = min(max(round(r - 0.5), 0), 5)
    g = min(max(round(g - 0.5), 0), 5)
    b = min(max(round(b - 0.5), 0), 5)
    return 16 + int(r) * 36 + int(g) * 6 + int(b)

def rgb6_to_256color(r, g, b):
    return fg256(rgb6_to_256color_index(r, g, b))

def rgb_to_256color_index(r, g, b, radix=256):
    r /= radix
    g /= radix
    b /= radix
    gray = (r + g + b) / 3
    err = (abs(gray - r) + abs(gray - g) + abs(gray - b)) / 3
    if err < 1 / 24:
        return int(232 + gray * 24)
    else:
        return rgb6_to_256color_index(r * 6, g * 6, b * 6)

def rgb_to_256color(r, g, b, radix=256):
    return fg256(rgb_to_256color_index(r, g, b, radix))

def hex_to_256color_index(hexcolor):
    if hexcolor.startswith('#'):
        hexcolor = hexcolor[1:]
    assert len(hexcolor) % 3 == 0
    d = len(hexcolor) // 3
    return rgb_to_256color_index(
        *[int(hexcolor[s:s+d], 16) for s in range(0, len(hexcolor), d)],
        radix=16**d)

def hex_to_256color(hexcolor):
    return fg256(hex_to_256color_index(hexcolor))

def hsv_to_256color_index(h, s, v):
    return rgb_to_256color_index(*colorsys.hsv_to_rgb(h, s, v), radix=1)

def hsv_to_256color(h, s, v):
    return fg256(hsv_to_256color_index(h, s, v))

def hsl_to_256color_index(h, s, l):
    return rgb_to_256color_index(*colorsys.hls_to_rgb(h, l, s), radix=1)

def hsl_to_256color(h, s, l):
    return fg256(hsl_to_256color_index(h, s, l))

LAST = object()
class Style:
    __slots__ = '_style'

    STYLE_CONTEXT = [] # global stack for style context
    def __init__(self, value=''):
        self._style = value

    def __call__(self, s, *args, **kwargs):
        if args or kwargs:
            return ''.join([self._style, str(s).format(*args, **kwargs), CLEAR,
                            *self.STYLE_CONTEXT])
        else:
            return ''.join([self._style, str(s), CLEAR, *self.STYLE_CONTEXT])

    def __getitem__(self, style):
        if style in BASIC_COLORS:
            return Style(self._style + BASIC_COLORS[style])
        if style in STYLES:
            start, end = STYLES[style]
            return Style(self._style + start)
        elif isinstance(style, int):
            if 0 <= style < 256:
                return Style(self._style + fg256(style))
            elif -256 < style < 0:
                return Style(self._style + bg256(-style))
            elif style == -256:
                return Style(self._style + bg256(0))
            else:
                raise ValueError(style)
        elif isinstance(style, float):
            if style >= 0:
                return Style(self._style + fg256(int(min(style, 0.99) * 24) + 232))
            else:
                return Style(self._style + bg256(int(min(-style, 0.99) * 24) + 232))
        elif isinstance(style, tuple):
            return Style(self._style + rgb6_to_256color(*style))
        elif style.startswith('#'):
            return Style(self._style + hex_to_256color(style))
        elif style.startswith('-#'):
            return Style(self._style + bg256(hex_to_256color_index(style[1:])))
        else:
            raise KeyError(style)

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(attr)

    def hsv(self, h, s, v):
        return Style(self._style + hsv_to_256color(h / 360, s, v))

    def hsl(self, h, s, l):
        return Style(self._style + hsl_to_256color(h / 360, s, l))

    def bg_hsv(self, h, s, v):
        return Style(self._style + bg256(hsv_to_256color_index(h / 360, s, v)))

    def bg_hsl(self, h, s, l):
        return Style(self._style + bg256(hsl_to_256color_index(h / 360, s, l)))

    @property
    def clear(self):
        return Style(CLEAR)

    def __enter__(self):
        self.STYLE_CONTEXT.append(self._style)
        print(self._style, end='')

    def __exit__(self, t, b, tb):
        self.STYLE_CONTEXT.pop()
        print(CLEAR, *self.STYLE_CONTEXT, sep='', end='')
        return False

fmt = format = Style()

if __name__ == '__main__':
    import sys

    if len(sys.argv) <= 1:
        with fmt.underline.hsv(40, 0.8, 0.4):
            print("Should be brown and underlined")
            with fmt.bold.hsl(200, 1, 0.8):
                print("Should be sky blue, bold, and underlined")
                print(fmt.clear.bg_yellow.black("Just black on yellow"))
                print("Should also be bold underlined sky blue")
            print("underlined brown")

    elif sys.argv[1] == 'index':
        for c in range(16):
            print(color256(c, c))
        print()
        for r in range(6):
            for g in range(6):
                base = r * 36 + g * 6 + 16
                print('\t'.join(color256(base + b, base + b) for b in range(6)))
            print()
        for c in range(232, 256):
            print(color256(c, c))

    elif sys.argv[1] == 'hsv':
        for s in range(6):
            H = s * 6 + 1
            for h in range(H):
                print(' '.join([
                    color(hex(hsv_to_256color_index(h / H, s / 6, v / 24))[2:],
                          hsv_to_256color(h / H, s / 6, v / 24))
                    for v in reversed(range(24))
                ]))
            print()

    elif sys.argv[1] == 'hsl':
        L = 12
        S = 5
        for h in range(0, 360, 10):
            for l in range(L):
                print('\t'.join([
                    color(hsl_to_256color_index(h / 360, s / S, l / L),
                          hsl_to_256color(h / 360, s / S, l / L))
                    for s in range(S + 1)
                ]))
            print()
