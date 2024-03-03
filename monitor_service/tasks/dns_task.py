import socket
import threading
import time
from datetime import datetime
from typing import NoReturn

from monitor_service.network_tests import check_dns_server_status


class DNSTask(threading.Thread):
    def __init__(
        self,
        server: str,
        query: str,
        record_types: list = None,
        frequency: int = 30,
        conn: socket.socket = None,
    ):
        super().__init__()

        # Define parameters
        if record_types is None:
            record_types = []
        self._server: str = server
        self._query: str = query
        self._record_types: list = record_types
        self._frequency: int = frequency

        # Define control attributes
        self.paused: bool = False  # Indicates if the task is paused
        self.stopped: bool = False  # Indicates if the task is stopped
        self.condition: threading.Condition = threading.Condition()

        # Socket
        self._conn: socket.socket = conn

        # Messages
        self._msgs: list = []

    def run(self) -> NoReturn:
        while not self.stopped:
            with self.condition:
                if self.paused:
                    self.condition.wait()  # Wait until the task is resumed
                else:
                    for record_type in self._record_types:
                        result = check_dns_server_status(
                            self._server, self._query, record_type
                        )
                        self._msgs.append(
                            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] - {result}"
                        )
                    self.send_msgs()
            time.sleep(self._frequency)  # Wait for the set frequency

    def pause(self) -> NoReturn:
        self.paused = True

    def resume(self) -> NoReturn:
        with self.condition:
            self.paused = False
            self.condition.notify()  # Notify the thread to resume

    def stop(self) -> NoReturn:
        self.stopped = True
        if self.paused:
            self.resume()  # Ensure the thread is not waiting to be resumed

    def send_msgs(self):
        """Send messages currently stored in self._msgs"""
        try:
            self._conn.sendall("\n".join(self._msgs).encode())
            self._msgs = []  # Clear msgs in case of successful send
        except socket.error as e:
            print(f"Socket error: {e}")
            print(f"Saving message for reconnection ...")
            self._conn.close()

    def set_connection(self, conn: socket.socket) -> NoReturn:
        """Set the connection data is being sent over"""
        self._conn = conn
