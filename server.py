import socket
import sys
import threading
from commands import IRCCommands, HELP_MESSAGE


class Server:
    def __init__(self, host='localhost', port=6667):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}  # {client_socket1: {"nickname": "sarah", "status": "available", "last_channel": None}, client_socket2: {...} , ...}
        self.channels = {}  # {channel_name1: {"clients": [client_socket1, client_socket2], "key": "channel_key"}, ...}

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server started with {self.host}:{self.port}")

        while True:
            client_socket, client_address = self.server_socket.accept()
            nickname = client_socket.recv(1024).decode('utf-8')
            client_socket.send(f"Welcome {nickname} !".encode())
            self.clients[client_socket] = {"nickname": nickname, "status": "available"}
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_thread.start()

    def handle_client(self, client_socket):
        nickname = self.clients[client_socket]["nickname"]
        join_message = f"{nickname} has joined the server!"
        self.broadcast_to_all(join_message, client_socket)

        while True:
            try:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                print(data)
                self.handle_command(data, client_socket)
            except OSError as e:
                break

        client_socket.close()

    def handle_command(self, command, client_socket):
        split_data = command.split(" ")
        cmd = split_data[0]

        if cmd == IRCCommands.HELP.value:
            self.handle_help(client_socket)
        if cmd == IRCCommands.AWAY.value:
            self.handle_away(command, client_socket)
        if cmd == IRCCommands.LIST.value:
            self.handle_list(client_socket)
        if cmd == IRCCommands.JOIN.value:
            self.handle_join(command, client_socket)
        if cmd == IRCCommands.NAMES.value:
            self.handle_names(command, client_socket)
        if cmd == IRCCommands.INVITE.value:
            self.handle_invite(command, client_socket)
        if cmd == IRCCommands.MSG.value:
            self.handle_msg(command, client_socket)
        if cmd == IRCCommands.QUIT.value:
            self.handle_quit(client_socket)

    def handle_help(self, client_socket):
        client_socket.send(HELP_MESSAGE.encode())

    def handle_list(self, client_socket):
        if not self.channels:
            client_socket.send("No channels available.".encode())
            return

        message = "List of channels: \n"
        for channel_name in self.channels:
            message += f"{channel_name}\n"
        client_socket.send(message.encode())

    def handle_away(self, command, client_socket):
        # We split one time to get the complete away message
        split_cmd = command.split(" ", 1)

        if len(split_cmd) > 1:
            message = split_cmd[1]
            self.clients[client_socket]["status"] = message
            client_socket.send(f"You are now OFF with the message: {message}".encode())
        else:
            self.clients[client_socket]["status"] = "available"
            client_socket.send("You are now AVAILABLE.".encode())

    def handle_join(self, command, client_socket):
        split_cmd = command.split(" ")
        if len(split_cmd) < 2:
            client_socket.send("Invalid /join command. Usage: /join <channel> [key]".encode())
            return

        channel_name = split_cmd[1]
        channel_key = split_cmd[2] if len(split_cmd) > 2 else None

        if not channel_name.startswith("#"):
            client_socket.send("Invalid channel name. Channel names must start with #.".encode())
            return

        if channel_name not in self.channels:
            # Channel doesn't exit => Create it
            self.channels[channel_name] = {"clients": [], "key": channel_key}
            client_socket.send(f"Channel {channel_name} created.".encode())

        # Verify if the user is already in the channel
        if client_socket in self.channels[channel_name]["clients"]:
            client_socket.send(f"You are already in channel {channel_name}.".encode())
            return

        # Verify key
        if self.channels[channel_name]["key"] and self.channels[channel_name]["key"] != channel_key:
            client_socket.send("Incorrect channel key. Unable to join the channel.".encode())
            return

        # Join
        self.channels[channel_name]["clients"].append(client_socket)

        # Save last channel for the client
        self.save_last_channel(client_socket, channel_name)

        client_socket.send(f"You just joined channel {channel_name}.".encode())

        join_message = f"{self.clients[client_socket]['nickname']} has joined the channel! "
        self.broadcast_to_channel(channel_name, join_message, client_socket)

    def handle_names(self, command, client_socket):
        split_cmd = command.split(" ")

        if len(split_cmd) == 2:
            channel_name = split_cmd[1]
            if channel_name.startswith("#"):
                self.names_in_channel(channel_name, client_socket)
            else:
                client_socket.send("Invalid channel name. Must start with #.".encode())
        elif len(split_cmd) == 1:
            self.names_in_all_channels(client_socket)
        else:
            client_socket.send("Invalid /names command. Usage: /names [channel]".encode())
            return

    def handle_msg(self, command, client_socket):
        split_cmd = command.split(" ", 2)

        if len(split_cmd) > 1:
            if len(split_cmd) > 2:
                target = split_cmd[1]
                message = split_cmd[2]

                # target is a user
                if self.get_socket_for_nickname(target):
                    self.send_msg_to_user(client_socket, target, message)
                elif target.startswith("#"):
                    # target is channel
                    self.send_msg_to_channel(client_socket, target, message)
                else:
                    # target is not a user and not a channel
                    self.broadcast_to_all(f"{self.clients[client_socket]['nickname']} (broadcast): {target} {message}", client_socket)
            elif len(split_cmd) == 2:
                message = split_cmd[1]
                self.broadcast_to_all(f"{self.clients[client_socket]['nickname']} (broadcast): {message}", client_socket)
        else:
            client_socket.send("Invalid /msg command. Usage: /msg <channel|nickname> message".encode())

    def handle_invite(self, command, client_socket):
        split_cmd = command.split(" ")
        if len(split_cmd) != 2:
            client_socket.send("Invalid /invite command. Usage: /invite <nick>".encode())
            return

        target_nickname = split_cmd[1]
        sender_nickname = self.clients[client_socket]["nickname"]

        # Get the last channel joined by the sender
        last_channel = self.clients[client_socket].get("last_channel")

        if last_channel:
            # Verify if the user is already in the channel
            target_socket = self.get_socket_for_nickname(target_nickname)
            if not target_socket:
                client_socket.send(f"No user found with the nickname {target_nickname}.".encode())
                return

            if target_socket in self.channels[last_channel]["clients"]:
                client_socket.send(f"{target_nickname} is already in the channel.".encode())
            else:
                client_socket.send(f"Invitation sent to {target_nickname}.".encode())
                target_socket.send(f"{sender_nickname} invites you to join {last_channel} channel! "
                                   f"Enter /join <canal> [cle] to join!".encode())
        else:
            client_socket.send("You haven't joined any channel yet. Cannot send an invitation.".encode())


    def handle_quit(self, client_socket):
        nickname = self.clients[client_socket]["nickname"]

        # Broadcast quit message to all channels
        quit_message = f"{nickname} has left the server."
        self.broadcast_to_all(quit_message, client_socket)

        # Remove the user from all channels
        self.remove_user_from_channels(client_socket)

        # Close the client socket
        client_socket.close()

        # Remove the client from the clients dictionary
        del self.clients[client_socket]

    # To use in handle_client
    def broadcast_to_all(self, message, sender_socket=None):
        for client_socket in self.clients:
            if client_socket != sender_socket:
                client_socket.send(message.encode())

    # To use in handle_join
    def broadcast_to_channel(self, channel_name, message, sender_socket):
        for client_socket in self.channels[channel_name]["clients"]:
            if client_socket != sender_socket:
                client_socket.send(message.encode())

    # To use in handle_names
    def names_in_channel(self, channel_name, client_socket):
        if channel_name in self.channels:
            client_socket.send(f"Users in {channel_name}: {', '.join([self.clients[client]['nickname'] for client in self.channels[channel_name]['clients']])}".encode())
        else:
            client_socket.send(f"Channel {channel_name} does not exist.".encode())

    # To use in handle_names
    def names_in_all_channels(self, client_socket):
        if not self.channels:
            client_socket.send("No channels available.".encode())
        else:
            message = "Users in all channels:\n"
            for channel_name, channel_info in self.channels.items():
                message += f"{channel_name}: {', '.join([self.clients[client]['nickname'] for client in channel_info['clients']])}\n"
            client_socket.send(message.encode())

    # To use in handle_msg
    def send_msg_to_user(self, sender_socket, target_nickname, message):
        sender_nickname = self.clients[sender_socket]["nickname"]

        for client_socket, client_info in self.clients.items():
            if client_info["nickname"] == target_nickname:

                msg = f"{sender_nickname} (private): {message}"
                client_socket.send(msg.encode())
                sender_socket.send(f"Message sent to {target_nickname}.".encode())

                if client_info["status"] != "available":
                    # Get the message left by the user
                    message_left = client_info.get("status")
                    sender_socket.send(f"({target_nickname} is currently OFF. Message left: {message_left})".encode())
                return

        sender_socket.send(f"No user found with the nickname {target_nickname}.".encode())

    # To use in handle_msg
    def send_msg_to_channel(self, sender_socket, channel_name, message):
        if channel_name in self.channels:
            sender_nickname = self.clients[sender_socket]["nickname"]
            msg = f"{sender_nickname} (channel {channel_name}): {message}"
            self.broadcast_to_channel(channel_name, msg, sender_socket)
        else:
            sender_socket.send(f"Channel {channel_name} does not exist.".encode())

    # To use in handle_invite
    # channels = {channel_name1: {"clients": [client_socket1, client_socket2], "key": "channel_key"}, ...}
    def get_channel_for_client(self, client_socket):
        for channel_name, channel_info in self.channels.items():
            if client_socket in channel_info["clients"]:
                return channel_name
        return None

    # To use in handle_invite
    def get_socket_for_nickname(self, target_nickname):
        for client_socket, client_info in self.clients.items():
            if client_info["nickname"] == target_nickname:
                return client_socket
        return None

    # To use dans handle_join
    def save_last_channel(self, client_socket, channel_name):
        self.clients[client_socket]["last_channel"] = channel_name

    # To use in handle_quit
    def remove_user_from_channels(self, client_socket):
        for channel_name, channel_info in self.channels.items():
            if client_socket in channel_info["clients"]:
                channel_info["clients"].remove(client_socket)

                # Broadcast to the channel
                quit_channel_message = f"{self.clients[client_socket]['nickname']} has left the channel {channel_name}!"
                self.broadcast_to_channel(channel_name, quit_channel_message, client_socket)


server = Server()
server.start()

"""
def display_clients(self, client_socket):
    message = "List of clients: \n"
    for client_id, client_info in self.clients.items():
        message += f"{client_id}: {client_info} \n"
    client_socket.send(message.encode())
    
def handle_list(self, client_socket):
    message = "List of channels: \n"
    for channel_name, channel_info in self.channels.items():
        message += f"{channel_name}: {channel_info} \n"
    client_socket.send(message.encode())
"""