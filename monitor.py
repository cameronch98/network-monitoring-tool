import pickle
import shutil
import socket
import threading
from datetime import datetime
from typing import NoReturn

from service_checks import run_service_check


class Monitor:

    def __init__(self, monitor_host: str = "127.0.0.1", monitor_port: int = 65432):
        # Identification
        self._id = ""  # Generate a random id or something
        self._monitor_host: str = monitor_host  # Server host address
        self._monitor_port: int = monitor_port  # Server port number

        # Tasks
        self._tasks: dict = {}

    def start(self):
        """Set up connection for management_service to send commands"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self._monitor_host, self._monitor_port))
            s.listen()
            while True:
                print(
                    f"Listening for connections on {self._monitor_host}:{self._monitor_port}\n"
                )
                conn, addr = s.accept()
                with conn:
                    print(f"Connected by: {addr}\n")

                    try:
                        while True:
                            # Receive command
                            command = conn.recv(1024).decode("utf-8")

                            # Break out to accept new connections if no command
                            if not command:
                                break
                            else:
                                print(f"Command received: {command}")

                            # Start up and bulk operation commands
                            if command == "SET_ID":
                                print("Awaiting ID ...")
                                conn.sendall("awaiting ID ...".encode("utf-8"))
                                self._id = conn.recv(1024).decode("utf-8")
                                print(f"ID received and set: {self._id}\n")

                            elif command == "START":
                                # Skip config and reconnect existing threads if active tasks
                                if self._tasks:
                                    print(
                                        "Tasks already started! Reconnecting task threads to send data ..."
                                    )
                                    conn.sendall(
                                        "reconnecting tasks ...".encode("utf-8")
                                    )
                                    self.reconnect_tasks(conn)
                                else:
                                    print("Awaiting task ...")
                                    conn.sendall("awaiting tasks ...".encode("utf-8"))
                                    config = conn.recv(1024)
                                    config = pickle.loads(config)
                                    print(f"Tasks received: {config}\n")
                                    conn.sendall("tasks started!".encode("utf-8"))
                                    self.configure_tasks(config, conn)
                                    self.start_tasks()

                            elif command == "QUIT":
                                print("Stopping tasks ...")
                                self.stop_tasks()
                                conn.sendall("tasks stopped!".encode("utf-8"))
                                print(f"Closing connection to {addr}")
                                conn.close()
                                break

                    except socket.error as e:
                        print(f"Socket error: {e}")

                    finally:
                        print("MANAGER CONNECTION LOST")
                        conn.close()

    def configure_tasks(self, config, conn):
        """Starts task instances based on config"""
        # Create the task objects/threads
        for task, params in config.items():
            frequency = params["frequency"]
            del params["frequency"]
            self._tasks[task] = NetworkTask(
                self._monitor_host, self._monitor_port, task, params, frequency, conn
            )

    def start_tasks(self):
        """Start all tasks in task list"""
        for task in self._tasks.values():
            print("Starting task {}".format(task))
            task.start()

    def reconnect_tasks(self, conn: socket.socket):
        """Re-establishes conn in task threads after reconnection"""
        for task in self._tasks.values():
            task.set_connection(conn)

    def stop_tasks(self):
        """Stop all tasks in task list"""
        for task in self._tasks.values():
            task.stop()


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
        # Loop until thread event is set
        while not self._event.is_set():
            try:
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

            except KeyboardInterrupt:
                print("Process interrupted by CTRL + C")
                self._conn.close()
                self.stop()

            # Sleep the loop for the given interval
            self._event.wait(self._frequency)

    def stop(self) -> NoReturn:
        """Stop thread by setting event and joining"""
        self._event.set()
        self.join()

    def send_msgs(self):
        """Send messages currently stored in self._msgs"""
        try:
            self._conn.sendall("\n".join(self._msgs).encode())
            self._msgs = []  # Clear msgs in case of successful send
        except socket.error:
            print(
                f"Saving {self._task} task results for reconnection - results saved: {len(self._msgs)}"
            )
            self._conn.close()

    def set_connection(self, conn: socket.socket) -> NoReturn:
        """Set the connection data is being sent over"""
        self._conn = conn


if __name__ == "__main__":
    ip = input("Enter IP for monitor: ")
    port = int(input("Enter port for monitor: "))
    monitor = Monitor(ip, port)
    monitor.start()
