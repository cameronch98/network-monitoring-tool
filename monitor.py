import os
import pickle
import shutil
import signal
import socket
import sys
import threading
import time
from datetime import datetime
from typing import NoReturn, Any

from service_checks import run_service_check

shutdown_flag = False


class Monitor:

    def __init__(self, monitor_host: str = "127.0.0.1", monitor_port: int = 65432):
        # Identification
        self._id = ""  # Generate a random id or something
        self._monitor_host: str = monitor_host  # Server host address
        self._monitor_port: int = monitor_port  # Server port number

        # Tasks
        self._tasks: dict = {}

        # Connection
        self._socket = None
        self._conn = None

    def start(self):
        """Set up connection for management_service to send commands"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self._socket:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((self._monitor_host, self._monitor_port))
            self._socket.listen()
            while not shutdown_flag:
                print(
                    f"\nListening for connections on {self._monitor_host}:{self._monitor_port}"
                )
                self._conn, addr = self._socket.accept()
                with self._conn:
                    print(f"Connected by: {addr}")

                    try:
                        while True:
                            # Receive command
                            command = self._conn.recv(1024).decode("utf-8")

                            # Break out to accept new connections if no command
                            if not command:
                                break
                            else:
                                print(f"\nCommand received: {command}")

                            # Start up and bulk operation commands
                            if command == "SET_ID":
                                print("Awaiting ID ...")
                                self._conn.sendall("awaiting ID ...".encode("utf-8"))
                                self._id = self._conn.recv(1024).decode("utf-8")
                                print(f"ID received and set: {self._id}")

                            elif command == "START":
                                # Skip config and reconnect existing threads if active tasks
                                if self._tasks:
                                    print(
                                        "Tasks already started! Reconnecting task threads to send data ..."
                                    )
                                    self._conn.sendall(
                                        "reconnecting tasks ...".encode("utf-8")
                                    )
                                    self.reconnect_tasks()
                                else:
                                    print("Awaiting tasks ...")
                                    self._conn.sendall(
                                        "awaiting tasks ...".encode("utf-8")
                                    )
                                    config = self._conn.recv(1024)
                                    config = pickle.loads(config)
                                    print(f"Tasks received: {config}\n")
                                    self._conn.sendall("tasks started!".encode("utf-8"))
                                    self.configure_tasks(config)
                                    self.start_tasks()

                            elif command == "QUIT":
                                # Alert client and shut down
                                self._conn.sendall("stopping tasks!".encode("utf-8"))
                                self.stop_tasks()
                                break

                    except socket.error as e:
                        print(f"Socket error: {e}")

                    finally:
                        self._conn.close()

    def configure_tasks(self, config: dict):
        """Starts task instances based on config"""
        # Create the task objects/threads
        for task, params in config.items():
            frequency = params["frequency"]
            del params["frequency"]
            self._tasks[task] = NetworkTask(
                self._monitor_host,
                self._monitor_port,
                task,
                params,
                frequency,
                self._conn,
            )

    def start_tasks(self):
        """Start all tasks in task list"""
        for task in self._tasks.values():
            print("Starting task {}".format(task))
            task.start()
        print("")

    def reconnect_tasks(self):
        """Re-establishes conn in task threads after reconnection"""
        for task in self._tasks.values():
            task.set_connection(self._conn)

    def stop_tasks(self):
        """Stops all tasks in task threads"""
        global shutdown_flag
        shutdown_flag = True

        # Wait for threads to quit
        print("\nKilling threads ...")
        for task in self._tasks.values():
            task.join()

        self._tasks = {}

        shutdown_flag = False

    def shutdown_handler(self, signum: int = None, frame: Any = None) -> None:
        """Set shutdown flag, kill threads, exit application"""
        # Kill running tasks
        self.stop_tasks()

        # Close sockets
        print("Closing connection ...")
        self._conn.close()
        print("Closing server socket ...")
        self._socket.close()

        print("Shutting down server ... goodbye!")
        exit()


class NetworkTask(threading.Thread):
    def __init__(
        self,
        monitor_host: str,
        monitor_port: int,
        task: str,
        params: dict,
        frequency: int,
        conn: socket.socket = None,
    ):
        super().__init__()

        # Monitor information
        self._monitor_host: str = monitor_host
        self._monitor_port: int = monitor_port

        # Network test information
        self._task: str = task
        self._params: dict = params

        # Thread control
        self._event: threading.Event = threading.Event()
        self._frequency: int = frequency

        # Connection to send data over
        self._conn: socket.socket = conn

        # Messages to send
        self._msgs: list = []

    def run(self) -> NoReturn:

        # Loop until shutdown event is set
        time.sleep(3)
        while not shutdown_flag:

            # Init msg
            msg = ""

            # Header
            columns, lines = shutil.get_terminal_size()
            msg += f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][Monitor: {self._monitor_host}:{self._monitor_port}] {self._task} Service Check \n"
            msg += "=" * columns + "\n"

            # Get results
            print(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][Monitor: {self._monitor_host}:{self._monitor_port}] - performing {self._task} test ..."
            )
            msg += run_service_check(self._task, self._params.values())

            # Send message
            self._msgs.append(msg)
            self.send_msgs()

            # Sleep the loop for the given interval
            self._event.wait(self._frequency)

    def send_msgs(self):
        """Send messages currently stored in self._msgs"""
        try:

            self._conn.sendall("\n".join(self._msgs).encode())
            print(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][Monitor: {self._monitor_host}:{self._monitor_port}] - successfully sent {self._task} test results!"
            )
            self._msgs = []  # Clear msgs in case of successful send
        except socket.error:
            print(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][Monitor: {self._monitor_host}:{self._monitor_port}] - connection to management service down!"
            )
            print(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][Monitor: {self._monitor_host}:{self._monitor_port}] - saving {self._task} task results for reconnection - results saved: {len(self._msgs)}"
            )
            self._conn.close()

    def set_connection(self, conn: socket.socket) -> NoReturn:
        """Set the connection data is being sent over"""
        self._conn = conn


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
    title_string = "Monitor Service"
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

        # Get configuration and start up
        ip = input("Enter IP for monitor: ")
        port = int(input("Enter port for monitor: "))
        monitor = Monitor(ip, port)
        signal.signal(signal.SIGINT, monitor.shutdown_handler)
        monitor.start()
