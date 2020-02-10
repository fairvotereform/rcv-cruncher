from functools import wraps, lru_cache, partial
from itertools import product, combinations
from collections import Counter
from argparse import ArgumentParser
from pprint import pprint
from copy import deepcopy
import csv
import shutil
import os
import pickle  # faster than json, shelve

# from fractions import Fraction
from gmpy2 import mpq as Fraction
from dbfread import DBF
import scipy.linalg
import scipy.optimize

import manifest
from math import sqrt
from collections import defaultdict
from contextlib import suppress
from glob import glob

from hashlib import md5
from inspect import getsource

UNDERVOTE = -1
OVERVOTE = -2
WRITEIN = -3


### Persistence ###
def unwrap(function):
    """
        checks if the function has been decorated + wrapped
        (using a @decorator using @wraps)
        and returns the wrapped function (the function decorated with @decorator)
    """
    while '__wrapped__' in dir(function):
        function = function.__wrapped__
    return function


def srchash(function):
    """
        input is the name of a function (str)

        returns a hash string representing all the set of all function source code
        implicated by the input function

    """
    visited = set()
    frontier = {function}  # start with input function
    while frontier:

        fun = frontier.pop()
        visited.add(fun)

        fun_obj = unwrap(globals()[fun])  # retrieve function object, unwrapped
        code = fun_obj.__code__  # get function's underlying code object
        helpers = list(code.co_names)  # get list of names used by function bytecode

        for const in code.co_consts:  # loop through constants used by bytecode
            if 'co_names' in dir(const):  # if they are code objects
                helpers.extend(const.co_names)  # add their names to helpers

        for helper in set(helpers) - visited:  # for any new helpers
            if '__code__' in dir(globals().get(helper)):  # if they have code objects
                frontier.add(helper)  # add them to be looped through

    # at the end of this loop, all functions called by the input function
    # should have been recursively checked for all their function calls and
    # added to the visited set

    # visited should contain the set of all functions implicated by calling the
    # input function

    # the next lines effectively concatenate all the functions' source code
    # in visited and produce a hash unique to that code set

    h = md5()
    for f in sorted(visited):
        h.update(bytes(getsource(globals()[f]), 'utf-8'))
    return h.hexdigest()


def shelve_key(arg):
    """
        only used in save() decorator def

        returns a string. either 'date, office, place' (if arg == dict)
            or callable.__name__ (if arg == callable)
    """
    if isinstance(arg, dict):
        return dop(arg)
    if callable(arg):
        return arg.__name__
    return arg


def save(f):
    """
        decorator def


    """
    f.not_called = True
    f.cache = {}

    @wraps(f)
    def fun(*args):

        # if this is the first time the function is being called during this run,
        # check that there isn't already a saved computation from previous runs
        if f.not_called:
            check = srchash(f.__name__)
            dirname = 'results/' + f.__name__
            checkname = dirname + '.check'
            # check if the saved srchash is the different from the current one
            # if so, delete the results previosuly saved from this function
            if os.path.exists(checkname) and check != open(checkname).read().strip():
                shutil.rmtree(dirname)
                os.remove(checkname)
            # if the check is absent at this point, write a new one out
            # and make a fresh results dir for this function
            if not os.path.exists(checkname):
                open(checkname, 'w').write(check)
                os.mkdir(dirname)
            # indicate that now the function has been called
            f.not_called = False

        key = tuple(str(shelve_key(a)) for a in args)

        # check if the current call is for the same election, if not, clear the cache
        if next(iter(f.cache), key)[0] != key[0]:
            f.cache = {}  # evict cache if first part of key (election id usually) is different
            f.visited_cache = False
        if key in f.cache:
            return f.cache[key]

        file_name = 'results/{}/{}'.format(f.__name__, '.'.join(key).replace('/', '.'))

        with suppress(IOError, EOFError), open(file_name, 'rb') as file_object:
            f.cache[key] = pickle.load(file_object)
            return f.cache[key]
        with open(file_name, 'wb') as file_object:
            f.cache[key] = f(*args)
            pickle.dump(f.cache[key], file_object)
            return f.cache[key]

    return fun


def tmpsave(f):
    @wraps(f)
    def fun(ctx):
        if f.__name__ in ctx:
            return ctx[f.__name__]
        return ctx.setdefault(f.__name__, f(ctx))

    return fun



####################################################################################################################
####################################################################################################################
####################################################################################################################
####################################################################################################################
####################################################################################################################
####################################################################################################################
####################################################################################################################
####################################################################################################################
# unresolved functions

# from crunch
@tmpsave
def number(ctx):
    return {
        ('Cambridge', 'School Committee'): 6,
        ('Cambridge', 'City Council'): 9,
        ('Minneapolis', 'BOE'): 2,
        ('Minneapolis', 'Park At Large'): 3,
    }.get((ctx['place'],ctx['office']), 1)

# from simple crunch
def number(ctx):
    if 'number' in ctx:
        return ctx['number']
    return {
        ('Cambridge', 'School Committee'): 6,
        ('Cambridge', 'City Council'): 9,
        ('Minneapolis', 'BOE'): 2,
        ('Minneapolis', 'Park At Large'): 3,
    }.get((ctx['place'],ctx['office']), 1)


# crunch
HEADLINE_STATS = [place, state, date, office, title_case_winner, blank,
    number_of_candidates, number_of_rounds, final_round_vote,
    final_round_percent, first_round_vote,
    first_round_percent, first_round_place, number_of_first_round_valid_votes,
    number_of_final_round_active_votes, blank, total, blank,
    final_round_inactive, final_round_winner_votes_over_first_round_valid,
    winners_consensus_value, condorcet, total_fully_ranked,
    ranked_multiple, first_round_undervote, first_round_overvote,
    later_round_inactive_by_overvote, later_round_inactive_by_abstention,
    later_round_inactive_by_ranking_limit, includes_duplicates, includes_skipped
]

