
import re
from fuzzywuzzy import fuzz

class LazySet(set):
    __slots__ = '_gen',
    def __init__(self, gen):
        self._gen = gen
        super().__init__()

    def __contains__(self, item):
        if not self and self._gen:
            self.update(self._gen)
            self._gen = None
        return super().__contains__(item)

_WORDS = LazySet(w.strip() for w in open('words.txt'))

def abbrev_score(abbr, full):
    """Scores how well an abbreviation matches a username/string.
    Assumes `abbr` is lowercased and only contains only alphanumerics."""
    l = len(abbr)
    if l > len(full) or l >= 5: # Not an acronym
        return 0

    f = full.lower()
    if l <= 1: # Base case
        return float(f.startswith(abbr))
    if not f.startswith(abbr[0]):
        return 0
    if abbr[1:].isdigit(): # Match users with numbers, e.g. A50 ~ Almost50
        return float(full.endswith(abbr[1:]))

    cut = 0
    best = 0
    s = abbr[1].lower()
    while True:
        cut = f.find(s, cut + 1)
        if cut == -1:
            return best
        score = max(
            float(
                full[cut].isupper()
                or not full[cut-1].isalpha()
                or full[:cut].lower() in _WORDS
            ),
            0.85 # TODO: non-dictionary word model
        ) * abbrev_score(abbr[1:], full[cut:]) * (
            0.8 if cut == 1 and f[0] not in 'ai' else 1)
        if score > best:
            best = score

def user_ratio(a_orig, b_orig):
    a = ''.join([c.lower() for c in a_orig if c.isalnum()])
    b = ''.join([c.lower() for c in b_orig if c.isalnum()])
    if a == b:
        return 100
    return max(
        max(abbrev_score(a, b_orig), abbrev_score(b, a_orig)) * 95,
        fuzz.ratio(a, b),
        fuzz.partial_ratio(a, b) * 0.85,
        fuzz.partial_ratio(a.split(None, 1)[0], b) * 0.75,
        fuzz.partial_ratio(a, b.split(None, 1)[0]) * 0.75,
    )

if __name__ == '__main__':
    import readline
    for abbr, name in [
        ('N_M', 'Not_Mafia'),
        ('NM', 'Not_Mafia'),
        ('nsg', 'northsidegal'),
        ('pz', 'Papa Zito'),
        ('A50', 'Almost50'),
        ('g27', 'Goron27'),
        ('RC', 'RadiantCowbells'),
        ('cedric', 'Cedrick'),
        ('fitz', 'havingfitz'),
        ('Zito', 'Papa Zito'),
        ('RadiantScumbells', 'RadiantCowbells'),
        ('beef', 'Beefster'),
        ('beefy', 'Beefster'),
        ('Beefeater', 'Beefster')
    ]:
        print(abbr, name, user_ratio(abbr, name))
    # try:
    #     while True:
    #         print(abbrev_score(*input().split(None, 1)))
    # except EOFError:
    #     print("Goodbye.")
