#!/usr/bin/env python3

import socket

IP = "127.0.0.1"
PORT = 55556

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sck:
    # Open a connection to the specified IP/port
    sck.connect((IP, PORT))

    while True:
        # Receive the size of the message first. The size is always padded to 4 bytes.
        data = sck.recv(4).decode("ascii")
        match len(data):
            case 4:
                # Parse the size of the message
                size = int(data)
                print(f"Going to read {size} bytes")
                # Read the specified number of bytes
                data = sck.recv(size).decode("ascii")
                print(f"Received message {data}")
            case 0:
                # The server closed the connection
                print("Connection closed by server")
                exit(0)
            case _:
                # Received a unknown stream of data
                print(f"Invalid data received: {data}")
                exit(1)
