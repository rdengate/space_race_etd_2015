#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# dummy_client.py
# Game client for 2015 ETD Winter retreat
# https://github.com/lmccalman/spacerace
#
# Created by Louis Tiao on 28/07/2015.
#

import logging
import string
import random
import zmq
import csv
import os
import math

from client import Client
from argparse import ArgumentParser

DEFAULTS = {
    'hostname': '192.168.1.192',
    'state_port': 5556,
    'control_port': 5557,
    'lobby_port': 5558,
}

# Yes, this is terrible. TODO fix me.
MAPS_PATH = "C:\\Users\\Local-Admin\\Desktop\\space_race_etd_2015\\maps"

# Setup basic logging
logger = logging.getLogger(__name__)

logging.basicConfig(
    level = logging.DEBUG,
    datefmt = '%I:%M:%S %p',
    format = '%(asctime)s [%(levelname)s]: %(message)s'
)

# Helper functions
make_random_name = lambda length: ''.join(random.choice(string.ascii_letters) \
    for _ in range(length))
make_random_control = lambda: (random.choice([1,1,1,1,0]), random.choice([-1,-1,1,1,0,0,0,0,0,0,0]))

def make_context():
    context = zmq.Context()
    context.linger = 0
    return context


class Controller(object):
    def __init__(self, map_name):
        flow_x_fn = os.path.join(MAPS_PATH, "%s_flowx.csv\\%s_flowx.csv" % (map_name, map_name))
        flow_y_fn = os.path.join(MAPS_PATH, "%s_flowy.csv\\%s_flowy.csv" % (map_name, map_name))
        if not os.path.exists(flow_x_fn):
            logger.debug("File not found! %s" % flow_x_fn)
        if not os.path.exists(flow_y_fn):
            logger.debug("File not found! %s" % flow_y_fn)
        print flow_x_fn

        self.flow_x = self.getFlow(flow_x_fn)
        self.flow_y = self.getFlow(flow_y_fn)

    def getFlow(self, filename):
        self.csvfile = open(filename, "r")
        csv_reader = csv.reader(self.csvfile, delimiter=' ')
        return list(csv_reader)

    def getFlowX(self, x, y):
        return float(self.flow_x[int(x)][len(self.flow_x) - 1 - int(y)])

    def getFlowY(self, x, y):
        return float(self.flow_y[int(x)][len(self.flow_y) - 1 - int(y)])

    def getMyArray(self, data):
        for line in data["data"]:
          if line["id"]=="Enterprise":
            return line
        return None

def getDeltaTheta(currentTheta, xFlow, yFlow):
    deltaTheta = math.atan2(yFlow,xFlow) - currentTheta
    if (deltaTheta < -3.14):
      deltaTheta = deltaTheta + 2*3.14
    elif (deltaTheta > 3.14):
      deltaTheta = deltaTheta - 2*3.14

    return deltaTheta

def getNewPosition(theta, omega, threshold, xflow, yflow):
    deltaTheta = getDeltaTheta(theta, xflow, yflow)

    rotational = int((math.copysign(1,deltaTheta) + math.copysign(1,omega)) / 2)

    if (abs(deltaTheta) > abs(threshold)):
       return (0, rotational)
    else:
       return (1, rotational)


if __name__ == '__main__':

    parser = ArgumentParser(
        description='Spacerace: Dummy Spacecraft'
    )

    parser.add_argument('--version', action='version', version='%(prog)s 1.0')

    parser.add_argument('--hostname', type=str, help='Server hostname', default=DEFAULTS['hostname'])
    parser.add_argument('--state_port', type=int, help='State port', default=DEFAULTS['state_port'])
    parser.add_argument('--control_port', type=int, help='Control port', default=DEFAULTS['control_port'])
    parser.add_argument('--lobby_port', type=int, help='Lobby port', default=DEFAULTS['lobby_port'])

    parser.add_argument('--ship_name', '-s', type=str,
        default=make_random_name(10), help='Ship Name')
    parser.add_argument('--team_name', '-t', type=str,
        default=make_random_name(10), help='Team Name')

    args = parser.parse_args()

    with make_context() as context:
        client = Client(args.hostname, args.lobby_port, args.control_port, args.state_port, context)

        while True:
            response = client.lobby.register(args.ship_name, args.team_name)
            controller = Controller(response["map"])

            client.state.subscribe(response.game)

            for state_data in client.state.state_gen():
                myArray = controller.getMyArray(state_data)
                omega = myArray["omega"]
                theta = myArray["theta"]
                print("array %s" % myArray)
                x = myArray["x"]
                y = myArray["y"]
                flow_x = controller.getFlowX(x, y)
                flow_y = controller.getFlowY(x, y)

                threshold = 30.0/360*2*3.14
                client.control.send(response.secret, *getNewPosition(theta, omega, threshold, flow_x, flow_y))

        client.close()

