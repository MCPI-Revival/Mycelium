from mycelium.server import Server
from mycelium.protocol import packets
from mycelium.utils import binTools
import struct, sys, os

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
    
    # AddPlayerPacket
    AddPlayerPacket = b"\x89" 
    AddPlayerPacket += struct.pack(">H", len(connection['username']))
    AddPlayerPacket += connection['username'].encode()
    AddPlayerPacket += struct.pack(">i", connection["entity_id"])
    AddPlayerPacket += struct.pack(">f", connection["pos"][0])
    AddPlayerPacket += struct.pack(">f", connection["pos"][1])
    AddPlayerPacket += struct.pack(">f", connection["pos"][2])
    AddPlayerPacket += bytes([connection["yaw"]])
    AddPlayerPacket += bytes([connection["pitch"]])
    AddPlayerPacket += b"\x00" * 4      # 2 shorts
    AddPlayerPacket += b"\xFF"
    server.broadcast_encapsulated(AddPlayerPacket, address, 0, [connection])

    # Inform players
    message = f"{connection['username']} joined the game."
    send_chat_message(server, address, connection, message)
    print(f"[CHAT] {message}")

@server.primeEvent(0x94)
def MovePlayerEvent(rawdata, address, connection):
    packets.read_encapsulated(rawdata)
    data = packets.encapsulated["body"]

    server.send_ack_queue(address)

    connection["pos"] = binTools.decode_pos(data[5:5 + 12])
    connection["yaw"] = struct.unpack(">f", data[17:17 + 4])[0]
    connection["pitch"] = struct.unpack(">f", data["body"][21:21 + 4])[0]

    server.broadcast_encapsulated(rawdata, 0)


server.set_option("name", "MCCPP;Demo;Mycelium Server")
server.set_option("entities", 0)
server.set_option("debug", True)
server.run()