# simple crunch
HEADLINE_STATS = [place, state, date, office, title_case_winner, blank,
    number_of_candidates, number_of_rounds, final_round_vote,
    final_round_percent, first_round_vote,
    first_round_percent, first_round_place, number_of_first_round_valid_votes,
    number_of_final_round_active_votes, blank, total, blank,
    final_round_inactive, final_round_winner_votes_over_first_round_valid,
    winners_consensus_value, condorcet, total_fully_ranked,
    ranked_multiple, first_round_undervote, first_round_overvote,
    later_round_inactive_by_overvote, later_round_inactive_by_abstention,
    later_round_inactive_by_ranking_limit, includes_duplicates, includes_skipped,
    top2_winners_vote_increased, top2_winners_fraction, top2_majority,
    top2_winner_over_40, effective_ballot_lengths
]

# simple crunch
@save
def effective_ballot_lengths(ctx):
    """
    A list of validly ranked choices, and how many ballots had that number of
    valid choices.
    """
    return '; '.join('{}: {}'.format(a,b) for a,b in sorted(Counter(map(len, cleaned(ctx))).items()))

# crunch
@save
def effective_ballot_length(ctx):
    return Counter(len(b) for b in cleaned(ctx))


# crunch
@save
def seq_stv(ctx):
    ballots = deepcopy(cleaned(ctx))
    winners = []
    for _ in range(number(ctx)):
        winners.append(rcv_ballots(ballots)[-1][0][0])
        ballots = remove([], (remove(winners[-1], b) for b in ballots))
    return winners

# simple crunch
@save
def seq_stv(ctx):
    ballots = deepcopy(cleaned(ctx))
    tallies = []
    winners = []
    winners_votes = []
    last_round_votes = []
    for _ in range(number(ctx)):
        deciding_round = rcv_ballots(ballots)[-1]
        winners.append(deciding_round[0][0])
        winners_votes.append(deciding_round[1][0])
        last_round_votes.append(sum(deciding_round[1]))
        ballots = remove([], (remove(winners[-1], b) for b in ballots))
    for i,(w,v,t) in enumerate(zip(winners,winners_votes,last_round_votes)):
        print('winner {}'.format(i+1),w,str(v/float(t)*100)[:5]+'%', v,'/',t,sep='\t')
    return ''



# crunch
@tmpsave
def break_on_repeated_undervotes(ctx):
    return place(ctx) == 'Maine'

@tmpsave
def break_on_overvote(ctx):
    return place(ctx) != 'Minneapolis'


# simple crunch
@tmpsave
def break_on_repeated_undervotes(ctx):
    return False

@tmpsave
def break_on_overvote(ctx):
    return True

####################################################################################################################
####################################################################################################################
####################################################################################################################
####################################################################################################################
####################################################################################################################
####################################################################################################################
####################################################################################################################
####################################################################################################################







### Headline Statistics ###

@tmpsave
def place(ctx):
    return '????'


def state(ctx):
    if place(ctx) in {'Berkeley', 'Oakland', 'San Francisco', 'San Leandro'}:
        return 'CA'
    if place(ctx) in {'Burlington'}:
        return 'VT'
    if place(ctx) in {'Cambridge'}:
        return 'MA'
    if place(ctx) in {'Maine'}:
        return 'ME'
    if place(ctx) in {'Minneapolis'}:
        return 'MN'
    if place(ctx) in {'Pierce County'}:
        return 'WA'
    if place(ctx) in {'Santa Fe'}:
        return 'NM'


@tmpsave
def date(ctx):
    return '????'


@tmpsave
def office(ctx):
    return '????'


@save
def title_case_winner(ctx):
    '''
    The winner of the election, or, in multiple winner contests, the
    hypothetical winner if the contest was single winner.
    '''
    # Horrible Hack!
    # no mapping file for the 2006 Burlington Mayoral Race, so hard coded here:
    if place(ctx) == 'Burlington' and date(ctx) == '2006':
        return 'Bob Kiss'
    return str(winner(ctx)).title()


# fixme
def number_of_candidates(ctx):
    '''
    The number of non-candidates on the ballot, not including write-ins.
    '''
    return len(candidates(ctx))


def number_of_rounds(ctx):
    '''
    The number of rounds it takes for one candidate (the winner) to receive
    the  majority of the non-exhausted votes. This number includes the
    round in which the winner receives the majority of the non-exhausted votes.
    This is based on a tabulator that doesn't eliminate more than one declared
    candidate per round.
    '''
    return len(rcv(ctx))


def final_round_vote(ctx):
    '''
    The number of votes for the winner in the final round. The final round is
    the first round where the winner receives a majority of the non-exhausted
    votes.
    '''
    return rcv(ctx)[-1][1][0]


def final_round_percent(ctx):
    '''
    The percent of votes for the winner in the final round. The final round is
    the first round where the winner receives a majority of the non-exhausted
    votes.
    '''
    return rcv(ctx)[-1][1][0] / sum(rcv(ctx)[-1][1])


def first_round_vote(ctx):
    '''
    The number of votes for the winner in the first round.
    '''
    wind = rcv(ctx)[0][0].index(winner(ctx))
    return rcv(ctx)[0][1][wind]


