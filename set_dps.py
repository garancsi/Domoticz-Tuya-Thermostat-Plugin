#!/usr/bin/python3

########################################################################################
# 	Domoticz Tuya Smart Plug Python Plugin                                             #
#                                                                                      #
# 	MIT License                                                                        #
#                                                                                      #
#	Copyright (c) 2018 iasmanis                                                            #
#                                                                                      #
#	Permission is hereby granted, free of charge, to any person obtaining a copy       #
#	of this software and associated documentation files (the "Software"), to deal      #
#	in the Software without restriction, including without limitation the rights       #
#	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell          #
#	copies of the Software, and to permit persons to whom the Software is              #
#	furnished to do so, subject to the following conditions:                           #
#                                                                                      #
#	The above copyright notice and this permission notice shall be included in all     #
#	copies or substantial portions of the Software.                                    #
#                                                                                      #
#	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR         #
#	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,           #
#	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE        #
#	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER             #
#	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,      #
#	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE      #
#	SOFTWARE.                                                                          #
#                                                                                      #
########################################################################################

import sys
import pytuya
import socket  # needed for socket.timeout exception
import logging

logging.basicConfig(level=logging.DEBUG)

if(len(sys.argv) != 8):
    print("usage: " + sys.argv[0] +
          " <IP> <DevID> <Local key> <version> <DPS key> <DPS value> <DPS type>")
    print("    <DPS type>: " +
          "\n       bool - a boolean value" +
          "\n       number - a numerical value value" +
          "\n       string - a string value value")
    exit(1)

ip = sys.argv[1]
devid = sys.argv[2]
localkey = sys.argv[3]
dps_key = sys.argv[5]
dps_value = sys.argv[6]
dps_type = sys.argv[7]

device = pytuya.OutletDevice(devid, ip, localkey)
device.version = sys.argv[4]

try:

    formatted_dps_value = str(dps_value)
    if (dps_type == "bool"):
        formatted_dps_value = (dps_value.lower() == "true")
    if (dps_type == "number"):
        formatted_dps_value = int(dps_value)

    payload = device.generate_payload(
        'set', {str(dps_key): formatted_dps_value})
    device._send_receive(payload)

except (ConnectionResetError, socket.timeout, OSError) as e:
    print("A problem occur please retry...")
    exit(1)
