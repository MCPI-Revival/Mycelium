# <img src="https://i.imgur.com/nUevR7C.png" width="48" height="48"/> Mycelium 

Mycelium is a low-level simple MCPE (v0.6.1) framework for creating a server.

## Simple Example Usage

```python
# This is a simple server that allows the client to connect and nothing else

from mycelium.server import Server
from mycelium.protocol import packets
from mycelium.utils import binTools
import struct

server = Server()

def send_chat_message(server, address, connection, message):
    message_packet = b"\x85" + struct.pack(">H", len(message)) + message.encode()    
    server.send_encapsulated(message_packet, address, 0, connection["sequence_order"])

@server.primeEvent(0x82)
def LoginPacket(rawdata, address, connection):
    packets.read_encapsulated(rawdata)
    data = packets.encapsulated["body"]
    
    # Username
    length = struct.unpack(">H", data[1:1 + 2])[0]
    connection["username"] = data[3:3 + length].decode()

    # LoginStatus
    LoginStatusPacket = b"\x83\x00\x00\x00\x00"
    server.send_encapsulated(LoginStatusPacket, address, 0)
    
    server.OPTIONS["entities"] += 1
    connection["entity_id"] = server.OPTIONS["entities"]

    connection["pos"] = [0, 4, 0]
    connection["yaw"] = 0
    connection["pitch"] = 0

    # StartGamePacket
    StartGamePacket = b"\x87"
    StartGamePacket += b"\x00\x00\x00\x00" # Seed
    StartGamePacket += b"\x00\x00\x00\x00" # Unknown
    StartGamePacket += b"\x00\x00\x00\x01" # Gamemode
    StartGamePacket += struct.pack(">l", server.OPTIONS["entities"]) # EntityID
    StartGamePacket += binTools.encode_pos([0, 4, 0]) #Position
    server.send_encapsulated(StartGamePacket, address, 0)

@server.primeEvent(0x84)
def ReadyPacket(data, address, connection):
    server.send_ack_queue(address)

    # Inform players
    message = f"{connection['username']} joined the game."
    send_chat_message(server, address, connection, message)
    print(f"[CHAT] {message}")

server.set_option("name", "MCCPP;Demo;Mycelium Server")
server.set_option("entities", 0)
server.set_option("debug", True)
server.run()
```

## Contributing
Pull requests are always welcome. 
If you have any ideas or issues submit them in the [issues tab](https://github.com/MCPI-Revival/Mycelium/issues) in GitHub!
