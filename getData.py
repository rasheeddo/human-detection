#!/usr/bin/env python3
import sys
if sys.version_info[0] < 3:
    raise Exception("Must be using Python 3")

import os
import struct
import socket
import numpy as np
import pickle
import time

s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

RecAddress = ("127.0.0.1", 12345)

s.bind(RecAddress)

while True:
	startTime = time.time()

	data, addr = s.recvfrom(1024)

	data = pickle.loads(data)
	print(data['nboxes'])
	print(data['distance'])

	period = time.time() - startTime
	print("period", period)

