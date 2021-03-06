#!/usr/bin/env python3

import argparse
import configparser
import itertools
import os.path
import re
import traceback
from collections import defaultdict
from urllib import parse as urlparse

import requests
import lxml.html
from lxml import etree
from fuzzywuzzy import process

from colors import fmt
from usermatch import user_ratio
import themes

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

def fuzzy_vote(vote, users, ambiguity_threshold=5):
    if vote is None:
        return vote
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
    for voter, (post, votee) in votes.items():
        if votee is None:
            wagons[None].append((post, voter))
            continue
        wagons[votee].append((post, voter))
    return wagons

class ModTool:
    DEFAULT_STYLE = {
        'error': fmt.Red,
        'warning': fmt.Yellow,

        'vote': fmt.Green,
        'unvote': fmt.dim.green,
        'hammer': fmt.Cyan,
        'user': fmt.inverted,
        'postnum': fmt.underline,

        'v/la': fmt.magenta,
        '@mod': fmt.Blue,
        'replace': fmt.cyan,
        'votecount': fmt,
    }

    def __init__(self, game_url, votecount=False, modname=None, deadline=None,
                 theme=None, **kwargs):
        self.base_url, query = game_url.split('?')
        self.query = {
            k: v for k, v in urlparse.parse_qsl(query)
            if k in ['t', 'f']
        }

        self.votecount_enabled = votecount
        self.last_votecount_post = None
        self.votes = None
        self.day = 0
        self.count_no = 0
        self.deadline = deadline
        self.modname = modname
        self.valid_players = []
        self.replacements = {}

        self.styles = dict(self.DEFAULT_STYLE)
        if theme:
            self.styles.update(theme)

    def warning(self, fmt, *args, **kwargs):
        print(self.styles['warning']('WARNING: ' + str(fmt).format(*args, **kwargs)))

    def error(self, fmt, *args, **kwargs):
        print(self.styles['error']('ERROR: ' + str(fmt).format(*args, **kwargs)))

    def print_vote_count(self, backlink=False):
        """Print a BBCode-formatted vote count."""
        if not self.votes:
            return

        def lminus(actual, required):
            if actual >= majority:
                return '[b][i](LYNCHED)[/i][/b]'
            if majority - actual == 1 or actual / majority >= 0.6:
                return '[b][i](L-{})[/b][/i]'.format(required - actual)
            else:
                return ''

        def vote_ref(post_ref, voter):
            if post_ref > 0:
                return '[post={}]{}[/post]'.format(post_ref, voter)
            else:
                return voter

        with self.styles['votecount']:
            wagons = get_wagons(self.votes)
            playercount = len(self.votes)
            majority = len(self.votes) // 2 + 1
            print('[area=Official Vote Count {}-{}]'.format(self.day, self.count_no))
            for wagon, voters in sorted(wagons.items(),
                                        key=lambda x: (-len(x[1]), x[1][0][0]
                                                       if x[1] else -999)):
                if wagon is not None:
                    print('[b]{wagon}[/b] ({count}): {voters} {lminus}'.format(
                        wagon=wagon, count=len(voters), voters=', '.join(
                            [vote_ref(*v) for v in sorted(voters)]),
                        lminus=lminus(len(voters), majority)
                    ))
            print()
            not_voting = wagons[None]
            print('[i]Not Voting[/i] ({}): {}'.format(
                len(not_voting), ', '.join([vote_ref(*v) for v in sorted(not_voting)])
            ))
            print()
            print('With {} players alive, it takes {} to lynch.'.format(playercount, majority))
            print()
            print('[b]Deadline[/b]: [countdown]{}[/countdown]'.format(self.deadline))
            if backlink and self.last_votecount_post is not None:
                print('[size=75][post={}]Previous Vote Count[/post][/size]'.format(self.last_votecount_post))
            print('[/area]')

    def count_vote(self, user, raw_vote, postnum):
        """Count a player's vote, trying to match the vote to a player.
        The operator will be warned on questionable votes.

        Returns a boolean indicating if the voted player was hammered
                or None if no vote was counted."""
        if (not self.votecount_enabled
            or self.votes is None
            or user not in self.votes):
            return # Ignore vote
        if raw_vote is None:
            self.votes[user] = postnum, None
            return False
        try:
            vote = fuzzy_vote(raw_vote, self.valid_players)
            while vote in self.replacements:
                vote = self.replacements[vote]
            if vote:
                self.votes[user] = postnum, vote
                if raw_vote.lower() != vote.lower():
                    self.warning("'{}' ==> '{}'", raw_vote, vote)
                return sum(v == vote for p, v in self.votes.values()) > len(self.votes) / 2
            else:
                self.error("'{}' could not be matched to any player!", raw_vote)
        except InvalidVoteError as e:
            self.error(str(e))

    def replace_player(self, original, replacement):
        self.valid_players.append(replacement)
        self.replacements[original] = replacement
        self.votes[replacement] = self.votes[original]
        del self.votes[original]
        for voter in self.votes:
            p, v = self.votes[voter]
            if v == original:
                self.votes[voter] = p, replacement

    def init_votes(self, vote_counter):
        if not self.votecount_enabled:
            return
        header = vote_counter.xpath('legend')[0]
        _, dc = header.text_content().rsplit(None, 1)
        day, count_no = dc.split('-')
        self.day = int(day)
        self.count_no = int(count_no) + 1
        header.drop_tree()
        fake_post_nums = itertools.count(-99)
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
                self.votes[voter] = next(fake_post_nums), wagon
        self.valid_players = list(self.votes)

    def process_page(self, page, end_post=None):
        doc = lxml.html.fromstring(page)
        if end_post is None:
            end_post = int(doc.find_class('pagination')[0].text_content().lstrip('"').split()[0])
        for quote in doc.xpath('//blockquote'):
            quote.drop_tree()
        for post in doc.find_class('post'):
            postnum = int(post.xpath('.//p[@class="author"]/a/strong')[0].text_content().strip().lstrip('#'))
            user = post.xpath('.//dl[@class="postprofile"]/dt/a')[0].text_content().strip()
            if postnum > end_post:
                return end_post

            if self.votes is None:
                vote_counter = post.xpath('.//fieldset[legend[starts-with(text(),"Official Vote Count")]]')
                if vote_counter:
                    self.votes = {}
                    if self.modname is None:
                        self.modname = user
                    self.last_votecount_post = postnum
                    self.init_votes(vote_counter[0])
                    continue

            post_text = etree.tostring(post.find_class('content')[0], encoding='unicode').strip()
            important = []
            deferred = []
            for rawline in post_text.split('<br />'):
                try:
                    line = lxml.html.fromstring(rawline)
                except etree.ParserError:
                    continue
                plain = line.text_content().strip()
                plainlower = plain.lower()
                if plainlower.startswith('mod') or '@mod' in plainlower:
                    important.append(self.styles['@mod'](plain))

                if 'V/LA' in plain.upper():
                    important.append(self.styles['v/la'](plain))

                if 'replaces' in plain and user == self.modname:
                    important.append(self.styles['replace'](plain))
                    try:
                        new, old = plain.split('replaces')
                        self.replace_player(old.strip(), new.strip())
                    except Exception:
                        self.error("Unable to do replacement: {}", traceback.format_exc())

                linevote = line.find_class('bbvote')
                hammered = None
                if linevote:
                    raw_vote = linevote[0].text_content()
                    vtype, vote = raw_vote.split(':')
                    if vtype == 'VOTE' and vote.strip().lower() != 'unvote':
                        important.append(self.styles['vote'](plain))
                        hammered = self.count_vote(user, vote.strip(), postnum)
                    else:
                        important.append(self.styles['unvote'](plain))
                        hammered = self.count_vote(user, None, postnum)
                elif plain.upper().startswith('VOTE:'): #TODO: have user confirm if vote is intended
                    important.append(self.styles['vote'](plain))
                    hammered = self.count_vote(user, plain.split(':')[1].strip(), postnum)
                elif plain.upper().startswith('UNVOTE'):
                    important.append(self.styles['unvote'](plain))
                    hammered = self.count_vote(user, None, postnum)

                if hammered:
                    important.append(self.styles['hammer']("{} has been HAMMERED!", vote))
                    deferred.append(lambda: self.print_vote_count())

            if important:
                print("{} - {}:".format(self.styles['user'](user),
                                        self.styles['postnum']('Post #' + str(postnum))))
                for line in important:
                    print('    ' + line)

            for thunk in deferred:
                thunk()

            if important or deferred:
                print()
        return end_post

    def run(self, start_post=0, end_post=None, page_size=200):
        qargs = dict(self.query)
        qargs['ppp'] = page_size
        while end_post is None or start_post < end_post:
            if start_post:
                qargs['start'] = start_post
            res = requests.get(self.base_url, params=qargs)
            if res.status_code == 200:
                end_post = self.process_page(res.text, end_post)
                start_post += page_size
            else:
                raise Exception("Request error!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Parses out mod-relevant info such as @mod and VOTEs")

    parser.add_argument('game_url',
                        help="The url of the game to use. (or file)")
    parser.add_argument('-s', '--start', type=int, default=0, dest='start_post',
                        help="The post # to start from")
    parser.add_argument('-e', '--end', type=int, dest='end_post',
                        help="The post # to end at (inclusive)")
    parser.add_argument('-v', '--votecount', action='store_true',
                        help="Count votes")
    parser.add_argument('-d', '--deadline',
                        help="The deadline to display in the votecounter.")
    parser.add_argument('-m', '--modname',
                        help="The username of the moderator.")
    parser.add_argument('-b', '--backlink', action='store_true',
                        help="Include link to previous vote count.")
    parser.add_argument('-y', '--auto-confirm', action='store_true',
                        help="Automatically confirm interactive confirmations.")
    parser.add_argument('-i', '--interactive-fixes', action='store_true',
                        help="Allow user to correct imperfect vote matches interactively.")

    args = parser.parse_args()

    rcfile = os.path.join(os.path.expanduser('~'), '.modtoolrc')
    if os.path.isfile(rcfile):
        config = configparser.ConfigParser()
        config.read(rcfile)
        try:
            theme = getattr(themes, config['Display']['theme'])
        except (KeyError, AttributeError):
            theme = None
    else:
        theme = None

    if args.votecount and not args.modname:
        print(fmt.yellow("NOTE: votecount was requested, but modname was "
                         "unspecified. Moderator will be inferred from "
                         "inital vote count post."))
    mod_tool = ModTool(args.game_url, votecount=args.votecount,
                       modname=args.modname, deadline=args.deadline,
                       theme=theme)
    mod_tool.run(args.start_post, args.end_post)
    if args.votecount:
        print('=' * 50)
        print()
        mod_tool.print_vote_count(args.backlink)
