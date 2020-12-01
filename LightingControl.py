from osc4py3.as_eventloop import *
from osc4py3 import oscbuildparse
import time
import socket

# CONSTANTS
channels_per_strip = 141
channels_per_univ = 512
strips_per_univ = 3
translate_index = {1: 2, 2: 6, 3: 7, 4: 5, 5: 4, 6: 3, 7: 0, 8: 1}


# VARS
num_universes = 3
output = [0 for _ in range(num_universes * 512)]

def receive_message(socket):
    msg = socket.recv(1024)
    msg = oscbuildparse.decode_packet(msg)
    return msg

# args may need to be a list, send on port 7000
def send(socket, addr, args):
    # use osc4py3 to create message
    message = oscbuildparse.OSCMessage(addr, None, args)
    message = oscbuildparse.encode_packet(message)
    # use socket to send message
    socket.send(message)

"""
Fills the strip at strip_index with rgb
"""
def set_strip(strip_index, rgb):
    strip_index = translate_index[strip_index]
    universe = int(strip_index / strips_per_univ)

    output_index = (strip_index % strips_per_univ) * channels_per_strip + universe * channels_per_univ

    color = [rgb[i % 3] for i in range(47*3)]
    output[output_index:output_index + channels_per_strip] = color

def set_strips(strips, rgbs):
    for i in range(len(strips)):
        strip = strips[i]
        rgb = rgbs[i]
        set_strip(strip, rgb)

if __name__ == "__main__":
    # create send socket on port 7000
    # max : udpreceive 7000
    send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_socket.connect(("localhost", 7000))

    # create receive socket on port 7001
    # max: udpsend localhost 7001
    recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_socket.bind(("localhost", 7001))

    end = False
    while not end:
        msg = receive_message(recv_socket)
        addr = msg.addrpattern
        if addr == "/end":
            end = True
        elif addr == "/set":
            args = msg.arguments
            strip = args[0]
            if strip <= 0 or strip >= 9:
                continue
            rgb = [args[1], args[2], args[3]]
            set_strip(strip, rgb)
            send(send_socket, "/channels", output)
        elif addr == "/amps":
            args = msg.arguments
            rgb = [args[0], args[1], args[2]]
            amps = [args[3], args[4], args[5], args[6]]

            strips = [1, 2, 3, 4, 5, 6, 7, 8]
            rgbs = []
            for a in amps:
                modified = [c * a for c in rgb]
                rgbs.append(modified)
                rgbs.append(modified)
            set_strips(strips, rgbs)
            send(send_socket, "/channels", output)
        elif addr == "/all":
            args = msg.arguments
            rgb = [args[0], args[1], args[2]]
            strips = [1, 2, 3, 4, 5, 6, 7, 8]
            rgbs = [rgb for _ in range(len(strips))]
            set_strips(strips, rgbs)
            send(send_socket, "/channels", output)
        else:
            continue

    # Properly close the system.
    send_socket.close()
    recv_socket.close()