def first_round_percent(ctx):
    '''
    The percent of votes for the winner in the first round.
    '''
    wind = rcv(ctx)[0][0].index(winner(ctx))
    return rcv(ctx)[0][1][wind] / sum(rcv(ctx)[0][1])


def first_round_place(ctx):
    '''
    In terms of first round votes, what place the eventual winner came in.
    '''
    return rcv(ctx)[0][0].index(winner(ctx)) + 1


def number_of_first_round_valid_votes(ctx):
    '''
    The number of votes that were awarded to any candidate in the first round.
    '''
    return sum(rcv(ctx)[0][1])


def number_of_final_round_active_votes(ctx):
    '''
    The number of votes that were awarded to any candidate in the final round.
    '''
    return sum(rcv(ctx)[-1][1])


@save
def total(ctx):
    '''
    This includes ballots with no marks.
    '''
    return len(ballots(ctx))


def final_round_inactive(ctx):
    '''
    The difference of first round valid votes and final round valid votes.
    '''
    return number_of_first_round_valid_votes(ctx) - number_of_final_round_active_votes(ctx)


def final_round_winner_votes_over_first_round_valid(ctx):
    '''
    The number of votes the winner receives in the final round divided by the
    number of valid votes in the first round.
    '''
    return final_round_vote(ctx) / number_of_first_round_valid_votes(ctx)


@save
def winners_consensus_value(ctx):
    '''
    The percentage of valid first round votes that rank the winner in the top 3.
    '''
    return winner_in_top_3(ctx) / number_of_first_round_valid_votes(ctx)


@save
def condorcet(ctx):
    '''
    Is the winner the condorcet winner?
    The condorcet winner is the candidate that would win a 1-on-1 election versus
    any other candidate in the election. Note that this calculation depends on
    jurisdiction dependant rule variations.
    '''
    if len(rcv(ctx)) == 1:
        return True
    net = Counter()
    for b in cleaned(ctx):
        for loser in losers(ctx):
            net.update({loser: before(winner(ctx), loser, b)})
    if not net:  # Uncontested Race -> net == {}
        return True
    return min(net.values()) > 0


@save
def total_fully_ranked(ctx):
    '''
    The number of voters that have validly used all available rankings on the
    ballot, or that have validly ranked all non-write-in candidates.
    '''
    return sum(fully_ranked(ctx))


@save
def ranked_multiple(ctx):
    '''
    The number of voters that validly use more than one ranking.
    '''
    return sum(len(b) > 1 for b in cleaned(ctx))


@save
def first_round_undervote(ctx):
    '''
    The number of ballots with absolutely no markings at all.

    Note that this is not the same as "exhausted by undervote". This is because
    some juristidictions (Maine) discard any ballot begining with two
    undervotes regardless of the rest of the content of the ballot, and call
    this ballot as exhausted by undervote.
    '''
    return sum(set(b) == {UNDERVOTE} for b in ballots(ctx))


@save
def first_round_overvote(ctx):
    '''
    The number of ballots with an overvote before any valid ranking.

    Note that this is not the same as "exhausted by overvote". This is because
    some juristidictions (Maine) discard any ballot begining with two
    undervotes, and call this ballot as exhausted by undervote, even if the
    undervotes are followed by an overvote.

    Other jursidictions (Minneapolis) simply skip over overvotes in a ballot.
    '''
    return sum(c == OVERVOTE for c in first_round(ctx))


@save
def later_round_inactive_by_overvote(ctx):
    '''
    The number of ballots that were discarded after the first round due to an
    overvote.

    Note that Minneapolis doesn't discard overvote ballots, it simply skips over
    the overvote.
    '''
    return sum(a and b for a, b in zip(later_round_exhausted(ctx), exhausted_by_overvote(ctx)))


@save
def later_round_inactive_by_abstention(ctx):
    '''
    The number of ballots that were discarded after the first round because not
    all rankings were used and it was not discarded because of an overvote.

    This factor will exclude all ballots with overvotes aside from those in Maine
    where more than one sequential undervote preceeds an overvote.
    '''
    return sum(later_round_exhausted(ctx)) \
           - later_round_inactive_by_overvote(ctx) \
           - later_round_inactive_by_ranking_limit(ctx)


@save
def later_round_inactive_by_ranking_limit(ctx):
    '''
    The number of ballots that validly used every ranking, but didn't rank any
    candidate that appeared in the final round.
    '''
    return sum(a and b for a, b in zip(later_round_exhausted(ctx), fully_ranked(ctx)))


def includes_duplicates(ctx):
    '''
    The number of ballots that rank the same candidate more than once, or
    include more than one write in candidate.
    '''
    return any_repeat(ctx)


@save
def any_repeat(ctx):
    return sum(v for k,v in count_duplicates(ctx).items() if k>1)


@save
def count_duplicates(ctx):
    return Counter(max_repeats(ctx))


@save
def max_repeats(ctx):
    return [max(0,0,*map(b.count,set(b)-{UNDERVOTE,OVERVOTE}))
            for b in ballots(ctx)]

@save
def skipped(ctx):
    return [any({UNDERVOTE} & {x} - {y} for x,y in zip(b, b[1:]))
            for b in ballots(ctx)]

@save
def includes_skipped(ctx):
    '''
    The number of ballots that have an undervote followed by an overvote or a
    valid ranking
    '''
    return sum(skipped(ctx))


