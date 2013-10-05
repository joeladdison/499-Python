#!/usr/bin/env python
from __future__ import print_function
import sys
import socket
import signal
import threading
import errno
import time
import select

from game499 import *

BACKLOG = 5


class Server(object):
    def __init__(self):
        self.sock = None
        self.greeting = ""
        self.deck_file = None
        self.decks = []
        self.pending = {}
        self.pending_games = []
        self.games = []
        self.scores = {}
        self.threads = []


class Player(object):
    def __init__(self):
        self.socket = None
        self.sock_file = None
        self.name = ""
        self.hand = []


class Game(object):
    def __init__(self):
        self.name = None
        self.server = None
        self.players = []
        self.scores = [0, 0]
        self.deck = 0
        self.lead_player = 0
        self.bid = ""
        self.trumps = ""
        self.bid_team = None
        self.running = True


class GameThread(threading.Thread):
    def __init__(self, game):
        threading.Thread.__init__(self)
        self.game = game

    def run(self):
        play_game(self.game)


# Global server variable, for use in signal handler.
server = None


def signal_handler(signal, frame):
    if server:
        # End running games
        for game in server.games:
            game.running = False
            # Close connections
            for p in game.players:
                close_player(p)

        # Close pending games

    # Exit the server
    sys.exit(0)


def create_server(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('localhost', port))
        s.listen(BACKLOG)
    except socket.error:
        if s:
            s.close()
        print("Port error", file=sys.stderr)
        sys.exit(5)
    return s


def read_decks(server):
    error = False
    line_count = 0

    for line in server.deck_file.readlines():
        line_count += 1
        line = line.rstrip()  # Strip newline character
        if len(line) != 104:
            error = True
            break
        all_cards = [line[i] + line[i + 1] for i in range(0, len(line), 2)]
        server.decks.append(all_cards)

    if error or line_count == 0:
        print("Bad deck", file=sys.stderr)
        sys.exit(7)


def close_player(player):
    print("Closing player: '%s'" % player.name)
    try:
        # Close the player socket file
        if player.sock_file:
            player.sock_file.close()

        # Close the player socket
        if player.socket:
            player.socket.shutdown(socket.SHUT_RDWR)
            player.socket.close()
    except socket.error:
        # Don't care, we were closing connection anyway
        pass


def end_game(game):
    print("Ending game: '%s'" % game.name)
    game.running = False
    # Send game over message
    send_message_to_players(game, "", message_type='O')
    # Close connections
    for p in game.players:
        close_player(p)
    # Remove game from the games list
    game.server.games.remove(game)


def get_client_input_timeout(game, player, timeout=10):
    client_error = False
    data = ''
    try:
        rlist, _, _ = select.select([player.sock_file], [], [], timeout)
        if rlist:
            data = player.sock_file.readline()
        else:
            # Timeout
            client_error = True
            print_to_player("MSorry, too slow.", player.sock_file)
            print("Kicked player due to read timeout.")
    except socket.error:
        client_error = True
    except MemoryError:
        client_error = True
        print_to_player("MNo thanks, I think that's too big", player.sock_file)
        print("Kicked player due to memory use.")

    if client_error or not data:
        # Client has disconnected during game, so end the game.
        if game:
            message = "%s disconnected early" % player.name
            send_message_to_players(game, message)
            game.running = False
        return
    return data.strip()


def print_to_player(message, socket_file):
    if socket_file:
        try:
            print(message, file=socket_file)
            socket_file.flush()
        except (socket.error, AttributeError):
            # We do not care about Broken Pipes at this stage
            pass


def send_message_to_players(game, message, message_type='M', skip_player=None):
    if game:
        for i, p in enumerate(game.players):
            if i == skip_player:
                continue
            print_to_player("%s%s" % (message_type, message), p.sock_file)


def deal_hand(game, deck):
    for i, card in enumerate(game.server.decks[deck]):
        game.players[i % 4].hand.append(card)

    for p in game.players:
        print_to_player("H%s" % ''.join(p.hand), p.sock_file)


def get_bids(game):
    eligible = range(4)
    current_bid = ""
    winning_player = None
    while len(eligible) > 1:
        for i in eligible[:]:
            if len(eligible) == 1:
                break
            p = game.players[i]

            bid_result = BID_INVALID
            while bid_result not in [BID_VALID, BID_PASS]:
                print_to_player("B%s" % current_bid, p.sock_file)
                # Read bid
                bid = get_client_input_timeout(game, p, timeout=60)
                if not game.running:
                    return
                bid_result = valid_bid(current_bid, bid)
            if bid_result == BID_PASS:
                send_message_to_players(game, "%s passes" % p.name,
                        skip_player=i)
                eligible.remove(i)
            else:
                current_bid = bid
                winning_player = i
                send_message_to_players(game, "%s bids %s" % (p.name, bid),
                        skip_player=i)

    # Inform all players of trumps
    send_message_to_players(game, current_bid, 'T')

    # Store winning bid and player
    game.bid = current_bid
    game.trumps = current_bid[SUIT]
    game.lead_player = winning_player
    game.bid_team = winning_player % 2


