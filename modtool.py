#!/usr/bin/env python3

import argparse
import re
from collections import defaultdict
from urllib import parse as urlparse

import requests
import lxml.html
from lxml import etree
from fuzzywuzzy import fuzz, process

class InvalidVoteError(Exception):
    def __str__(self):
        return "'{}' is not a valid vote!".format(self.args[0])

class AmbiguityError(InvalidVoteError):
    def __init__(self, orig, *possibilities):
        super(AmbiguityError, self).__init__()
        self.orig = orig
        self.possibilities = possibilities

    def __str__(self):
        return "{} can be matched to '{}' or '{}'".format(
            self.orig, ', '.join(self.possibilities[:-1]), self.possibilities[-1])

class NoMatchError(InvalidVoteError):
    def __str__(self):
        return "'{}' could not be matched to any player!".format(self.args[0])

SEPS = re.compile(r'[-_.]+|\s+')
def abbrev_match(abbr, full):
    if len(abbr) < 2 or len(abbr) > len(full) or abbr[0].lower() != full[0].lower():
        return 0
    if abbr.upper() == ''.join(filter(str.isupper, full)):
        return 1
    if abbr.lower() == ''.join(w[0].lower() for w in SEPS.split(full) if w):
        return 1
    pos = 0
    f = full.lower()
    # TODO: model probability of word boundaries
    for char in abbr[1:].lower():
        pos = f.find(char, pos + 1)
        if pos == -1:
            return 0
    return 0.75

def user_ratio(a_orig, b_orig):
    a = a_orig.lower()
    b = b_orig.lower()
    if a == b:
        return 100
    return max(
        fuzz.ratio(a, b),
        max(abbrev_match(a, b_orig), abbrev_match(b, a_orig)) * 95,
        a.startswith(b) * 90, a.endswith(b) * 90,
        b.startswith(a) * 90, b.endswith(a) * 90,
        fuzz.partial_ratio(a, b) * 0.7,
        fuzz.partial_ratio(a.split(None, 1)[0], b) * 0.65,
        fuzz.partial_ratio(a, b.split(None, 1)[0]) * 0.65,
    )

def fuzzy_vote(vote, users, ambiguity_threshold=5):
    if vote.lower() == 'no lynch':
        return 'No Lynch'
    user_poss = list(users)
    if len(vote) < 2:
        raise InvalidVoteError(vote)
    options = process.extractBests(
        vote, user_poss, processor=lambda x: x, scorer=user_ratio, score_cutoff=60)
    if options:
        match, score = options[0]
        if vote.lower() != match.lower():
            if len(options) >= 2 and abs(score - options[1][1]) < ambiguity_threshold:
                print(options)
                raise AmbiguityError(vote, match, options[1][0])
        return match
    else:
        raise NoMatchError(vote)

def get_wagons(votes):
    wagons = defaultdict(list)
    for voter, votee in votes.items():
        if votee is None:
            wagons[None].append(voter)
            continue
        wagons[fuzzy_vote(votee, votes)].append(voter)
    return wagons

def print_vote_count(votes, day='X', count='Y', deadline='20YY-MM-DD hh:mm:ss tz'):
    def lminus(actual, required):
        if actual >= majority:
            return '[b][i](LYNCHED)[/i][/b]'
        if majority - actual == 1 or actual / majority >= 0.6:
            return '[b][i](L-{})[/b][/i]'.format(required - actual)
        else:
            return ''
    wagons = get_wagons(votes)
    playercount = len(votes)
    majority = len(votes) // 2 + 1
    print('[area=Official Vote Count {}-{}]'.format(day, count))
    for wagon, voters in sorted(wagons.items(), key=lambda x: -len(x[1])):
        if wagon is not None:
            print('[b]{wagon}[/b] ({count}): {voters} {lminus}'.format(
                wagon=wagon, count=len(voters), voters=', '.join(sorted(voters, key=str.lower)),
                lminus=lminus(len(voters), majority)
            ))
    print()
    not_voting = wagons[None]
    print('[i]Not Voting[/i] ({}): {}'.format(len(not_voting), ', '.join(not_voting)))
    print()
    print('With {} players alive, it takes {} to lynch.'.format(playercount, majority))
    print()
    print('[b]Deadline[/b]: [countdown]{}[/countdown]'.format(deadline))
    print('[/area]')

