# serv499 / client499 (CSSE2310 Assignment 4, 2013)
#
# Copyright (c) 2013, Joel Addison (jea)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# The card suits, indexed starting at 1
SUITS = {
    'S': 1,
    'C': 2,
    'D': 3,
    'H': 4
}

# All of the allowed ranks, in increasing order of
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']

# The position of the rank and suit in a 2 char card value
RANK = 0
SUIT = 1

# Bid results
BID_INVALID = 0
BID_VALID = 1
BID_PASS = 2

# Bid min and max
MIN_BID = 4
MAX_BID = 9


def valid_bid(current_bid, bid):
    if len(bid) != 2:
        return BID_INVALID

    num, suit = bid
    try:
        num = int(num)
    except ValueError:
        if bid != "PP":
            return BID_INVALID

    if bid != "PP" and (num < MIN_BID or num > MAX_BID
            or suit not in SUITS.keys()):
        return BID_INVALID  # Bad rank or suit, and not a pass

    # First bidder
    if not current_bid:
        if bid == "PP":
            return BID_INVALID  # First bidder cannot pass
        return BID_VALID

    current_num, current_suit = current_bid
    current_num = int(current_num)

    # All other bidders
    if bid == "PP":
        return BID_PASS
    elif (num > current_num or (
        num == current_num and SUITS[suit] > SUITS[current_suit])):
        # New bid higher than current bid.
        return BID_VALID
    return BID_INVALID


def higher_card(card1, card2, lead_suit, trumps):
    if (not card2 or
            (card1[SUIT] == trumps and card2[SUIT] != trumps) or
            (card1[SUIT] == card2[SUIT] and
            (card2[SUIT] == trumps or card2[SUIT] == lead_suit) and
            RANKS.index(card1[RANK]) > RANKS.index(card2[RANK]))):
        return True
    return False


def rank_sort(card1, card2):
    if card1[RANK] == card2[RANK]:
        return 0
    elif RANKS.index(card1[RANK]) < RANKS.index(card2[RANK]):
        return -1
    else:
        return 1


def valid_play(lead, card, hand):
    if len(card) != 2:
            return False  # Card is incorrent length - invalid

    rank, suit = card
    if rank not in RANKS or suit not in SUITS.keys():
        return False  # Bad rank or suit, and not a pass
    elif card not in hand:
        return False  # Player is trying to use a card they do not have

    # Check if card matches lead suit, if player has such a card available.
    if lead and suit != lead:
        for card in hand:
            if card[SUIT] == lead:
                # Player is trying to play a card from another suit,
                # but they still have cards of the lead suit left
                return False

    # Play is valid
    return True