def play_trick(game):
    current = game.lead_player
    suit = ""
    winning_card = ""
    winning_player = None
    for i in range(4):
        pid = current % 4
        p = game.players[pid]

        valid = False
        while not valid:
            if i == 0:
                # Send lead message
                print_to_player('L', p.sock_file)
            else:
                # Send play message
                print_to_player('P%s' % suit, p.sock_file)

            play = get_client_input_timeout(game, p, timeout=60)
            print("play", p.name, i, "'%s'" % play)
            if not game.running:
                print("play:", play)
                return -1

            valid = valid_play(suit, play, p.hand)
            if not valid:
                # Invalid play, so ask for another play
                continue

            # Announce the play to other players
            play_message = "%s plays %s" % (p.name, play)
            send_message_to_players(game, play_message, skip_player=pid)
            # Accept the play
            print_to_player("A", p.sock_file)
            # Remove card from player's hand
            p.hand.remove(play)

            if i == 0:
                # Store lead suit
                suit = play[SUIT]
            if higher_card(play, winning_card, suit, game.trumps):
                winning_card = play
                winning_player = pid
            current += 1

    # Inform players the trick is finished.
    send_message_to_players(game,
            "Trick won by %s" % game.players[winning_player].name)

    # Update the winning player to be the new lead
    game.lead_player = winning_player

    # Return winning team
    return winning_player % 2


def play_hand(game):
    # Deal hand
    deal_hand(game, 0)
    # Get bids and inform everyone of trumps
    get_bids(game)
    if not game.running:
        return

    tricks_won = [0, 0]

    # Play hand
    for i in range(13):
        winner = play_trick(game)
        if not game.running:
            return
        tricks_won[winner] += 1

    # Add scores
    multiplier = 1
    if tricks_won[game.bid_team] < int(game.bid[RANK]):
        multiplier = -1
    game.scores[game.bid_team] += multiplier * bid_points(game.bid)

    # Send scores
    scores_message = "Team 1=%d, Team 2=%d" % (game.scores[0], game.scores[1])
    send_message_to_players(game, scores_message)


def bid_points(bid):
    num = int(bid[RANK])
    suit = bid[SUIT]
    return 20 + ((num - 4) % 6) * 50 + (SUITS[suit] - 1) * 10


def send_player_names(game):
    t1 = "Team1: %s, %s" % (game.players[0].name, game.players[2].name)
    send_message_to_players(game, t1)
    t2 = "Team2: %s, %s" % (game.players[1].name, game.players[3].name)
    send_message_to_players(game, t2)


def play_game(game):
    send_player_names(game)

    while game.running:
        play_hand(game)
        if not game.running:
            break

        # Check for winner
        if (game.scores[0] > 499 or game.scores[1] < -499 or
                game.scores[1] > 499 or game.scores[0] < -499):
            # A team has won
            break

        # Change to the next deck
        game.deck = (game.deck + 1) % len(game.server.decks)

    # Finish game
    end_game(game)


def accept_connection(server, client):
    p = Player()
    p.socket = client
    p.sock_file = p.socket.makefile(bufsize=0)

    # Send greeting
    print_to_player("M%s" % server.greeting, p.sock_file)

    # Get player name
    p.name = get_client_input_timeout(None, p)
    if not p.name:
        print_to_player("MInvalid player name.", p.sock_file)
        close_player(p)
        return

    # Get game name
    game = get_client_input_timeout(None, p)
    if not game:
        print_to_player("MInvalid game name.", p.sock_file)
        close_player(p)
        return

    # Add player to pending game
    players = server.pending.setdefault(game, [])
    if game not in server.pending_games:
        server.pending_games.append(game)
    players.append(p)
    print("Connection: Player: '%s', Game: '%s'" % (p.name, game))

    # Check if we need to start the game
    if len(players) == 4:
        g = Game()
        g.name = game
        g.server = server
        g.players = sorted(players, key=lambda x: x.name.lower())
        # Add game to list of running games
        server.games.append(g)
        # Remove from pending
        del server.pending[game]
        server.pending_games.remove(game)

        # Start thread for game
        print("Starting game: '%s'" % game)
        gt = GameThread(g)
        server.threads.append(gt)
        gt.start()


def start_game(server):
    print("started game")
    while True:
        # Accept connection
        try:
            client, address = server.sock.accept()
        except socket.error as e:
            if e.errno == errno.EMFILE:
                # Clean up oldest pending game
                print("Removing pending game due to hitting file limit")
                name = server.pending_games.pop()
                game = server.pending[name]
                for p in game:
                    close_player(p)
                del server.pending[name]
                continue

        print("[%s] accepted connection" % time.ctime(), address)
        accept_connection(server, client)

        for t in server.threads:
            t.join(0)
            if not t.is_alive():
                server.threads.remove(t)


def main():
    signal.signal(signal.SIGINT, signal_handler)

    if len(sys.argv) != 4:
        print("Usage: serv499 port greeting deck", file=sys.stderr)
        sys.exit(1)

    port = int(sys.argv[1])
    if port < 1 or port > 65535:
        print("Invalid Port", file=sys.stderr)
        sys.exit(4)

    server = Server()
    server.sock = create_server(port)
    server.greeting = sys.argv[2]

    try:
        server.deck_file = open(sys.argv[3], "r")
    except IOError:
        print("Unable to read deck", file=sys.stderr)
        sys.exit(6)

    read_decks(server)

    start_game(server)

    sys.exit(0)


if __name__ == '__main__':
    main()
