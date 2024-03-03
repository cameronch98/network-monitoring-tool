import pickle

from network_tests import *
from tasks.dns_task import DNSTask
from tasks.echo_task import EchoTask
from tasks.http_task import HTTPTask
from tasks.https_task import HTTPSTask
from tasks.ntp_task import NTPTask
from tasks.ping_task import PingTask
from tasks.tcp_task import TCPTask
from tasks.tracert_task import TracertTask
from tasks.udp_task import UDPTask


class Monitor:
    """
    CURRENTLY INCLUDING ALL TESTS FOR MONITORING IN THE CLASS. PLAY AROUND WITH IMPORTING AND JUST CALLING THE METHODS
    INSTEAD SINCE YOU CAN JUST PASS THEM THE THREAD OBJECTS AND CONFIG TO LET MONITOR KEEP CONTROL BUT STAY MORE
    MODULAR. THIS MAY BE BETTER BUT NEED TO TRY BOTH. IF SO, YOU MAY WANT TO TRY BOTH KEEPING SERVER AS AN INPUT
    PARAM OR NOT. IT MIGHT BE FINE TO JUST KEEP THINGS HOW THEY ARE AND ADD ANOTHER LAYER OF NESTING TO THE SERVER_DICT.
    THIS COULD SAVE A LOT OF TIME AND ALL YOUR FUNCTIONS COULD REMAIN THE SAME FOR THE MOST PART. THE SERVICE CHECKS
    NEED TO BE UPDATED TO INTAKE THE CONNECTION AND SEND THINGS OVER THE SOCKET INSTEAD OF PRINTING THOUGH.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 65432):
        # Identification
        self._id = ""  # Generate a random id or something
        self.host: str = host  # Server host address
        self.port: int = port  # Server port number

        # Tasks
        self._tasks: dict = {}

    def start(self):
        """Set up connection for management_service to send commands"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            while True:
                print(f"Listening for connections on {self.host}:{self.port}")
                conn, addr = s.accept()
                with conn:
                    print(f"Connected by: {addr}\n")

                    # Reconnect existing threads if active tasks
                    if self._tasks:
                        self.reconnect_tasks(conn)

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

                    except socket.error or KeyboardInterrupt:
                        print("Stopping tasks ...")
                        self.stop_tasks()
                        print("Connection closing ...")
                        conn.close()
                        break

                    finally:
                        conn.close()

    def configure_tasks(self, config, conn):
        """Starts task instances based on config"""
        # Create the task objects/threads
        for task, params in config.items():
            if task == "Ping":
                self._tasks[task] = PingTask(*params.values(), conn)
            elif task == "Tracert":
                self._tasks[task] = TracertTask(*params.values(), conn)
            elif task == "HTTP":
                self._tasks[task] = HTTPTask(*params.values(), conn)
            elif task == "HTTPS":
                self._tasks[task] = HTTPSTask(*params.values(), conn)
            elif task == "NTP":
                self._tasks[task] = NTPTask(*params.values(), conn)
            elif task == "DNS":
                self._tasks[task] = DNSTask(*params.values(), conn)
            elif task == "TCP":
                self._tasks[task] = TCPTask(*params.values(), conn)
            elif task == "UDP":
                self._tasks[task] = UDPTask(*params.values(), conn)
            elif task == "Echo":
                self._tasks[task] = EchoTask(*params.values(), conn)

    def start_tasks(self):
        """Start all tasks in task list"""
        for task in self._tasks.values():
            task.run()

    def reconnect_tasks(self, conn: socket.socket):
        """Re-establishes conn in task threads after reconnection"""
        for task in self._tasks:
            task.set_connection(conn)

    def pause_tasks(self):
        """Pause all tasks in task list"""
        for task in self._tasks.values():
            task.pause()

    def resume_tasks(self):
        """Pause all tasks in task list"""
        for task in self._tasks.values():
            task.resume()

    def stop_tasks(self):
        """Stop all tasks in task list"""
        for task in self._tasks.values():
            task.stop()
        self._tasks = []


if __name__ == "__main__":
    monitor = Monitor()
    monitor.start()
