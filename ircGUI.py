import socket
import threading
import sys
import tkinter as tk
from tkinter import scrolledtext, Entry, Button, END


class ClientGUI:
    def __init__(self, host='localhost', port=6667):
        self.host = host
        self.port = port
        self.nickname = ""
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.init_gui()

    def init_gui(self):
        self.root = tk.Tk()
        self.root.title("IRC Client")

        self.text_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=100, height=35)
        self.text_area.pack(padx=10, pady=10)

        self.input_entry = Entry(self.root, width=100)
        self.input_entry.pack(pady=10, ipady=8)

        self.send_button = Button(self.root, text="Send", command=self.send_command)
        self.send_button.pack(pady=10)

    def connect(self):
        self.client_socket.connect((self.host, self.port))
        self.print_message(f"Connected to server with {self.host}:{self.port}")

        self.nickname = sys.argv[1] if len(sys.argv) > 1 else input("Enter your nickname: ")
        self.client_socket.send(self.nickname.encode('utf-8'))

    def send_command(self):
        """ Read user command, send it to server, and update GUI """

        command = self.input_entry.get()
        self.client_socket.send(command.encode('utf-8'))
        self.input_entry.delete(0, END)  # Clear the input field

    def receive_response(self):
        """ Display server response in GUI """

        while True:
            try:
                data = self.client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                else:
                    self.print_message(data)
            except OSError as e:
                break

    def print_message(self, message):
        self.text_area.insert(tk.END, f"{message}\n")
        self.text_area.yview(tk.END)  # Auto-scroll to the bottom

    def run_gui(self):
        self.connect()

        # Start GUI and threads
        thread_recv = threading.Thread(target=self.receive_response)
        thread_recv.start()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

        thread_recv.join()
        self.client_socket.close()

    def on_close(self):
        """ Handler for the window close event """
        try:
            self.client_socket.shutdown(socket.SHUT_RDWR)  # Shutdown the socket
        except OSError as e:
            # Handle exceptions, e.g., socket already closed
            print(f"Error during socket shutdown: {e}")

        self.client_socket.close()  # Close the socket
        self.root.destroy()


client_gui = ClientGUI()
client_gui.run_gui()

