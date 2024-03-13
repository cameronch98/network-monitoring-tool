import socket


def tcp_server():
    """
    Local TCP echo server for use with network monitoring application and echo client. Will accept messages in the same
    TCP connection until the "Goodbye" message is received. In the case of the included echo client, this will be done
    via user input. In the case of the network monitoring application, this will be done automatically.
    :return: None
    """
    # Create IPv4 sock stream socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket
    server_address = '127.0.0.1'  # Loop back address for local host
    server_port = 12345  # Port to listen on
    server_sock.bind((server_address, server_port))

    # Listen for incoming connections
    server_sock.listen(5)  # Configure for backlog of 5 connections

    print('Server is listening for incoming connections...')

    try:
        while True:
            # Accept a connection
            client_sock, client_address = server_sock.accept()
            print(f"Connection from {client_address}")

            try:
                # Receive messages until "Goodbye" received
                while True:

                    # Receive data from echo client
                    message = client_sock.recv(1024).decode()
                    if not message or message == "Goodbye":
                        print(f"Goodbye message received. Closing connection with {client_address}...")
                        break

                    # Print the message and return to client
                    print(f"Received echo request message: {message}")
                    print(f"Sending back echo reply message: {message}")
                    client_sock.sendall(message.encode())

            finally:
                # Close client connection
                client_sock.close()
                print(f"Connection with {client_address} closed")

    except KeyboardInterrupt:
        print("Server is shutting down")

    finally:
        # Close server socket
        server_sock.close()
        print("Server socket closed")


if __name__ == '__main__':
    tcp_server()
