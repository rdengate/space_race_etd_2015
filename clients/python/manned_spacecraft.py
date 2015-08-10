#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# manned_spacecraft.py
# Game client for 2015 ETD Winter retreat
# https://github.com/lmccalman/spacerace
# 
# Created by Louis Tiao on 28/07/2015.
# 

import matplotlib.pyplot as plt

import itertools
import argparse
import logging
import pprint
import string
import random
import json
import zmq

DEFAULTS = {
    'hostname': 'localhost',  #'192.168.1.110', #'localhost',
    'state_port': 5556,
    'control_port': 5557,
    'lobby_port': 5558,
}

# Setup basic logging
logger = logging.getLogger(__name__)

logging.basicConfig(
    level = logging.INFO,
    datefmt = '%I:%M:%S %p',
    format = '%(asctime)s [%(levelname)s]: %(message)s'
)

# Helper functions
make_address = 'tcp://{}:{}'.format
make_random_name = lambda length: ''.join(random.choice(string.ascii_letters) \
    for _ in range(length))

class Client:

    def __init__(self, server, state_port, control_port, lobby_port, ship_name, team_name):

        # ZeroMQ context
        self.context = zmq.Context()
        self.context.linger = 0
        
        self.pressed = set()

        self.ship_name = ship_name        
        self.team_name = team_name

        self.control_address = make_address(server, control_port)
        self.state_address = make_address(server, state_port)
        self.lobby_address = make_address(server, lobby_port)

        # Lobby socket
        self.lobby_sock = self.context.socket(zmq.REQ)

        logger.info('Connecting to lobby lobby at [{0}]...'.format(self.lobby_address)) 
        self.lobby_sock.connect(self.lobby_address)

        logger.info('Sending ship name [{0}]'.format(self.ship_name))
        greeting_message = json.dumps({"name":self.ship_name, "team":self.team_name})
        self.lobby_sock.send_string(greeting_message)

        logger.info('Awaiting confirmation from lobby...')
        lobby_response_data = self.lobby_sock.recv_json()

        logging.debug(pprint.pformat(lobby_response_data))

        self.secret_key = lobby_response_data['secret']
        self.game_name = lobby_response_data['game']
        self.game_map  = lobby_response_data['map']

        logging.info('Ship [{}] was registered to participate in game [{}]'
                     ' (secret [{}])'.format(self.ship_name, self.game_name, \
                        self.secret_key))

        # Control socket
        self.control_sock = self.context.socket(zmq.PUSH)

        logger.info('Connecting to control socket at [{0}]...'.format(self.control_address)) 
        self.control_sock.connect(self.control_address)

        # State socket
        self.state_sock = self.context.socket(zmq.SUB)
        self.state_sock.setsockopt_string(zmq.SUBSCRIBE, self.game_name)

        logger.info('Connecting to state socket at [{0}]...'.format(self.state_address)) 
        self.state_sock.connect(self.state_address)

    def recv_state(self):
        logger.info('Awaiting message from state socket...')
        msg_filter_b, state_b = self.state_sock.recv_multipart()
        state = json.loads(state_b.decode())
        return state

    def send_control(self, linear, rotational):
        control_lst = [self.secret_key, linear, rotational]
        control_str = ','.join(map(str, control_lst))
        logger.info('Sending control string "{}"'.format(control_str))
        self.control_sock.send_string(control_str)

    def update_control(self):
        linear = int('up' in self.pressed)
        rotation = 0
        rotation += int('left' in self.pressed)
        rotation -= int('right' in self.pressed)
        self.send_control(linear, rotation)

    def press(self, event):
        self.pressed.add(event.key)
        self.update_control()

    def release(self, event):
        self.pressed.discard(event.key)
        self.update_control()



if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Spacerace: Manned Spacecraft'
    )

    parser.add_argument('--hostname', type=str, help='Server hostname', default=DEFAULTS['hostname'])
    parser.add_argument('--state_port', type=int, help='State port', default=DEFAULTS['state_port'])
    parser.add_argument('--control_port', type=int, help='Control port', default=DEFAULTS['control_port'])
    parser.add_argument('--lobby_port', type=int, help='Lobby port', default=DEFAULTS['lobby_port'])

    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('--ship_name', '-n', type=str,
        default=make_random_name(10), help='Ship Name')
    parser.add_argument('--team_name', '-t', type=str,
        default=make_random_name(10), help='Ship Name')

    args = parser.parse_args()

    logger.debug(args)

    client = Client(args.hostname, args.state_port, args.control_port, args.lobby_port, args.ship_name, args.team_name)

    fig, ax = plt.subplots()

    fig.canvas.mpl_connect('key_press_event', client.press)
    fig.canvas.mpl_connect('key_release_event', client.release)

    plt.show()

