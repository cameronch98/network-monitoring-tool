import json
import pickle
import socket
import threading
import time

from prompts import *


class Manager:
    def __init__(self):

        # Monitor service configurations
        self._configs = {}
        self.read_config()

        # Clients
        self._clients = {}

    def start(self):
        """Main command center"""
        while True:
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
                break

    def load_monitor(self):
        """Starts control client for a chosen monitor_service service"""
        # Get user's choice
        monitor_id, host, port, services = monitor_choice_prompt(
            "Which monitor_service would you like to load? [TAB]: ", self._configs
        )

        # Start control client
        self._clients[monitor_id] = ControlClient(monitor_id, host, port, services)
        self._clients[monitor_id].start()
        print(f"Monitor service at {host}:{port} has been loaded!")

        # Start up command loop
        time.sleep(3)
        self.command_loop()

    def load_all_monitors(self):
        """Starts control client for all monitor_service services"""
        # Loop through and start up clients
        for monitor_id, config in self._configs:
            host, port, services = config["IP"], config["Port"], config["Services"]
            self._clients[monitor_id] = ControlClient(monitor_id, host, port, services)
            self._clients[monitor_id].start()
        print("All monitor_service services loaded!")

        # Start up command loop
        time.sleep(3)
        self.command_loop()

    def command_loop(self):
        """Command loop to run while results are being gathered"""
        while True:

            # Ask user if they want to quit monitoring or send server command
            user_input = results_prompt("Enter command [TAB]: ")
            if user_input == "send-server-command":

                # Get the command and the monitor_service service to send it to
                server_command = monitor_command_prompt("Enter server command [TAB]: ")
                monitor_id = monitor_choice_prompt(
                    "Which monitor_service would you like to send the command to? [TAB]: ",
                    self._configs,
                )[0]

                # Send the command
                self._clients[monitor_id].send_command(server_command.upper())

            # Check for quit command
            elif user_input == "quit":

                # Send command for monitors to shut all tasks down
                for client in self._clients:
                    client.send_command("QUIT")

                # Sleep and break
                time.sleep(3)
                break

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


class ControlClient(Manager, threading.Thread):
    def __init__(self, monitor_id: str, host: str, port: int, services: dict):
        super().__init__()

        # Set params
        self._monitor_id: str = monitor_id
        self._host: str = host
        self._port: int = port
        self._services: dict = services

        # Socket
        self._socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        """Start up socket and handle client behavior"""
        while True:
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
                    f"Error with connection to monitor_service service at {self._host}:{self._port} ... trying to reconnect!"
                )
                self._socket.close()
                time.sleep(3)
                continue

            except KeyboardInterrupt:
                print("\n\nClosing sockets and shutting down management service!\n")
                self._socket.close()
                break

    def connect(self):
        """Connect to monitor_service service"""

        # Create new socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Enable keepalive behavior to receive messages for detecting dead connections
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        while True:
            try:
                print(
                    f"Attempting to connect to monitor_service service at {self._host}:{self._port} ..."
                )
                self._socket.connect((self._host, self._port))
                print(
                    f"Successfully connected to monitor_service service at {self._host}:{self._port}\n"
                )

                # Break when connection succeeds
                break

            except socket.error:
                print(
                    f"Connection to monitor_service service at {self._host}:{self._port} failed! Trying again!\n"
                )
                time.sleep(5)

    def set_id(self):
        """Send monitor_service service an ID"""
        # Assign ID to monitor_service
        response = self.send_command("SET_ID")
        if response == "awaiting ID ...":
            print(
                f"Sending ID {self._monitor_id} to monitor_service service at {self._host}:{self._port}\n"
            )
            self._socket.send(self._monitor_id.encode("utf-8"))

    def close(self):
        """Close connection with given monitor_service service"""
        # Close socket connection with given id
        self._socket.close()

    def send_command(self, command):
        """Send command over given monitor_service service"""
        # Send command
        print(
            f"Sending {command} command to monitor_service service {self._monitor_id} at {self._host}:{self._port}"
        )
        self._socket.sendall(command.encode())

        # Await acknowledgment
        response = self._socket.recv(1024).decode("utf-8")
        print(f"Command to monitor_service {self._monitor_id} acknowledged: {response}")
        return response

    def distribute_tasks(self):
        """Distribute defined tasks to monitors"""
        # Send the start command to prepare monitor_service for config
        response = self.send_command("START")

        # If response is awaiting tasks, send config
        if response == "awaiting tasks ...":

            # Create task config data and send
            task_configs = pickle.dumps(self._configs[self._monitor_id]["Services"])
            self._socket.sendall(task_configs)

            # Await confirmation of tasks
            response = self._socket.recv(1024).decode("utf-8")
            print(
                f"Task start up at monitor_service {self._monitor_id} acknowledged: {response}\n"
            )

    def monitor_status(self):
        """Await results and status updates for given monitor_service service"""
        print("PRESS CTRL+C TO STOP")
        # Await responses until error or condition
        while True:
            try:
                response = self._socket.recv(1024).decode("utf-8")
                if response:
                    print(response)
                else:
                    self._socket.close()
                    break

            except KeyboardInterrupt:
                response = self.send_command("QUIT")
                print(response)
                print("Exiting status monitor_service ...\n")
                time.sleep(2)
                break

            except socket.error:
                print(
                    f"Connection to monitor_service ${self._configs[self._monitor_id]['IP'], self._configs[self._monitor_id]['Port']} lost!"
                )
                self._socket.close()
                break


if __name__ == "__main__":
    manager = Manager()
    manager.start()
