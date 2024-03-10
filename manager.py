import json
import os
import pickle
import shutil
import signal
import socket
import sys
import threading
import time
from typing import Any

from prompts import *

restart_flag = False


class Manager:
    def __init__(self):

        # Monitor service configurations
        self._configs: dict = {}
        self.read_config()

        # Threading
        self._clients: dict = {}
        self._lock: threading.Lock = threading.Lock()

    def start_manager(self):
        while True:
            """Main command center"""
            print("What would you like to do?")
            print("1. Create new config")
            print("2. Delete existing config")
            print("3. See current configs")
            print("4. Collect results from a monitor service")
            print("5. Collect results from all monitor services")
            print("6. Exit")

            command = input("\nEnter command number: ")
            if command == "1":
                self.create_config()

            elif command == "2":
                self.delete_config()

            elif command == "3":
                self.display_configs()

            elif command == "4":
                self.load_monitor()
                break

            elif command == "5":
                self.load_all_monitors()
                break

            elif command == "6":
                print("Exiting ...")
                exit()

    def restart_handler(self, signum: int, frame: Any) -> None:
        """Kill threads and restart application"""
        global restart_flag
        restart_flag = True
        print("\nInterrupt detected!")

        # Close sockets and kill client threads
        for client in self._clients.values():

            # Send command to quit tasks
            client.send_command("QUIT")

            # Close sockets/kill threads
            print("Closing sockets ...")
            client.close()
            print("Killing client threads ...")
            client.join()

        # Clear clients dict
        self._clients = {}

        # Reset flag
        restart_flag = False

        # Restart menu
        print("Returning to main menu ...")
        time.sleep(4)
        os.system("cls") if sys.platform.startswith("win") else os.system("clear")
        self.start_manager()

    def load_monitor(self):
        """Starts control client for a chosen monitor service"""
        # Get user's choice
        monitor_id, host, port, services = monitor_choice_prompt(
            "Which monitor service would you like to load? [TAB]: ", self._configs
        )

        # Start control client
        self._clients[monitor_id] = ControlClient(
            monitor_id, host, port, services, self._lock
        )
        self._clients[monitor_id].daemon = True
        self._clients[monitor_id].start()

    def load_all_monitors(self):
        """Starts control client for all monitor services"""
        # Loop through and start up clients
        for monitor_id, config in self._configs.items():
            host, port, services = config["IP"], config["Port"], config["Services"]
            self._clients[monitor_id] = ControlClient(
                monitor_id, host, port, services, self._lock
            )
            self._clients[monitor_id].daemon = True
            self._clients[monitor_id].start()

    def stop_all_monitors(self):

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

    def create_config(self):
        """Creates new monitor service config based on user input and saves it"""
        # Set monitor service details
        monitor_id = self.set_monitor_service()
        if monitor_id is None:
            print("")
            return
        print("")

        # Get set of services from user
        services = self.set_services(monitor_id)
        print("")

        # Get params
        for service in services.keys():
            self.set_service_params(service, monitor_id)
            print("")

        # Persist to configs.json
        self.write_config()
        print("Successfully added config: ")
        print(self._configs[monitor_id])
        print("")

    def delete_config(self):
        """Deletes monitor service config based on user input and updates config file"""
        monitor_id = monitor_choice_prompt(
            "Which monitor would you like to delete? [TAB]: ", self._configs
        )[0]
        del self._configs[monitor_id]
        print(f"Config for monitor at {monitor_id} deleted!\n")

    def set_monitor_service(self):
        """Gets the id, monitor ip and port of a monitor service from user and sets in configs"""
        # Get ip, port, id
        monitor_ip = input("Enter monitor ip address: ")
        monitor_port = input("Enter monitor port: ")
        monitor_id = f"{monitor_ip}:{monitor_port}"

        # Ensure user wants to overwrite existing monitor
        if monitor_id in self._configs:
            choice = input(
                "Monitor already exists. Are you sure you want to overwrite it? [Y/N]: "
            )
            if choice.lower() == "n":
                return

        # Set ip, port, id
        self._configs[monitor_id] = {
            "IP": monitor_ip,
            "Port": monitor_port,
            "Services": {},
        }
        return monitor_id

    def set_services(self, monitor_id):
        """Gets services to set up for a given monitor service"""
        while (
            service := service_prompt(
                "Enter a service or press enter when finished [TAB]: "
            )
        ) != "":
            self._configs[monitor_id]["Services"][service] = {}
        return self._configs[monitor_id]["Services"]

    def set_service_params(self, service, monitor_id):
        """Calls method for given service to get parameters for given monitor service"""
        if service == "Ping":
            self.set_ping_params(monitor_id)
        elif service == "Tracert":
            self.set_tracert_params(monitor_id)
        elif service == "HTTP":
            self.set_http_params(monitor_id)
        elif service == "HTTPS":
            self.set_https_params(monitor_id)
        elif service == "NTP":
            self.set_ntp_params(monitor_id)
        elif service == "DNS":
            self.set_dns_params(monitor_id)
        elif service == "TCP":
            self.set_tcp_params(monitor_id)
        elif service == "UDP":
            self.set_udp_params(monitor_id)
        elif service == "Echo":
            self.set_echo_params(monitor_id)

    def set_ping_params(self, monitor_id):
        """Gets service params from a user for a ping task and sets the results to self._configs"""
        # Get params
        print("Enter ping params (press enter for defaults): ")
        host = input("\tEnter host: ")
        ttl = int(input("\tEnter TTL (Default = 64): ").strip() or "64")
        timeout = int(input("\tEnter timeout (Default = 1): ").strip() or "1")
        sequence_number = int(
            input("\tEnter sequence number (Default = 1): ").strip() or "1"
        )
        frequency = int(input("\tEnter frequency (Default = 60): ").strip() or "60")

        # Return param dict
        self._configs[monitor_id]["Services"]["Ping"] = {
            "host": host,
            "ttl": ttl,
            "timeout": timeout,
            "sequence_number": sequence_number,
            "frequency": frequency,
        }

    def set_tracert_params(self, monitor_id):
        """Gets service params from a user for a tracert task and sets the results to self._configs"""
        # Get params
        print("Enter tracert params (press enter for defaults): ")
        host = input("\tEnter host: ")
        max_hops = int(input("\tEnter max hops (Default = 30): ").strip() or "30")
        pings_per_hop = int(
            input("\tEnter pings per hop (Default = 1): ").strip() or "1"
        )
        verbose = (
            input("\tEnter verbosity preference (Default = False): ").strip() or False
        )
        frequency = int(input("\tEnter frequency (Default = 60): ").strip() or "60")

        # Return param dict
        self._configs[monitor_id]["Services"]["Tracert"] = {
            "host": host,
            "max_hops": max_hops,
            "pings_per_hop": pings_per_hop,
            "verbose": verbose,
            "frequency": frequency,
        }

    def set_http_params(self, monitor_id):
        """Gets service params from a user for an http task and sets the results to self._configs"""
        # Get params
        print("Enter http params (press enter for defaults): ")
        url = input("\tEnter url: http://")
        url = f"http://{url}"
        frequency = int(input("\tEnter frequency (Default = 60): ").strip() or "60")

        # Return param dict
        self._configs[monitor_id]["Services"]["HTTP"] = {
            "url": url,
            "frequency": frequency,
        }

    def set_https_params(self, monitor_id):
        """Gets service params from a user for an https task and sets the results to self._configs"""
        # Get params
        print("Enter https params (press enter for defaults): ")
        url = input("\tEnter url: https://")
        url = f"https://{url}"
        timeout = int(input("\tEnter timeout (Default = 5): "))
        frequency = int(input("\tEnter frequency (Default = 60): ").strip() or "60")

        # Return param dict
        self._configs[monitor_id]["Services"]["HTTPS"] = {
            "url": url,
            "timeout": timeout,
            "frequency": frequency,
        }

    def set_ntp_params(self, monitor_id):
        """Gets service params from a user for an ntp task and sets the results to self._configs"""
        # Get params
        print("Enter ntp params (press enter for defaults): ")
        server = input("\tEnter ntp server: ")
        frequency = int(input("\tEnter frequency (Default = 60): ").strip() or "60")

        # Return param dict
        self._configs[monitor_id]["Services"]["NTP"] = {
            "server": server,
            "frequency": frequency,
        }

    def set_dns_params(self, monitor_id):
        """Gets service params from a user for a dns task and sets the results to self._configs"""
        # Get params
        print("Enter dns params (press enter for defaults): ")
        server = input("\tEnter dns server: ")
        query = input("\tEnter server to query: ")
        record_types = []
        while (
            record_type := record_type_prompt(
                "Enter a record type or press enter when finished [TAB]: "
            )
            != ""
        ):
            record_types.append(record_type)
        frequency = int(input("\tEnter frequency (Default = 60): ").strip() or "60")

        # Return param dict
        self._configs[monitor_id]["Services"]["DNS"] = {
            "server": server,
            "query": query,
            "record_types": record_types,
            "frequency": frequency,
        }

    def set_tcp_params(self, monitor_id):
        """Gets service params from a user for a tcp task and sets the results to self._configs"""
        # Get params
        print("Enter tcp params (press enter for defaults): ")
        server = input("\tEnter server or ip address: ")
        port = int(input("\tEnter port number: "))
        frequency = int(input("\tEnter frequency (Default = 60): ").strip() or "60")

        # Return param dict
        self._configs[monitor_id]["Services"]["TCP"] = {
            "server": server,
            "port": port,
            "frequency": frequency,
        }

    def set_udp_params(self, monitor_id):
        """Gets service params from a user for a udp task and sets the results to self._configs"""
        # Get params
        print("Enter udp params (press enter for defaults): ")
        server = input("\tEnter server or ip address: ")
        port = int(input("\tEnter port number: "))
        timeout = int(input("\tEnter timeout (Default = 3): ").strip() or "3")
        frequency = int(input("\tEnter frequency (Default = 60): ").strip() or "60")

        # Return param dict
        self._configs[monitor_id]["Services"]["UDP"] = {
            "server": server,
            "port": port,
            "timeout": timeout,
            "frequency": frequency,
        }

    def set_echo_params(self, monitor_id):
        """Gets service params from a user for an echo task and sets the results to self._configs"""
        # Get params
        print("Enter echo params (press enter for defaults): ")
        server = input("\tEnter server or ip address: ")
        port = int(input("\tEnter port number: "))
        frequency = int(input("\tEnter frequency (Default = 60): ").strip() or "60")

        # Return param dict
        self._configs[monitor_id]["Services"]["Echo"] = {
            "server": server,
            "port": port,
            "frequency": frequency,
        }

    def display_configs(self):
        """Displays current task configurations"""
        for monitor_id, config in self._configs.items():
            print(f"\nMonitor {monitor_id}:")
            columns, lines = shutil.get_terminal_size()
            print("=" * columns)
            print(f"IP: {config['IP']}")
            print(f"Port: {config['Port']}")
            print("Services: ")
            for service, params in config["Services"].items():
                print(f"  {service}: {params}")
        print("")

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

    def run(self):
        """Start up socket and handle client behavior"""
        global restart_flag
        while not restart_flag:
            try:
                # Connect to monitor service
                self.connect()
                time.sleep(2)

                # Send id to monitor service to set
                self.set_id()
                time.sleep(2)

                # Distribute tasks to monitor service
                self.distribute_tasks()
                time.sleep(2)

                # Monitor status until keyboard interrupt
                self.monitor_status()

            except socket.error:
                print(
                    f"Error with connection to monitor service at {self._monitor_host}:{self._monitor_port} ... trying to reconnect!"
                )
                self._socket.close()
                time.sleep(10)

    def connect(self):
        """Connect to monitor service"""

        # Create new socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Enable keepalive behavior to receive messages for detecting dead connections
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        global restart_flag
        while not restart_flag:
            self._lock.acquire()
            try:
                print(
                    f"\nAttempting to connect to monitor service at {self._monitor_host}:{self._monitor_port} ..."
                )
                self._socket.connect((self._monitor_host, self._monitor_port))
                print(
                    f"Successfully connected to monitor service at {self._monitor_host}:{self._monitor_port}"
                )
                self._lock.release()
                break

            except socket.error:
                print(
                    f"Connection to monitor service at {self._monitor_host}:{self._monitor_port} failed! Trying again!"
                )
                self._lock.release()
                time.sleep(15)

    def set_id(self):
        """Send monitor service an ID"""
        # Assign ID to monitor service
        with self._lock:
            try:
                response = self.send_command("SET_ID")
                if response == "awaiting ID ...":
                    print(
                        f"Sending ID {self._monitor_id} to monitor service at {self._monitor_host}:{self._monitor_port}\n"
                    )
                    self._socket.send(self._monitor_id.encode("utf-8"))
            except socket.error as e:
                print(f"Socket error: {e}")

    def close(self):
        """Close connection with given monitor service"""
        # Close socket connection with given id
        self._socket.close()

    def send_command(self, command):
        """Send command over given monitor service"""
        try:
            # Send command
            print(
                f"Sending {command} command to monitor service {self._monitor_id} at {self._monitor_host}:{self._monitor_port}"
            )
            self._socket.sendall(command.encode())

            # Await acknowledgment
            response = self._socket.recv(1024).decode("utf-8")
            print(
                f"Command to monitor service {self._monitor_id} acknowledged: {response}"
            )
            return response
        except socket.error as e:
            print(f"Socket error: {e}")

    def distribute_tasks(self):
        """Distribute defined tasks to monitors"""
        with self._lock:
            try:
                # Send the start command to prepare monitor for config
                response = self.send_command("START")

                # If response is awaiting tasks, send config
                if response == "awaiting tasks ...":

                    # Create task config data and send
                    task_configs = pickle.dumps(self._services)
                    self._socket.sendall(task_configs)

                    # Await confirmation of tasks
                    response = self._socket.recv(1024).decode("utf-8")
                    print(
                        f"Task start up at monitor service {self._monitor_id} acknowledged: {response}\n"
                    )

            except socket.error as e:
                print(f"Socket error: {e}")

    def monitor_status(self):
        """Await results and status updates for given monitor service"""
        # Await responses until error or condition
        global restart_flag
        try:
            while not restart_flag:
                response = self._socket.recv(1024).decode("utf-8")
                if response:
                    with self._lock:
                        print(response)
                else:
                    break

        except socket.error:
            print(
                f"Connection to monitor service ${self._monitor_host, self._monitor_port} lost!"
            )
            self._socket.close()


if __name__ == "__main__":
    # Get terminal size
    columns, lines = shutil.get_terminal_size()
    print("")

    # Print project title
    print(r" _   _      _    ____                ".center(columns - 1))
    print(r"| \ | | ___| |_ / ___|__ _ _ __ ___  ".center(columns - 1))
    print(r"|  \| |/ _ \ __| |   / _` | '_ ` _ \ ".center(columns - 1))
    print(r"| |\  |  __/ |_| |__| (_| | | | | | |".center(columns - 1))
    print(r"|_| \_|\___|\__|\____\__,_|_| |_| |_|".center(columns - 1))
    print("")
    title_string = "Management Service"
    print(title_string.center(columns - 1))
    author_string = "by Cameron Hester"
    print(author_string.center(columns - 1))
    print("\n")

    # Prompt user to start program
    start_string = "Press enter to begin ..."
    print(start_string.center(columns - 1))

    # Sleep to prevent auto enter
    time.sleep(1)

    # Start program upon keypress
    if input("") == "":

        # Clear terminal
        os.system("cls") if sys.platform.startswith("win") else os.system("clear")
        manager = Manager()
        signal.signal(signal.SIGINT, manager.restart_handler)
        manager.start_manager()
