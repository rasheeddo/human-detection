#!/usr/bin/env python3
import sys
if sys.version_info[0] < 3:
    raise Exception("Must be using Python 3")

import os
import struct
import socket
import numpy as np 

# create an socket object
s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

# the address of this thread
RecAddress = ("127.0.0.1", 12345)
  
# only the receiver need to bind
s.bind(RecAddress)

SENDER = "127.0.0.1"
SEN_PORT = 11223

while True:
	data, addr = s.recvfrom(1024)
	print(data)
	print(addr)

	#s.sendto(b"Yoo!",(SENDER,SEN_PORT))
	#time.sleep(1)