@save
def cleaned(ctx):
    """
        retrieve ballots (list of lists, each containing candidate names in
        rank order, also write-ins marked with WRITEIN constant, and OVERVOTES and
        UNDERVOTES marked with their respective constants)

        For each ballot, return a cleaned version that has pre-skipped
        undervoted and overvoted rankings and only includes one ranking
        per candidate (the highest ranking for that candidate).

        Additionally, each ballot may be cut short depending on the
        -break_on_repeated_undervotes- and -break_on_overvote- settings for
        a contest.

        returns: list of cleaned ballot-lists
    """
    new = []
    for b in ballots(ctx):
        result = []
        # look at successive pairs of rankings - zip list with itself offset by 1
        for elem_a, elem_b in zip(b, b[1:]+[None]):
            if break_on_repeated_undervotes(ctx) and {elem_a, elem_b} == {UNDERVOTE}:
                break
            if break_on_overvote(ctx) and elem_a == OVERVOTE:
                break
            if elem_a not in [*result, OVERVOTE, UNDERVOTE]:
                result.append(elem_a)
        new.append(result)
    return new

@save
def until2rcv(ctx):
    """
    run an rcv election until there are two candidates remaining
    """
    rounds = []
    bs = [list(i) for i in cleaned(ctx)]
    while True:
        rounds.append(list(zip(*Counter(b[0] for b in bs if b).most_common())))
        finalists, tallies = rounds[-1]
        if len(finalists) < 3:
            return rounds
        bs = [keep(finalists[:-1], b) for b in bs]

@save
def top2_winners_margin(ctx):
    """
    winner's votes less runner-up's votes
    (after running an rcv to two candidates and possibly past the round in
    which the winner receives 50% of the remaining vote)
    """
    last_round = until2rcv(ctx)[-1][1]
    if len(last_round) == 2:
        return last_round[0] - last_round[1]

@save
def top2_winners_vote_increased(ctx):
    """
    If you run an RCV contest until there are two or fewer candidates left,
    does the number of votes the winner receive increase from the first to the
    last round?
    """
    first = until2rcv(ctx)[0]
    start = first[1][first[0].index(winner(ctx))]
    return until2rcv(ctx)[-1][1][0] > start

@save
def top2_winners_fraction(ctx):
    """
    If you run an RCV contest until there are two or fewer candidates left,
    what fraction of the votes that cast validly ranked at least one candidate
    does the winner eventually receive?
    """
    return until2rcv(ctx)[-1][1][0]/float(sum(until2rcv(ctx)[0][1]))

@save
def top2_majority(ctx):
    """
    If you run an RCV contest until there are two or fewer candidates left,
    Does the winner receive over half the votes that cast validly ranked at
    least one candidate?
    """
    return top2_winners_fraction(ctx) > 0.5

@save
def top2_winner_over_40(ctx):
    """
    If you run an RCV contest until there are two or fewer candidates left,
    Does the winner receive over 40% of the votes that cast validly ranked at
    least one candidate?
    """
    return top2_winners_fraction(ctx) > 0.4


@save
def head_to_head(ctx):
    tallies = Counter()
    for ballot in cleaned(ctx):
        nowritein = [i for i in ballot if i != WRITEIN]
        tallies.update(combinations(nowritein,2))
        tallies.update(product(set(nowritein), candidates(ctx)-set(nowritein)))
    for key in sorted(tallies):
        k0, k1 = key
        print(date(ctx),office(ctx),place(ctx),k0,k1,tallies[key],tallies[(k1,k0)],sep='\t')

def blank(ctx):
    return None



### Tabulation ###
def remove(x,l):
    return [i for i in l if i != x]

def keep(x,l):
    return [i for i in l if i in x]



def rcv_ballots(clean_ballots):
    rounds = []
    ballots = remove([],deepcopy(clean_ballots))
    while True:
        rounds.append(list(zip(*Counter(b[0] for b in ballots).most_common())))
        finalists, tallies = rounds[-1]
        if tallies[0]*2 > sum(tallies):
            return rounds
        ballots = remove([], (keep(finalists[:-1], b) for b in ballots))


@save
def rank_and_add_borda(ctx):
    """https://voterschoose.info/wp-content/uploads/2019/04/Tustin-White-Paper.pdf"""
    c = Counter()
    for b in cleaned(ctx):
        c.update({v:1/i for i,v in enumerate(b,1)})
    return [i for i,_ in c.most_common()[:number(ctx)]]

@save
def bottom_up_stv(ctx):
    ballots = deepcopy(cleaned(ctx))
    rounds = []
    while True:
        rounds.append(list(zip(*Counter(b[0] for b in ballots).most_common())))
        finalists,_ = rounds[-1]
        if len(finalists) == number(ctx):
            return finalists
        ballots = remove([], (keep(finalists[:-1], b) for b in ballots))

@save
def stv(ctx):
    rounds = []
    bs = [(b,Fraction(1)) for b in cleaned(ctx) if b]
    threshold = int(len(bs)/(number(ctx)+1)) + 1
    winners = []
    while len(winners) != number(ctx):
        totals = defaultdict(int)
        for c,v in bs:
            totals[c[0]] += v
        ordered = sorted(totals.items(), key=lambda x:-x[1])
        rounds.append(ordered)
        names, tallies = zip(*ordered)
        if len(names) + len(winners) == number(ctx):
            winners.extend(names)
            break
        if threshold < tallies[0]:
            winners.append(names[0])
            bs = ((keep(names[1:], c),
                    v*(names[0] != c[0] or (tallies[0]-threshold)/tallies[0]))
                   for c,v in bs)
        else:
            bs = ((keep(names[:-1], c), v) for c,v in bs)
        bs = [b for b in bs if b[0]]
    return winners

@save
def in_common(ctx):
    return len(set(stv(ctx)) & set(seq_stv(ctx)))

