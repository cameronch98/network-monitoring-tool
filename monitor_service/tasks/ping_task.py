import socket
import threading
import time
from datetime import datetime
from typing import NoReturn

from monitor_service.network_tests import ping


class PingTask(threading.Thread):
    def __init__(
        self,
        host: str,
        ttl: int = 64,
        timeout: int = 1,
        sequence_number: int = 1,
        frequency: int = 30,
        conn: socket.socket = None,
    ) -> None:
        # Super call
        super().__init__()

        # Define parameters
        self._host: str = host
        self._ttl: int = ttl
        self._timeout: int = timeout
        self._sequence_number: int = sequence_number
        self._frequency: int = frequency

        # Define control attributes
        self.paused: bool = False  # Indicates if the task is paused
        self.stopped: bool = False  # Indicates if the task is stopped
        self.condition: threading.Condition = threading.Condition()

        # Connection
        self._conn: socket.socket = conn

        # Messages
        self._msgs: list = []

    def run(self) -> NoReturn:
        while not self.stopped:
            with self.condition:
                if self.paused:
                    self.condition.wait()  # Wait until the task is resumed
                else:
                    result = ping(
                        self._host, self._ttl, self._timeout, self._sequence_number
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
