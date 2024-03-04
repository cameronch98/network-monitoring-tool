import shutil
import socket
import threading
import time
from datetime import datetime
from typing import NoReturn

from monitor import Monitor
from network_tests import check_dns_server_status


class DNSTask(threading.Thread, Monitor):
    def __init__(
        self,
        server: str,
        query: str,
        record_types: list = None,
        frequency: int = 30,
        conn: socket.socket = None,
    ):
        super().__init__()

        if record_types is None:
            record_types = []
        self._server: str = server
        self._query: str = query
        self._record_types: list = record_types
        self._frequency: int = frequency  # Interval for tests to be run
        self._event: threading.Event = threading.Event()  # Event to stop threads
        self._conn: socket.socket = conn  # Socket connection
        self._msgs: list = []

    def run(self) -> NoReturn:
        # Loop until thread event is set
        while not self._event.is_set():
            try:
                msg = ""

                # Header
                columns, lines = shutil.get_terminal_size()
                msg += f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] DNS Service Check\n[Monitor: {self.host}:{self.port} , {self._id}]\n"
                msg += "=" * columns + "\n"

                # DNS Test
                msg += (
                    f"Querying DNS Server {self._server} with Server {self._query} ... "
                )
                for dns_record_type in self._record_types:
                    dns_server_status, dns_query_results = check_dns_server_status(
                        self._server, self._query, dns_record_type
                    )
                    msg += f"\nDNS Server: {self._server}, Status: {dns_server_status}, {dns_record_type} Records Results: {dns_query_results}"

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
        self._event.set()
        self.join()

    def send_msgs(self):
        """Send messages currently stored in self._msgs"""
        try:
            self._conn.sendall("\n".join(self._msgs).encode())
            self._msgs = []  # Clear msgs in case of successful send
        except socket.error as e:
            print(f"Socket error: {e}")
            print(
                f"Saving dns task results for reconnection - results saved: {len(self._msgs)}"
            )
            self._conn.close()

    def set_connection(self, conn: socket.socket) -> NoReturn:
        """Set the connection data is being sent over"""
        self._conn = conn