@save
def not_in_common(ctx):
    return len(set(stv(ctx)) ^ set(seq_stv(ctx)))//2

@save
def only_seq(ctx):
    return [name_map(ctx)(i) for i in set(seq_stv(ctx)) - set(stv(ctx))]

@save
def only_reg(ctx):
    return [name_map(ctx)(i) for i in set(stv(ctx)) - set(seq_stv(ctx))]

def name_map(ctx):
    mapping = {}
    with suppress(KeyError), open(glob(ctx['chp'])[0]) as f:
        for i in f:
            parts = i.split(' ')
            if parts[0] == '.CANDIDATE':
                mapping[parts[1].strip(',')] = ' '.join(parts[2:]).replace('"','').replace('\n', '')
    if mapping:
        return lambda x: mapping[x]
    return lambda x: x

def rcv_stack(ballots):
    stack = [ballots]
    results = []
    while stack:
        ballots = stack.pop()
        finalists, tallies = map(list, zip(*Counter(b[0] for b in ballots if b).most_common()))
        if tallies[0]*2 > sum(tallies):
            results.append((finalists, tallies))
        else:
            losers = finalists[tallies.index(min(tallies)):]
            for loser in losers:
                stack.append([keep(set(finalists)-set([loser]), b) for b in ballots])
            if len(losers) > 1:
                stack.append([keep(set(finalists)-set(losers), b) for b in ballots])
    return results


def minneapolis_undervote(ctx):
    """Ballots containing only"""
    return effective_ballot_length(ctx).get(0,0)

def minneapolis_total(ctx):
    return total(ctx) - minneapolis_undervote(ctx)

@save
def naive_tally(ctx):
    """ Sometimes reported if only one round, only nominal 1st place rankings count"""
    return Counter(b[0] if b else None for b in ballots(ctx))


@save
def winner_ranking(ctx):
    return Counter(b.index(winner(ctx))+1 if winner(ctx) in b else None
                    for b in cleaned(ctx))
@save
def winner_in_top_3(ctx):
    return sum(v for k,v in winner_ranking(ctx).items() if k is not None and k<4)


@save
def consensus(ctx):
    return winner_in_top_3(ctx) / (total(ctx) - undervote(ctx))

@save
def winners_first_round_share(ctx):
    return rcv(ctx)[0][1][0] / (total(ctx) - undervote(ctx))

@save
def winners_final_round_share(ctx):
    return rcv(ctx)[-1][1][0] / (total(ctx) - undervote(ctx))

@save
def rcv(ctx):
    rounds = []
    bs = [list(i) for i in cleaned(ctx)]
    while True:
        rounds.append(list(zip(*Counter(b[0] for b in bs if b).most_common())))
        finalists, tallies = rounds[-1]
        if tallies[0]*2 > sum(tallies):
            return rounds
        bs = [keep(finalists[:-1], b) for b in bs]


@save
def margin_when_2_left(ctx):
    ballots = remove([], (remove(UNDERVOTE, b) for b in cleaned(ctx)))
    while True:
        finalists, tallies = zip(*Counter(b[0] for b in ballots).most_common())
        if len(tallies) == 1:
            return tallies[0]
        if len(tallies) == 2:
            return tallies[0] - tallies[-1]
        ballots = remove([], (keep(finalists[:-1], b) for b in ballots))

@save
def margin_when_winner_has_majority(ctx):
    last_tally = rcv(ctx)[-1][1]
    if len(last_tally)<2:
        return last_tally[0]
    else:
        return last_tally[0] - last_tally[1]

def rcvreg(ballots):
    rounds = []
    while True:
        rounds.append(list(zip(*Counter(b[0] for b in ballots).most_common())))
        finalists, tallies = rounds[-1]
        if tallies[0]*2 > sum(tallies):
            return rounds
        ballots = remove([], (keep(finalists[:-1], b) for b in ballots))

def last5rcv(ctx):
    return rcv(ctx)[-5:]


@save
def winner(ctx):
    return rcv(ctx)[-1][0][0]

def finalists(ctx):
    return rcv(ctx)[-1][0]

@save
def first_round(ctx):
    return [next((c for c in b if c != UNDERVOTE), UNDERVOTE)
            for b in ballots(ctx)]


### TODO: exhausted should not include straight undervotes nor
### per Drew
@save
def exhausted(ctx):
    return [not set(finalists(ctx)) & set(b) for b in cleaned(ctx)]

@save
def later_round_exhausted(ctx):
    return [not (set(finalists(ctx)) & set(b)) and bool(b) for b in cleaned(ctx)]

@save
def total_exhausted(ctx):
    '''
    Number of ballots (including ballots made up of only undervotes or
    overvotes) that do not rank a finalist.
    '''
    return sum(exhausted(ctx))

@save #fixme
def involuntarily_exhausted(ctx):
    return [a and b for a,b in zip(fully_ranked(ctx), exhausted(ctx))]

@save
def total_involuntarily_exhausted(ctx):
    '''
    Number of validly fully ranked ballots that do not rank a finalist.
    '''
    return sum(involuntarily_exhausted(ctx))

@save
def voluntarily_exhausted(ctx):
    return [a and not b
            for a,b in zip(exhausted(ctx),involuntarily_exhausted(ctx))]

@save
def total_voluntarily_exhausted(ctx):
    '''
    Number of ballots that do not rank a finalists and aren't fully ranked.
    This number includes ballots consisting of only undervotes or overvotes.
    '''
    return sum(voluntarily_exhausted(ctx))

def margin_greater_than_all_exhausted(ctx):
    return margin_when_2_left(ctx) > total_exhausted(ctx)

