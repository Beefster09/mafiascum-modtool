import colorsys
import sys
import os
import platform

def clamp(x, lo, hi):
    if x < lo: return lo
    elif x > hi: return hi
    else: return x

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
    'silver':  '\x1b[37m',
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
    'bg_silver':  '\x1b[47m',
    'bg_gray':    '\x1b[100m',
    'bg_white':   '\x1b[107m',
}

STYLES = {
    'bold':      '\x1b[1m',
    'dim':       '\x1b[2m',
    'underline': '\x1b[4m',
    'inverted':  '\x1b[7m',
}

CLEAR = '\x1b[0m'

# === Control Codes ===

def _fg256(c):
    return '\x1b[38;5;{}m'.format(int(c))

def _bg256(c):
    return '\x1b[48;5;{}m'.format(int(c))

def _fg24bit(r, g, b, radix=255):
    M = 255 / radix
    return '\x1b[38;2;{};{};{}m'.format(
        clamp(int(M * r), 0, 255),
        clamp(int(M * g), 0, 255),
        clamp(int(M * b), 0, 255)
    )

def _bg24bit(r, g, b, radix=255):
    M = 255 / radix
    return '\x1b[48;2;{};{};{}m'.format(
        clamp(int(M * r), 0, 255),
        clamp(int(M * g), 0, 255),
        clamp(int(M * b), 0, 255)
    )

# === Hexcolor conversions ===
def hex_to_rgb(hexcolor):
    if hexcolor.startswith('#'):
        hexcolor = hexcolor[1:]
    if len(hexcolor) % 3 != 0:
        raise ValueError("Invalid Hex Color: #{}".format(hexcolor))
    d = len(hexcolor) // 3
    radix = 16 ** d
    return tuple(int(hexcolor[s:s+d], 16) / radix
                 for s in range(0, len(hexcolor), d))

# === 256-color conversions ===

def _rgb6_to_256color_index(r, g, b):
    r = clamp(int(r), 0, 5)
    g = clamp(int(g), 0, 5)
    b = clamp(int(b), 0, 5)
    return 16 + r * 36 + g * 6 + b

