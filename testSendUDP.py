#!/usr/bin/env python3
import sys
if sys.version_info[0] < 3:
    raise Exception("Must be using Python 3")
import os
import struct
import socket
import numpy as np 
import time

# the receiver address that we need to send to
RECEIVER = "127.0.0.1"
REC_PORT = 12345
# create socket object
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# make packet data
#udpPacket = struct.pack('HH',000,456)
udpPacket = b"HELLO"

# this is in case this thread gonna receive a data from receiver thread
SenderAddress = ("127.0.0.1",11223)
# need to bind if want to receive
s.bind(SenderAddress)

while True:
	# send data to receiver
	s.sendto(udpPacket,(RECEIVER, REC_PORT))

	#data, addr = s.recvfrom(1024)
	#print("data from receiver",data)
	#print("address of receiver",addr)
	time.sleep(1)