@save
def exhausted_by_undervote(ctx):
    if break_on_repeated_undervotes(ctx):
        return sum(ex and not ex_over and  has_under for ex,ex_over,has_under in
                  zip(exhausted(ctx), exhausted_by_overvote(ctx), has_undervote(ctx)))
    return 0


@save
def exhausted_by_overvote(ctx):
    if break_on_repeated_undervotes(ctx):
        return [ex and over<under for ex,over,under in
                zip(exhausted(ctx),overvote_ind(ctx),repeated_undervote_ind(ctx))]

    return [ex and over for ex,over in zip(exhausted(ctx),overvote(ctx))]

@save
def total_exhausted_by_overvote(ctx):
    return sum(exhausted_by_overvote(ctx))

@save
def total_exhausted_not_by_overvote(ctx):
    return sum(ex and not ov
                for ex,ov in zip(exhausted(ctx), exhausted_by_overvote(ctx)))

@save
def validly_ranked_winner(ctx):
    return sum(winner(ctx) in b for b in cleaned(ctx))

@save
def ranked_winner(ctx):
    return sum(winner(ctx) in b for b in ballots(ctx))

@save
def ranked_finalist(ctx):
    return [not ex for ex in exhausted(ctx)]


def before(x, y, l):
    for i in l:
        if i == x:
            return 1
        if i == y:
            return -1
    return 0


@save
def losers(ctx):
    return set(candidates(ctx)) - {winner(ctx)}


def come_from_behind(ctx):
    return winner(ctx) != rcv(ctx)[0][0][0]


@save
def candidate_combinations(ctx):
    return Counter(tuple(sorted(b)) for b in cleaned(ctx))


@save
def orderings(ctx):
    return Counter(map(tuple, cleaned(ctx))).most_common()


@save
def top2(ctx):
    return Counter(tuple(i[:2]) for i in cleaned(ctx)).most_common()


@save
def next_choice(ctx):
    c = Counter()
    for b in cleaned(ctx):
        c.update(zip([None, *b], [*b, None]))
    return c.most_common()


@save
def repeated_undervote_ind(ctx):
    rs = []
    for b in ballots(ctx):
        rs.append(float('inf'))
        z = list(zip(b,b[1:]))
        uu = (UNDERVOTE,UNDERVOTE)
        if uu in z:
            occurance = z.index(uu)
            for c in b[occurance+1:]:
                if c != UNDERVOTE:
                    rs[-1] = occurance
                    break
    return rs

@save
def overvote_ind(ctx):
    return [b.index(OVERVOTE) if OVERVOTE in b else float('inf')
            for b in ballots(ctx)]

def two_repeated(ctx):
    return count_duplicates(ctx).get(2,0)

def three_repeated(ctx):
    return count_duplicates(ctx).get(3,0)

@save
def overvote(ctx):
    return [OVERVOTE in b for b in ballots(ctx)]

@save
def total_overvote(ctx):
    '''
    Number of ballots with at least one overvote.
    '''
    return sum(overvote(ctx))

@save
def total_skipped(ctx):
    return sum(skipped(ctx))

@save
def irregular(ctx):
    return sum(map(any, zip(duplicates(ctx), overvote(ctx), skipped(ctx))))


@save
def fully_ranked(ctx):
    return [len(b) == len(a) or set(b) >= candidates(ctx)
            for a,b in zip(ballots(ctx), cleaned(ctx))]

@save
def candidates(ctx):
    cans = set()
    for b in ballots(ctx):
        cans.update(b)
    return cans - {OVERVOTE, UNDERVOTE, WRITEIN}


@save
def effective_subsets(ctx):
    c = Counter()
    for b in cleaned(ctx):
        unranked = candidates(ctx) - set(b)
        c.update((b[0], u) for u in unranked)
        for i in range(2, len(b) + 1):
            c.update(combinations(b, i))
            c.update((*b[:i], u) for u in unranked)
    return c


@save
def preference_pairs(ctx):
    return [set(product(b, candidates(ctx) - set(b))) | set(combinations(b, 2))
            for b in cleaned(ctx)]


@save
def preference_pairs_count(ctx):
    c = Counter()
    for i in preference_pairs(ctx):
        c.update(i)
    return c


@save
def all_pairs(ctx):
    return list(preference_pairs_count(ctx).keys())


@save
def precincts(ctx):
    return [i.precinct.replace('/', '+')
            for i in ctx['parser'](ctx)]


@save
def precinct_totals(ctx):
    return Counter(precincts(ctx))


@save
def precinct_overvotes(ctx):
    return Counter(p for p, o in zip(precincts(ctx), overvote(ctx)) if o)


@save
def precinct_participation(ctx):
    return Counter(p for p, o in zip(precincts(ctx), cleaned(ctx)) if o)


@save
def precinct_ranked_finalists(ctx):
    return Counter(p for p, o in zip(precincts(ctx), exhausted(ctx)) if not o)


@save
def precinct_overvote_rate(ctx):
    return {k: precinct_overvotes(ctx)[k] / v for k, v in precinct_totals(ctx).items()}


@save
def unique_precincts(ctx):
    return set(precincts(ctx))


@lru_cache(maxsize=2)
def processed_sov(file_name):
    result = {}
    asian_ethnicities = ['kor', 'jpn', 'chi', 'ind', 'viet', 'fil']
    with open(file_name) as f:
        reader = csv.DictReader(f)
        for i in reader:
            result[i['srprec']] = {
                'total': int(i['totreg_r']),
                'latin': sum(int(i[k]) for k in i if k.startswith('hisp')),
                'asian': sum(int(i[k]) for k in i
                             if any(map(k.startswith, asian_ethnicities)))
            }
    return result


