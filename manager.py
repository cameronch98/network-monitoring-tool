import json
import pickle
import socket
import threading
import time

from prompts import *


class Manager:
    def __init__(self):

        # Monitor service configurations
        self._configs: dict = {}
        self.read_config()

        # Threading
        self._clients: dict = {}
        self._lock: threading.Lock = threading.Lock()
        self._event: threading.Event = threading.Event()

    def start_manager(self):
        """Main command center"""
        try:
            print("What would you like to do?")
            print("1. Create new config")
            print("2. Load a monitor_service service")
            print("3. Load all monitor_service services")
            print("4. Exit")

            command = input("\nEnter command number: ")
            if command == "1":
                pass

            elif command == "2":
                self.load_monitor()

            elif command == "3":
                self.load_all_monitors()

            elif command == "4":
                print("Exiting ...")
                exit()

        except KeyboardInterrupt:
            print("Keyboard interrupt detected ... shutting down clients")
            self._event.set()
            for client in self._clients.values():
                client.join()

    def load_monitor(self):
        """Starts control client for a chosen monitor_service service"""
        # Get user's choice
        monitor_id, host, port, services = monitor_choice_prompt(
            "Which monitor_service would you like to load? [TAB]: ", self._configs
        )

        # Start control client
        self._clients[monitor_id] = ControlClient(
            monitor_id, host, port, services, self._event, self._lock
        )
        self._clients[monitor_id].start()
        print(f"Monitor service at {host}:{port} has been loaded!")

    def load_all_monitors(self):
        """Starts control client for all monitor_service services"""
        # Loop through and start up clients
        for monitor_id, config in self._configs.items():
            host, port, services = config["IP"], config["Port"], config["Services"]
            self._clients[monitor_id] = ControlClient(
                monitor_id, host, port, services, self._event, self._lock
            )
            self._clients[monitor_id].start()
        time.sleep(5)
        print("All available monitor services loaded!")
        print("\nPress Ctrl+C to Stop")

    def read_config(self):
        """Updates self._configs with current config file"""
        # Get configs from json file
        with open("configs.json", "r") as file:
            self._configs = json.loads(file.read())

    def write_config(self):
        """Updates config file to reflect current state of self._configs"""
        # Persist server dict to JSON file
        with open("configs.json", "w") as file:
            file.write(json.dumps(self._configs))

    def get_config(self):
        """Returns self._configs"""
        return self._configs


class ControlClient(threading.Thread):
    def __init__(
        self,
        monitor_id: str,
        monitor_host: str,
        monitor_port: int,
        services: dict,
        event: threading.Event,
        lock: threading.Lock,
    ):
        super().__init__()

        # Set params
        self._monitor_id: str = monitor_id
        self._monitor_host: str = monitor_host
        self._monitor_port: int = monitor_port
        self._services: dict = services

        # Socket
        self._socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Threading
        self._lock: threading.Lock = lock
        self._event: threading.Event = event

    def run(self):
        """Start up socket and handle client behavior"""
        while not self._event.is_set():
            try:
                # Connect to monitor_service service
                self.connect()
                time.sleep(2)

                # Send id to monitor_service service to set
                self.set_id()
                time.sleep(2)

                # Distribute tasks to monitor_service service
                self.distribute_tasks()
                time.sleep(2)

                # Monitor status until keyboard interrupt
                self.monitor_status()

            except socket.error:
                print(
                    f"Error with connection to monitor_service service at {self._monitor_host}:{self._monitor_port} ... trying to reconnect!"
                )
                self._socket.close()
                time.sleep(10)

    def connect(self):
        """Connect to monitor_service service"""

        # Create new socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Enable keepalive behavior to receive messages for detecting dead connections
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        while True:
            self._lock.acquire()
            try:
                print(
                    f"Attempting to connect to monitor_service service at {self._monitor_host}:{self._monitor_port} ..."
                )
                self._socket.connect((self._monitor_host, self._monitor_port))
                print(
                    f"Successfully connected to monitor_service service at {self._monitor_host}:{self._monitor_port}\n"
                )
                self._lock.release()
                break

            except socket.error:
                print(
                    f"Connection to monitor_service service at {self._monitor_host}:{self._monitor_port} failed! Trying again!\n"
                )
                self._lock.release()
                time.sleep(15)

    def set_id(self):
        """Send monitor_service service an ID"""
        # Assign ID to monitor_service
        with self._lock:
            try:
                response = self.send_command("SET_ID")
                if response == "awaiting ID ...":
                    print(
                        f"Sending ID {self._monitor_id} to monitor_service service at {self._monitor_host}:{self._monitor_port}\n"
                    )
                    self._socket.send(self._monitor_id.encode("utf-8"))
            except socket.error as e:
                print(f"Socket error: {e}")

    def close(self):
        """Close connection with given monitor_service service"""
        # Close socket connection with given id
        self._socket.close()

    def send_command(self, command):
        """Send command over given monitor_service service"""
        try:
            # Send command
            print(
                f"Sending {command} command to monitor_service service {self._monitor_id} at {self._monitor_host}:{self._monitor_port}"
            )
            self._socket.sendall(command.encode())

            # Await acknowledgment
            response = self._socket.recv(1024).decode("utf-8")
            print(
                f"Command to monitor_service {self._monitor_id} acknowledged: {response}"
            )
            return response
        except socket.error as e:
            print(f"Socket error: {e}")

    def distribute_tasks(self):
        """Distribute defined tasks to monitors"""
        with self._lock:
            try:
                # Send the start command to prepare monitor_service for config
                response = self.send_command("START")

                # If response is awaiting tasks, send config
                if response == "awaiting tasks ...":

                    # Create task config data and send
                    task_configs = pickle.dumps(self._services)
                    self._socket.sendall(task_configs)

                    # Await confirmation of tasks
                    response = self._socket.recv(1024).decode("utf-8")
                    print(
                        f"Task start up at monitor_service {self._monitor_id} acknowledged: {response}\n"
                    )

            except socket.error as e:
                print(f"Socket error: {e}")

    def monitor_status(self):
        """Await results and status updates for given monitor_service service"""
        # Await responses until error or condition
        try:
            while True:
                response = self._socket.recv(1024).decode("utf-8")
                if response:
                    with self._lock:
                        print(response)
                else:
                    break

        except socket.error:
            print(
                f"Connection to monitor_service ${self._monitor_host, self._monitor_port} lost!"
            )
            self._socket.close()


if __name__ == "__main__":
    manager = Manager()
    manager.start_manager()
