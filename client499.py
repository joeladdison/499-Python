#!/usr/bin/env python
from __future__ import print_function
import sys
import socket
import signal

from game499 import *


class Player(object):
    sock = None
    sock_file = None
    player_name = None
    game_name = None
    hand = None
    sorted_hand = {}
    last_play = None
    made_bid = False


def signal_handler(signal, frame):
    sys.exit(0)


def connect_to_server(port, hostname):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((hostname, port))
    except socket.error:
        print("Bad Server.", file=sys.stderr)
        sys.exit(2)
    return sock


def send_msg(sock, message, add_newline=True):
    if add_newline:
        message = "%s\n" % message
    try:
        sock.sendall(message)
    except socket.error:
        print("Protocol Error.", file=sys.stderr)
        sys.exit(6)


def recv_msg(sock_file):
    server_error = False
    try:
        data = sock_file.readline()
    except socket.error:
        server_error = True
    if server_error or not data:
        print("Protocol Error.", file=sys.stderr)
        sys.exit(6)
    return data.strip()


def initialise_game(player):
    # Send player name
    send_msg(player.sock, player.player_name)
    # Send game name
    send_msg(player.sock, player.game_name)
    # Wait for greeting
    receive_and_parse_message(player, ['M'])


def sort_hand(player, hand):
    suits = {'C': [], 'S': [], 'D': [], 'H': []}

    # Split cards up into a list
    all_cards = [hand[i] + hand[i + 1] for i in range(0, len(hand), 2)]
    for card in all_cards:
        suits[card[SUIT]].append(card)

    for suit, cards in sorted(suits.items(), key=lambda x: SUITS[x[0]]):
        sorted_cards = sorted(cards, cmp=rank_sort, reverse=True)
        player.sorted_hand[suit] = sorted_cards

    # Store for later use
    player.hand = all_cards


def print_hand(player):
    for suit, cards in sorted(player.sorted_hand.items(), key=lambda x: SUITS[x[0]]):
        suit_cards = [r for r, _ in cards]
        if suit_cards:
            print("%s: %s" % (suit, " ".join(suit_cards)))
        else:
            print("%s:" % suit)


def get_user_input(prompt):
    try:
        response = raw_input(prompt)
    except EOFError:
        print("User Quit.", file=sys.stderr)
        sys.exit(7)
    return response


def make_bid(player, current):
    # Build prompt for bid
    prompt = ""
    if current:
        prompt = "[%s] - Bid (or pass)> " % current
    else:
        prompt = "Bid> "

    # Get bid from user
    while True:
        bid = get_user_input(prompt)
        if valid_bid(current, bid) in [BID_VALID, BID_PASS]:
            send_msg(player.sock, bid)
            break


def play_card(player, lead):
    prompt = "Lead> "
    if lead:
        prompt = "[%s] play> " % lead

    while True:
        print_hand(player)
        move = get_user_input(prompt)
        if valid_play(lead, move, player.hand):
            # Card is fine, so send back to server
            send_msg(player.sock, move)
            player.last_play = move
            break


def receive_and_parse_message(player, expected=[]):
    message = recv_msg(player.sock_file)
    extended_expected = expected + ['M', 'O']
    if not message or (expected and message[0] not in extended_expected):
        print("Protocol Error.", file=sys.stderr)
        sys.exit(6)

    if message[0] == 'M':
        # Chat message
        print("Info: %s" % message[1:])
        if 'M' not in expected:
            return True
    elif message[0] == 'H':
        sort_hand(player, message[1:])
        print_hand(player)
    elif message[0] == 'B':
        make_bid(player, message[1:])
    elif message[0] == 'L':
        play_card(player, '')
    elif message[0] == 'P':
        play_card(player, message[1:])
    elif message[0] == 'A':
        player.hand.remove(player.last_play)
        player.sorted_hand[player.last_play[SUIT]].remove(player.last_play)
    elif message[0] == 'T':
        player.made_bid = True
    elif message[0] == 'O':
        # Game over
        try:
            player.sock.shutdown(socket.SHUT_RDWR)
            player.sock.close()
        except socket.error:
            pass
        sys.exit(0)

    return False


def play_game(player):
    # Play the game
    while True:
        # Receive hand
        while receive_and_parse_message(player, ['H']):
            pass

        player.made_bid = False
        # Perform bidding
        while not player.made_bid:
            receive_and_parse_message(player, ['B', 'T'])

        # Play cards for rest of the game
        while player.hand:
            while receive_and_parse_message(player, ['L', 'P', 'A']):
                pass


def main():
    signal.signal(signal.SIGINT, signal_handler)

    if len(sys.argv) not in [4, 5]:
        print("Usage: client499 name game port [host]", file=sys.stderr)
        sys.exit(1)

    player_name = sys.argv[1]
    game_name = sys.argv[2]
    try:
        port = int(sys.argv[3])
    except ValueError:
        port = 0
    hostname = "localhost"
    if len(sys.argv) == 5:
        hostname = sys.argv[4]

    if not player_name or not game_name or port < 1 or port > 65535:
        print("Invalid Arguments.", file=sys.stderr)
        sys.exit(4)

    sock = connect_to_server(port, hostname)

    p = Player()
    p.player_name = player_name
    p.game_name = game_name
    p.sock = sock
    p.sock_file = sock.makefile()

    initialise_game(p)
    play_game(p)

    sock.close()

    sys.exit(0)


if __name__ == '__main__':
    main()