@save
def precinct_percent_sov(ctx, precinct, ethnicity):
    total = 0
    ethnic = 0
    int_year = int(date(ctx))
    year = str(min(int_year + int_year % 2, 2018))
    precincts = split_precincts(precinct)
    file_name = 'SOV/c{}_g{}_voters_by_g{}_srprec.csv'.format(county(ctx), year[-2:], year[-2:])
    for p in precincts:
        try:
            ethnic += processed_sov(file_name)[p][ethnicity]
            total += processed_sov(file_name)[p]['total']
        except KeyError:
            print('\tSOV:\tPOSSIBLE MISSING OR CONSOLIDATED PRECINCT IN SOV:', p)

    return ethnic / total if total else 0


@lru_cache(maxsize=11)
def cvap_by_block(file_name):
    table = DBF(file_name)
    counties = {'001', '075'}
    result = {}
    for row in table:
        block = next(v for k, v in row.items() if 'BLOCK' in k)
        cvap = next(v for k, v in row.items() if 'CVAP' in k)
        if block[2:5] in counties:
            result[block] = cvap
    return result


@save
def block_ethnicities(ctx, ethnicity):
    year = {'2019': '2017', '2018': '2017', '2012': '2013'}.get(date(ctx), date(ctx))
    file_name = 'CVAPBLOCK/{}/{}_cvap_by_block.dbf'.format(year, ethnicity.replace(' ', '_'))
    return cvap_by_block(file_name)


@save
def sr_blk_map(file_name):
    _, state, county, *_ = file_name.split('/')
    result = defaultdict(list)
    with open(file_name) as f:
        next(f)
        for line in f:
            srprec, tract, block, blkreg, srtotreg, pctsrprec, blktotreg, pctblk = \
                [i.strip('"') for i in line.strip('\n').split(',')]
            result[srprec].append((state + county + tract.zfill(6) + block, float(pctblk) / 100))
    return dict(result)


def split_precincts(precinct):
    split = precinct.split('+')
    if len(split) == 1 or len(set(map(len, split))) == 1:
        return split
    first = split[0]
    return [first[:-len(i)] + i for i in split]


@save
def precinct_ethnicity_totals(ctx, precinct, ethnicity):
    ethnic = 0
    int_year = int(date(ctx))
    year = str(int_year - int_year % 2)
    precinct_block_fraction = 'precinct_block_maps/06/{}/c{}_g{}_sr_blk_map.csv'.format(county(ctx), county(ctx),
                                                                                        year[-2:])
    precincts = split_precincts(precinct)
    for p in precincts:
        try:
            blocks = sr_blk_map(precinct_block_fraction)[p]
        except:
            print("\tCVAP:\tPOSSIBLE MISSING PRECINCT:", p)
            continue
        for (b, f) in blocks:
            for eth in cvap_ethnicities(ethnicity):
                ethnic += block_ethnicities(ctx, eth)[b] * float(f)
    return ethnic


@save
def election_ethnic_cvap_totals(ctx, ethnicity):
    if state_code(ctx) is None or int(date(ctx)) < 2012:
        return None or None
    return sum(precinct_ethnicity_totals(ctx, p, ethnicity)
               for p in unique_precincts(ctx))


def cvap_ethnicities(eth):
    return {
        'black': ['Black or African American Alone'],
        'white': ['White Alone'],
        'latin': ['Hispanic or Latino'],
        'asian': ['Asian Alone'],
        'total': ['Total'],
        'other': ['American Indian or Alaska Native Alone',
                  'Native Hawaiian or Other Pacific Islander Alone',
                  'American Indian or Alaska Native and White', 'Asian and White',
                  'Black or African American and White',
                  'American Indian or Alaska Native and Black or African American',
                  'Remainder of Two or More Race Responses'],
    }[eth]


@save
def precinct_percent_cvap(ctx, precinct, ethnicity):
    total = 0
    ethnic = 0
    int_year = int(date(ctx))
    year = str(int_year - int_year % 2)
    precinct_block_fraction = 'precinct_block_maps/06/{}/c{}_g{}_sr_blk_map.csv'.format(county(ctx), county(ctx),
                                                                                        year[-2:])
    precincts = split_precincts(precinct)
    for p in precincts:
        try:
            blocks = sr_blk_map(precinct_block_fraction)[p]
        except:
            print("\tCVAP:\tPOSSIBLE MISSING PRECINCT:", p)
            continue
        for (b, f) in blocks:
            for eth in cvap_ethnicities(ethnicity):
                ethnic += block_ethnicities(ctx, eth)[b] * float(f)
            total += block_ethnicities(ctx, 'Total')[b] * float(f)
    return ethnic / total if total else 0


def precinct_estimate(eth, ethnicity_rate, precinct_metric, ctx):
    '''
    assumes precinct explains behavior
    '''
    if state_code(ctx) is None or int(date(ctx)) < 2012:
        return None
    numerator = 0
    for precinct, good_ballots in precinct_metric(ctx).items():
        numerator += good_ballots * ethnicity_rate(ctx, precinct, eth)
    return numerator


def ethnicity_estimate(eth, ethnicity_rate, precinct_metric, ctx):
    '''
    assumes group status explains behavior
    '''
    if state_code(ctx) is None or int(date(ctx)) < 2012:
        return None
    b = []
    A = []
    for precinct, total in precinct_totals(ctx).items():
        b.append(precinct_metric(ctx).get(precinct, 0))
        pct = ethnicity_rate(ctx, precinct, eth)
        specific = total * pct
        general = total * (1 - pct)
        A.append([specific, general])
    rate = scipy.optimize.lsq_linear(A, b, (0, 1))['x'][0]
    return sum(rate * i[0] for i in A)


