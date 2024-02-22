import socket
import threading
import sys


class Client:
    def __init__(self, host='localhost', port=6667):
        self.host = host
        self.port = port
        self.nickname = ""
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.client_socket.connect((self.host, self.port))
        print(f"Connected to server with {self.host}:{self.port}")
        self.nickname = sys.argv[1] if len(sys.argv) > 1 else input("Enter your nickname: ")
        self.client_socket.send(self.nickname.encode('utf-8'))

    def send_command(self):
        """ Read user command and send it to server """

        while True:
            command = input('>')
            self.client_socket.send(command.encode('utf-8'))

    def receive_response(self):
        """ Display server response """

        while True:
            try:
                data = self.client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                else:
                    print(data)
            except OSError as e:
                break


client = Client()
client.connect()

thread_recv = threading.Thread(target=client.receive_response)
thread_recv.start()

thread_send = threading.Thread(target=client.send_command)
thread_send.start()

thread_recv.join()
thread_send.join()

client.client_socket.close()
