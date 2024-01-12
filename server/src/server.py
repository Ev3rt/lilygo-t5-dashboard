#!/usr/bin/env python3

from datetime import datetime
import requests
import signal
import socket
import threading
import time


IP = "0.0.0.0"
PORT = 55556
FETCH_INTERVAL = 15 * 60  # every 15 minutes

weather_data = {
    "code": {
        "now": "unknown",
        "1h": "unknown",
        "2h": "unknown",
        "4h": "unknown",
        "8h": "unknown",
        "1d": "unknown",
        "2d": "unknown",
        "3d": "unknown",
        "4d": "unknown",
        "5d": "unknown",
    },
    "temp": {
        "now": -9999,
        "1h": -9999,
        "2h": -9999,
        "4h": -9999,
        "8h": -9999,
        "1d": -9999,
        "2d": -9999,
        "3d": -9999,
        "4d": -9999,
        "5d": -9999,
    },
}

print_lock = threading.Lock()
stop = threading.Event()


def weather_lookup(id: int, sun: bool) -> str:
    match id:
        case 0:
            return "sun" if sun else "moon"
        case 1:
            return "sun_cloud" if sun else "moon_cloud"
        case 2 | 3:
            return "cloud"
        case 45 | 48:
            return "fog"
        case 51 | 53 | 55:
            return "drizzle"
        case 56 | 57:
            return "hail"
        case 61 | 63 | 65 | 80 | 81 | 82:
            return "rain"
        case 66 | 67:
            return "hail"
        case 71 | 73 | 75 | 77 | 85 | 86:
            return "snow"
        case 95 | 96 | 99:
            return "thunder"
        case _:
            return "unknown"


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
        print_threaded(f"Started server on {IP}:{PORT}")

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
                send_thread = threading.Thread(target=send_data_threaded, args=(connection, address))
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
        # Retrieved data starts at today 00:00, so we can use the current hour as a offset to get the actual data
        current_time = datetime.now()
        weather_offset = current_time.hour + current_time.minute // 30

        # Retrieve weather data from Open-Meteo
        # TODO: configurable
        request = requests.get(
            "https://api.open-meteo.com/v1/forecast?latitude=51.99&longitude=5.09&timezone=auto&hourly=temperature_2m,weathercode&daily=temperature_2m_max,temperature_2m_min,weathercode,sunrise,sunset"
        )

        # Check if the request was successful
        if request.status_code == 200:
            weather_request = request.json()
            # Assume the data is complete if status code 200 was returned
            try:
                # Parse the received data and populate the buffer
                sunrise = datetime.strptime(weather_request["daily"]["sunrise"][0], "%Y-%m-%dT%H:%M")
                sunset = datetime.strptime(weather_request["daily"]["sunrise"][0], "%Y-%m-%dT%H:%M")
                sun = current_time > sunrise and current_time < sunset

                # Current weather
                weather_data["temp"]["now"] = str(round(weather_request["hourly"]["temperature_2m"][weather_offset]))
                weather_data["code"]["now"] = weather_lookup(weather_request["hourly"]["weathercode"][weather_offset], sun)

                # Hourly forecast
                for i in [1, 2, 4, 8]:
                    weather_data["temp"][f"{i}h"] = str(round(weather_request["hourly"]["temperature_2m"][weather_offset + i]))
                    weather_data["code"][f"{i}h"] = weather_lookup(
                        weather_request["hourly"]["weathercode"][weather_offset + i], sun
                    )

                # Daily forecast
                for i in [1, 2, 3, 4, 5]:
                    weather_data["temp"][f"{i}d"] = (
                        str(round(weather_request["daily"]["temperature_2m_min"][i]))
                        + "-"
                        + str(round(weather_request["daily"]["temperature_2m_max"][i]))
                    )
                    weather_data["code"][f"{i}d"] = weather_lookup(weather_request["daily"]["weathercode"][i], True)

                print_threaded(
                    "Retrieved weather data:"
                    f"\n  now | Temperature: {weather_data['temp']['now']} | Weather: {weather_data['code']['now']}"
                    f"\n   1h | Temperature: {weather_data['temp']['1h']} | Weather: {weather_data['code']['1h']}"
                    f"\n   2h | Temperature: {weather_data['temp']['2h']} | Weather: {weather_data['code']['2h']}"
                    f"\n   4h | Temperature: {weather_data['temp']['4h']} | Weather: {weather_data['code']['4h']}"
                    f"\n   8h | Temperature: {weather_data['temp']['8h']} | Weather: {weather_data['code']['8h']}"
                    f"\n   1d | Temperature: {weather_data['temp']['1d']} | Weather: {weather_data['code']['1d']}"
                    f"\n   2d | Temperature: {weather_data['temp']['2d']} | Weather: {weather_data['code']['2d']}"
                    f"\n   3d | Temperature: {weather_data['temp']['3d']} | Weather: {weather_data['code']['3d']}"
                    f"\n   4d | Temperature: {weather_data['temp']['4d']} | Weather: {weather_data['code']['4d']}"
                    f"\n   5d | Temperature: {weather_data['temp']['5d']} | Weather: {weather_data['code']['5d']}"
                )

            except Exception as ex:
                print_threaded("An exception occured while parsing weather data:\n" + ex)

        # Sleep until the next interval
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

    # Send weather data
    msg_weather = generate_message_weather()
    send_message(connection, msg_weather)

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
    # Send the message to the dashboard using the TCP connection
    print_threaded(f"Sending message: '{message}'")
    connection.sendall(message.encode("ascii"))


def generate_message_time() -> str:
    """
    Compose a message containing the current date and time.

    Returns:
        str: The composed message
    """
    # The dashboard only updates once a minute so we don't need the seconds
    return f"TIME|{datetime.now().strftime('%d-%m-%Y %H:%M')}]"


def generate_message_weather() -> str:
    """
    Compose a message containing the weather forecast data.

    Returns:
        str: The composed message
    """
    # The dashboard only updates once a minute so we don't need the seconds
    message = "WEATHER"
    for i in ["now", "1h", '2h', '4h', '8h', '1d', '2d', '3d', '4d', '5d']:
        message += f"|{weather_data['temp'][i]}|{weather_data['code'][i]}"
    return message + "]"


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