STAT_ESTIMATORS = [precinct_estimate, ethnicity_estimate]
PRECINCT_STATS = [precinct_participation, precinct_ranked_finalists, precinct_overvotes]
PRECINT2ETHNICITY = [precinct_percent_cvap, precinct_percent_sov]
ETHS = ['black', 'white', 'latin', 'asian', 'other']
ETHNICITY_STATS = [partial(*prod)
                   for prod in product(STAT_ESTIMATORS, ETHS, PRECINT2ETHNICITY, PRECINCT_STATS)
                   if prod[1] in {'latin', 'asian'} or prod[2].__name__[-3:] != 'sov']
for f in ETHNICITY_STATS:
    f.__name__ = f.func.__name__ + '(' + ','.join(a.__name__ if callable(a) else str(a) for a in f.args) + ')'


def asian_ethnic_cvap_totals(ctx):
    return election_ethnic_cvap_totals(ctx, 'asian')


def black_ethnic_cvap_totals(ctx):
    return election_ethnic_cvap_totals(ctx, 'black')


def latin_ethnic_cvap_totals(ctx):
    return election_ethnic_cvap_totals(ctx, 'latin')


def white_ethnic_cvap_totals(ctx):
    return election_ethnic_cvap_totals(ctx, 'white')


def cvap_totals(ctx):
    return election_ethnic_cvap_totals(ctx, 'total')


def state_code(ctx):
    return {
        'Oakland': '06',
        'San Francisco': '06',
        'San Leandro': '06',
        'Berkeley': '06'
    }.get(place(ctx))


def county(ctx):
    return {
        'Oakland': '001',
        'Berkeley': '001',
        'San Leandro': '001',
        'San Francisco': '075'
    }.get(place(ctx))


def election_type(ctx):
    return 'g'

@save
def ballots(ctx):
    return ctx['parser'](ctx)

@tmpsave
def write_ins(ctx):
    return 0

@tmpsave
def number(ctx):
    return {
        ('Cambridge', 'School Committee'): 6,
        ('Cambridge', 'City Council'): 9,
        ('Minneapolis', 'BOE'): 2,
        ('Minneapolis', 'Park At Large'): 3,
    }.get((ctx['place'],ctx['office']), 1)

def ballot_length(ctx):
    return len(ballots(ctx)[0])

@save
def one_pct_cans(ctx):
    return sum(1 for i in rcv(ctx)[0][1] if i/sum(rcv(ctx)[0][1]) >= 0.01)

@tmpsave
def dop(ctx):
    return ','.join(str(f(ctx)) for f in [date, office, place])

@save
def undervote(ctx):
    '''
    Ballots completely made up of undervotes (no marks).
    '''
    return sum(c == UNDERVOTE for c in first_round(ctx))

@save


ALLSTATS = [place, state, date, office,
    total, undervote, total_overvote, first_round_overvote,
    total_exhausted_by_overvote, total_fully_ranked, ranked2,
    ranked_winner,
    two_repeated, three_repeated, total_skipped, irregular, total_exhausted,
    total_exhausted_not_by_overvote, total_involuntarily_exhausted,
    effective_ballot_length, minneapolis_undervote, minneapolis_total,
    total_voluntarily_exhausted, condorcet, come_from_behind, number_of_rounds,
    finalists, winner, exhausted_by_undervote,
    naive_tally, candidates, count_duplicates,
    any_repeat, validly_ranked_winner, margin_when_2_left,
    margin_when_winner_has_majority,
    cvap_totals,
    asian_ethnic_cvap_totals, black_ethnic_cvap_totals,
    latin_ethnic_cvap_totals, white_ethnic_cvap_totals
] + ETHNICITY_STATS

def calc(ctx, functions):
    print(dop(ctx))
    results = {}
    for f in functions:
        results[f.__name__] = f(ctx)
    return results


def main():
    p = ArgumentParser()
    p.add_argument('-j', '--json', action='store_true')
    a = p.parse_args()
    if a.json:
        for k in manifest.competitions.values():
            pprint(calc(k, FUNCTIONS))
        return

    with open('results.csv', 'w', newline='\n') as f:
        w = csv.writer(f)
        w.writerow([fun.__name__ for fun in ALLSTATS])
        w.writerow([' '.join((fun.__doc__ or '').split())
                    for fun in ALLSTATS])
        for k in sorted(manifest.competitions.values(), key=lambda x: x['date']):
            if True:  # k['office'] == 'Democratic Primary for Governor': #county(k) in {'075'} and int(date(k)) == 2012:
                result = calc(k, ALLSTATS)
                w.writerow([result[fun.__name__] for fun in ALLSTATS])


#    with open('headline.csv', 'w') as f:
#        w = csv.writer(f)
#        w.writerow([fun.__name__ for fun in HEADLINE_STATS])
#        w.writerow([' '.join((fun.__doc__ or '').split())
#                     for fun in HEADLINE_STATS])
#        for k in sorted(manifest.competitions.values(),key=lambda x: x['date']):
#            if True: #k['office'] == 'Democratic Primary for Governor': #county(k) in {'075'} and int(date(k)) == 2012:
#                result = calc(k, HEADLINE_STATS)
#                w.writerow([result[fun.__name__] for fun in HEADLINE_STATS])

if __name__ == '__main__':
    main()