def filter_page(page, votes=None, initial_vote_count=False, day='X', count_no='Y'):
    important = None
    user = None
    deferred = None
    def count_vote(raw_vote):
        try:
            vote = fuzzy_vote(raw_vote, votes)
            if vote:
                votes[user] = vote
                if raw_vote.lower() != vote.lower():
                    print("\x1b[93mWARNING: '{}' ==> '{}'\x1b[0m".format(raw_vote, vote))
                if len(get_wagons(votes)[vote]) > len(votes) / 2:
                    important.append("\x1b[96m{} has been HAMMERED!\x1b[0m".format(vote))
                    deferred.append(lambda: print_vote_count(votes))
            else:
                print("\x1b[91mERROR: '{}' could not be matched to any player!\x1b[0m".format(raw_vote))
        except InvalidVoteError as e:
            print("\x1b[91mERROR: {}!\x1b[0m".format(str(e)))

    doc = lxml.html.fromstring(page)
    total_posts = int(doc.find_class('pagination')[0].text_content().lstrip('"').split()[0])
    for quote in doc.xpath('//blockquote'):
        quote.drop_tree()
    for post in doc.find_class('post'):
        if initial_vote_count:
            vote_counter = post.xpath('.//fieldset[legend[starts-with(text(),"Official Vote Count")]]')
            if vote_counter:
                vote_counter = vote_counter[0]
                header = vote_counter.xpath('legend')[0]
                _, dc = header.text_content().rsplit(None, 1)
                day, count_no = dc.split('-')
                day = int(day)
                count_no = int(count_no) + 1
                header.drop_tree()
                for rawline in etree.tostring(vote_counter, encoding='unicode').split('<br />'):
                    try:
                        line = lxml.html.fromstring(rawline).text_content().strip()
                    except etree.ParserError:
                        continue
                    if not line or line.startswith('Deadline') or ':' not in line:
                        continue
                    wagon, voters = line.split(':', 1)
                    if '(' in voters and voters.endswith(')'): # Remove (L-X)
                        voters = voters.split('(')[0]
                    wagon = wagon.rsplit(None, 1)[0].strip()
                    voters = [v.strip() for v in voters.split(',')]
                    if wagon == 'Not Voting':
                        wagon = None
                    for voter in voters:
                        votes[voter] = wagon
                initial_vote_count = False
                continue

        postnum = int(post.xpath('.//p[@class="author"]/a/strong')[0].text_content().strip().lstrip('#'))
        user = post.xpath('.//dl[@class="postprofile"]/dt/a')[0].text_content().strip()
        post_text = etree.tostring(post.find_class('content')[0], encoding='unicode').strip()
        important = []
        deferred = []
        for rawline in post_text.split('<br />'):
            try:
                line = lxml.html.fromstring(rawline)
            except etree.ParserError:
                continue
            plain = line.text_content().strip()
            linevote = line.find_class('bbvote')
            if plain.lower().startswith('@mod'):
                important.append("\x1b[94m{}\x1b[0m".format(plain))
            elif linevote:
                raw_vote = linevote[0].text_content()
                vtype, vote = raw_vote.split(':')
                if vtype == 'VOTE':
                    important.append("\x1b[92m{}\x1b[0m".format(plain))
                    if votes is not None and user in votes:
                        count_vote(plain.split(':')[1].strip())
                else:
                    important.append("\x1b[32m{}\x1b[0m".format(plain))
                    if votes is not None and user in votes:
                        votes[user] = None
            elif plain.startswith('VOTE:'):
                important.append("\x1b[92m{}\x1b[0m".format(plain))
                if votes is not None and user in votes:
                    count_vote(plain.split(':')[1].strip())
            elif plain.startswith('UNVOTE'):
                important.append("\x1b[32m{}\x1b[0m".format(plain))
                if votes is not None and user in votes:
                    votes[user] = None
            elif 'V/LA' in plain.upper():
                important.append("\x1b[35m{}\x1b[0m".format(plain))

        if important:
            print("\x1b[7m{}\x1b[0m - Post #{}:".format(user, postnum))
            for line in important:
                print('    ' + line)

        for thunk in deferred:
            thunk()

        if important or deferred:
            print()
    return total_posts, day, count_no

def mod_filter(game_url, start_post=0, votecount=False, deadline=None):
    base, query = game_url.split('?')
    qargs = {
        k: v for k, v in urlparse.parse_qsl(query)
        if k in ['t', 'f']
    }
    total_posts = None
    votes = {} if votecount else None
    initial_vote_count = votecount
    day, count_no = 'X', 'Y'
    while total_posts is None or start_post < total_posts:
        if start_post:
            qargs['start'] = str(start_post)
        res = requests.get(base, params=qargs)
        if res.status_code == 200:
            total_posts, day, count_no = filter_page(res.text, votes, initial_vote_count, day, count_no)
            initial_vote_count = False
            start_post += 25
        else:
            raise Exception("Request error!")

    if votecount:
        print_vote_count(votes, day=day, count=count_no, deadline=deadline)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Parses out mod-relevant info such as @mod and VOTEs")

    parser.add_argument('game_url',
                        help="The url of the game to use. (or file)")
    parser.add_argument('-s', '--start', type=int, default=0,
                        help="The post # to start from")
    parser.add_argument('-l', '--local', action='store_true',
                        help="Filter a saved page")
    parser.add_argument('-v', '--votecount', action='store_true',
                        help="Count votes")
    parser.add_argument('-d', '--deadline',
                        help="The deadline to display in the votecounter.")

    args = parser.parse_args()

    if args.local:
        with open(args.game_url) as game:
            filter_page(game.read())
    else:
        mod_filter(args.game_url, args.start, votecount=args.votecount, deadline=args.deadline)