Wr, Wg, Wb = 0.299, 0.587, 0.114
#Wr, Wg, Wb = 1/3, 1/3, 1/3
def _rgb_to_256color_index(r, g, b, radix=255):
    def close(x):
        if x >= 95:
            return round((x - 95) / 40) * 40 + 95
        elif x < 47.5:
            return 0
        else:
            return 95

    norm = 255 / radix
    r = clamp(norm * r, 0, 255)
    g = clamp(norm * g, 0, 255)
    b = clamp(norm * b, 0, 255)

    nr = close(r)
    ng = close(g)
    nb = close(b)
    colordiff = abs(r - nr) + abs(g - ng) + abs(b - nb)

    gray = clamp(round((Wr * r + Wg * g + Wb * b + 2) / 10) * 10 - 2, 8, 238)
    graydiff = max(abs(r - gray), abs(g - gray), abs(b - gray)) * (3 if gray >= 48 else 1)

    if graydiff <= colordiff:
        return int(232 + (gray - 8) // 10)
    else:
        return _rgb6_to_256color_index(
            (nr - 95) // 40 + 1, (ng - 95) // 40 + 1, (nb - 95) // 40 + 1)

def rgb_to_256color_fg(r, g, b, radix=256):
    return _fg256(_rgb_to_256color_index(r, g, b, radix))

def rgb_to_256color_bg(r, g, b, radix=256):
    return _bg256(_rgb_to_256color_index(r, g, b, radix))

def _hex_to_256color_index(hexcolor):
    return _rgb_to_256color_index(*hex_to_rgb(hexcolor), 1.0)

def hex_to_256color_fg(hexcolor):
    return _fg256(_hex_to_256color_index(hexcolor))

def hex_to_256color_bg(hexcolor):
    return _bg256(_hex_to_256color_index(hexcolor))

def _hsv_to_256color_index(h, s, v):
    return _rgb_to_256color_index(*colorsys.hsv_to_rgb(h, s, v), radix=1)

def hsv_to_256color_fg(h, s, v):
    return _fg256(_hsv_to_256color_index(h, s, v))

def hsv_to_256color_bg(h, s, v):
    return _bg256(_hsv_to_256color_index(h, s, v))

def _hsl_to_256color_index(h, s, l):
    return _rgb_to_256color_index(*colorsys.hls_to_rgb(h, l, s), radix=1)

def hsl_to_256color_fg(h, s, l):
    return _fg256(_hsl_to_256color_index(h, s, l))

def hsl_to_256color_bg(h, s, l):
    return _bg256(_hsl_to_256color_index(h, s, l))

# === 24-bit color conversions ===

def hsv_to_truecolor_fg(h, s, v):
    return _fg24bit(*colorsys.hsv_to_rgb(h, s, v), radix=1)

def hsv_to_truecolor_bg(h, s, v):
    return _bg24bit(*colorsys.hsv_to_rgb(h, s, v), radix=1)

def hsl_to_truecolor_fg(h, s, l):
    return _fg24bit(*colorsys.hls_to_rgb(h, l, s), radix=1)

def hsl_to_truecolor_bg(h, s, l):
    return _bg24bit(*colorsys.hls_to_rgb(h, l, s), radix=1)

def hex_to_truecolor_fg(hexcolor):
    return _fg24bit(*hex_to_rgb(hexcolor), radix=1)

def hex_to_truecolor_bg(hexcolor):
    return _bg24bit(*hex_to_rgb(hexcolor), radix=1)

# === Infer capabilities ===

SUPPORTS_TRUECOLOR = os.environ.get('TRUECOLOR', '1') == '1'
TERM = os.environ.get('TERM')
SUPPORTS_ANSI = platform.system() != 'Windows'

if sys.stdout.isatty(): # and SUPPORTS_ANSI:
    if SUPPORTS_TRUECOLOR:
        rgb_fg = _fg24bit
        rgb_bg = _bg24bit
        hsv_fg = hsv_to_truecolor_fg
        hsv_bg = hsv_to_truecolor_bg
        hsl_fg = hsl_to_truecolor_fg
        hsl_bg = hsl_to_truecolor_bg
        hex_fg = hex_to_truecolor_fg
        hex_bg = hex_to_truecolor_bg
    else:
        rgb_fg = rgb_to_256color_fg
        rgb_bg = rgb_to_256color_bg
        hsv_fg = hsv_to_256color_fg
        hsv_bg = hsv_to_256color_bg
        hsl_fg = hsl_to_256color_fg
        hsl_bg = hsl_to_256color_bg
        hex_fg = hex_to_256color_fg
        hex_bg = hex_to_256color_bg
else:
    CLEAR = ''
    for key in BASIC_COLORS:
        BASIC_COLORS[key] = ''
    for key in STYLES:
        STYLES[key] = ''
    rgb_fg = rgb_bg = hsv_fg = hsv_bg = hex_fg = hex_bg = hsl_fg = hsl_bg = (
        lambda x, y, z, radix=255: '')

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
            return Style(self._style + STYLES[style])
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
                return Style(self._style + rgb_fg(style, style, style, radix=1))
            else:
                return Style(self._style + rgb_bg(style, style, style, radix=1))
        elif isinstance(style, tuple):
            return Style(self._style + rgb_fg(*style))
        elif style.startswith('#'):
            return Style(self._style + hex_fg(style))
        elif style.startswith('-#'):
            return Style(self._style + hex_bg(style[1:]))
        else:
            raise KeyError(style)

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(attr)

    def hsv(self, h, s, v):
        return Style(self._style + hsv_fg(h / 360, s, v))

    def hsl(self, h, s, l):
        return Style(self._style + hsl_fg(h / 360, s, l))

    def hsv_bg(self, h, s, v):
        return Style(self._style + hsv_bg(h / 360, s, v))

    def hsl_bg(self, h, s, l):
        return Style(self._style + hsl_bg(h / 360, s, l))

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
        def color256(s, c):
            return '\x1b[38;5;{}m{}\x1b[0m'.format(c, s)
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
        H = 72
        S = 10
        V = 24
        for s in range(S+1):
            for v in range(V, -1, -1):
                print(''.join([fmt.hsv(h * 360 / H, s / S, v / V)('#')
                               for h in range(H)]))

    elif sys.argv[1] == 'hsl':
        H = 72
        S = 10
        L = 24
        for s in range(S+1):
            for l in range(L, -1, -1):
                print(''.join([fmt.hsl(h * 360 / H, s / S, l / L)('#')
                               for h in range(H)]))
