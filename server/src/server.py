#!/usr/bin/env python3

from datetime import datetime
import signal
import socket
import threading
import time


IP = "0.0.0.0"
PORT = 55555
FETCH_INTERVAL = 15 * 60  # every 15 minutes

print_lock = threading.Lock()
stop = threading.Event()


def main() -> None:
    """
    Entry point of the application.
    """
    # Setup signal hander for gracefully terminating application
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start a thread for fetching weather and uptime data
    fetch_thread = threading.Thread(target=fetch_data_threaded)
    fetch_thread.start()

    # Start listening for connections to the configured IP/port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sck:
        sck.bind((IP, PORT))

        # Stop accept() periodically to allow terminating the thread if a signal has been received
        sck.settimeout(1)

        sck.listen()
        print(f"Started server on {IP}:{PORT}")

        # Keep listening for connections until a signal is received
        while not stop.is_set():
            try:
                # Wait for an incoming connection
                connection, address = sck.accept()
            except socket.timeout:
                # Timeout has been triggered, check the loop condition again
                pass
            except:
                # Raise any other exception
                raise
            else:
                # A connection has been established. Send data to the client from a separate thread
                send_thread = threading.Thread(
                    target=send_data_threaded, args=(connection, address)
                )
                send_thread.start()


def signal_handler(signal_: int, _) -> None:
    """
    Stop the program when a signal is received.

    Parameters:
        signal_ (int): ID of the signal received
    """
    print_threaded(f"{signal.Signals(signal_).name} received, stopping server...")
    # Trigger the stop event
    stop.set()


def print_threaded(message: str) -> None:
    """
    Print a message to the console in a thread-safe way.

    Parameters:
        message (str): The message to print
    """
    # Lock the console
    print_lock.acquire()
    print(message)
    print_lock.release()


def fetch_data_threaded():
    """
    TODO
    """
    while not stop.is_set():
        # TODO fetch data
        stop.wait(FETCH_INTERVAL)


def send_data_threaded(connection, address: str) -> None:
    """
    Send data to a connected dashboard.

    Parameters:
        connection (socket): Connection to the client
        address (str): IP of the client
    """
    # Log from which address the client connected
    print_threaded(f"Client '{address}' connected")

    # Send current date and time
    msg_time = generate_message_time()
    send_message(connection, msg_time)

    # Wait a little before closing the connection, to facilitate re-sending lost packages
    time.sleep(1)

    # Close the connection after sending all data
    print_threaded(f"Closing connection to client '{address}'")
    connection.close()


def send_message(connection: socket, message: str) -> None:
    """
    Send a message to a connected client.

    Parameters:
        connection (socket): Connection to the client
        message (str): Message to send
    """
    # Determine message length
    length = format(len(message), "04d")

    # Send the message length so the dashboard knows how many bytes to read
    print_threaded(f"Sending message length: '{length}'")
    connection.sendall(length.encode("ascii"))

    # Send the message itself
    print_threaded(f"Sending message: '{message}'")
    connection.sendall(message.encode("ascii"))


def generate_message_time() -> str:
    """
    Compose a message containing the current date and time.

    Returns:
        str: The composed message
    """
    # The dashboard only updates once a minute so we don't need the seconds
    time = datetime.now().strftime("%d-%m-%Y %H:%M")

    # Add the message type as a prefix
    return f"TIME|{time}"


def generate_message_weather() -> str:
    """
    Compose a message containing the weather forecast data.

    Returns:
        str: The composed message
    """
    # TODO
    pass


def generate_message_status() -> str:
    """
    Compose a message containing the service status data.

    Returns:
        str: The composed message
    """
    # TODO
    pass


if __name__ == "__main__":
    main()
