# encoding: utf-8
#
# Copyright (C) 2011 Chris Jerdonek.  All rights reserved.
#

import logging


_log = logging.getLogger(__name__)


def increment_dict_total(mapping, key):
    try:
        mapping[key] += 1
    except KeyError:
        mapping[key] = 1


class Stats(object):

    """
    Attributes:

    ballot_position: dict of the number of times each candidate appears at
      each of the three positions on the ballot.  The position is the
      effective position, so that [UNDERVOTE, A, B] results in [A, B].
      Each triple is [first, second, third].

    combinations: a dict of set() to int keeping track of how many times
      each combination of candidates appears.
    orderings: a dict of tuple() to int keeping track of how many times
      each effective ordering of candidates appears.
    """

    def __init__(self, candidates, winner_id):

        # These dicts are all grouped by first-round choice.
        number_ranked = {}
        ranked_winner = {}
        ranked_finalist = {}
        truly_exhausted = {}
        ballot_position = {}
        did_sweep = {}

        combinations = {}
        orderings = {}

        for candidate_id in candidates:
            ballot_position[candidate_id] = 3 * [0]  # [first, second, third]
            number_ranked[candidate_id] = 3 * [0]  # [ranked3, ranked2, ranked1]
            ranked_winner[candidate_id] = 0
            ranked_finalist[candidate_id] = 0
            truly_exhausted[candidate_id] = 0
            did_sweep[candidate_id] = 0

        # Initialize condorcet pairs against the winner.
        condorcet = {}
        for candidate_id in candidates:
            if candidate_id == winner_id:
                continue
            condorcet[(candidate_id, winner_id)] = 0
            condorcet[(winner_id, candidate_id)] = 0

        self.total = 0
        self.undervotes = 0
        self.has_overvote = 0
        self.has_skipped = 0
        self.first_round_overvotes = 0
        self.exhausted_by_overvote = 0  # excludes first-round overvotes.

        # The total of the winner in the final round.
        # There may be more than two finalists in the final round.
        self.final_round_winner_total = 0

        self.duplicates = {2: 0, 3: 0}

        self._condorcet = condorcet
        self._number_ranked = number_ranked

        self.ballot_position = ballot_position
        self.combinations = combinations
        self.orderings = orderings
        self.ranked_winner = ranked_winner
        self.ranked_finalist = ranked_finalist
        self.truly_exhausted = truly_exhausted
        self.did_sweep = did_sweep

    @property
    def has_dup(self):
        return sum(self.duplicates.values())

    @property
    def irregular(self):
        return sum([self.has_overvote, self.has_skipped, self.duplicates[2], self.duplicates[3]])

    @property
    def voted(self):
        """
        Get the number of voted ballots.

        """
        return self.total - self.undervotes

    @property
    def first_round_continuing(self):
        return self.voted - self.first_round_overvotes

    @property
    def final_round_continuing(self):
        return sum([value for value in self.ranked_finalist.values()])

    @property
    def exhausted(self):
        """
        Does not include first-round overvotes or exhausted by overvote.

        """
        return self.first_round_continuing - (self.final_round_continuing + self.exhausted_by_overvote)

    @property
    def truly_exhausted_total(self):
        return sum([value for value in self.truly_exhausted.values()])

    def get_first_round(self, candidate):
        """
        Return the first-round count for a candidate.

        """
        return self.ballot_position[candidate][0]

    def add_number_ranked(self, candidate_id, number_ranked):
        index = 3 - number_ranked
        self._number_ranked[candidate_id][index] += 1

    def get_number_ranked(self, candidate_id):
        """
        Return the number ranked as a list: [ranked3, ranked2, ranked1].

        """
        return list(self._number_ranked[candidate_id])

    def add_condorcet_winner(self, winning_id, losing_id):
        self._condorcet[(winning_id, losing_id)] += 1

    def get_condorcet_support(self, candidate_id1, candidate_id2):
        win_count = self._condorcet[(candidate_id1, candidate_id2)]
        lose_count = self._condorcet[(candidate_id2, candidate_id1)]
        total_count = win_count + lose_count
        return (win_count, total_count)

    def is_condorcet_winner(self, candidate_id, all_candidate_ids):
        """Return whether the given candidate is the Condorcet winner."""
        for other_id in set(all_candidate_ids) - set([candidate_id]):
            win_count, total_count = self.get_condorcet_support(candidate_id, other_id)
            if 1.0 * win_count / total_count <= 0.5:
                return False
        return True


