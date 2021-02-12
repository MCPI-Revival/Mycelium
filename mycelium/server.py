import os, struct, sys
from typing import Callable
from threading import Thread
from mycelium.types.context import Context
from mycelium.protocol import packets, handler
from mycelium.raknet import messages, reliability, socket

class Server(object):
    OPTIONS = {
        "name": "",
        "ip": "0.0.0.0",
        "port": 19132,
        "server_guid": struct.unpack(">q", os.urandom(8))[0],
        "debug": True,
        "accepted_raknet_protocols": [5]
    }

    EVENT_BEFORE = (lambda self, context, connection: None)
    EVENT_AFTER = (lambda self, context, connection: None)

    EVENTS = {

    }

    STATUS = {
        "connecting": 0,
        "connected": 1,
        "disconnecting": 2,
        "disconnected": 3
    }
    
    def __init__(self):
        self.socket = socket.create_socket((self.OPTIONS["ip"], self.OPTIONS["port"]))
        self.connections = {}
        self.socket_thread = None

        self.EVENTS[messages.ID_CONNECTION_REQUEST] = self.handle_connection_request
        self.EVENTS[messages.ID_NEW_CONNECTION] = self.handle_new_connection
        self.EVENTS[messages.ID_CONNECTION_CLOSED] = self.handle_connection_closed
        self.EVENTS[messages.ID_CONNECTED_PING] = self.handle_connected_ping

    def primeEvent(self, id: int):  
        def wrap(func: Callable):
            self.EVENTS[id] = func
        return wrap

    def onPacketReceived(self, func: Callable):
        self.EVENTS["before"] = func

    def afterPacketProcessed(self, func: Callable):
        self.EVENTS["processed"] = func
        
    def add_connection(self, addr, port):
        token = str(addr) + ":" + str(port)
        self.connections[token] = {
            "mtu_size": 0,
            "address": (addr, port),
            "connecton_state": self.STATUS["connecting"],
            "packets_queue": [],
            "sequence_order": 0
        }

    def remove_connection(self, addr, port):
        token = str(addr) + ":" + str(port)
        if token in self.connections:
            del self.connections[token]

    def get_connection(self, addr, port):
        token = str(addr) + ":" + str(port)
        if token in self.connections:
            return self.connections[token]
        else:
            return None

    def set_option(self, option, value):
        self.OPTIONS[option] = value

    def add_to_queue(self, data, address):
        connection = self.get_connection(address[0], address[1])
        connection["packets_queue"].append(data)
        if connection["sequence_order"] >= 16777216:
            connection["packets_queue"] = []
            connection["sequence_order"] = 0
        else:
            connection["sequence_order"] += 1

    def get_last_packet(self, address):
        connection = self.get_connection(address[0], address[1])
        queue = connection["packets_queue"]
        if len(queue) > 0:
            return queue[-1]
        else:
            return b""
        
    def send_ack_queue(self, address):
        connection = self.get_connection(address[0], address[1])
        packets.ack["packets"] = []
        packets.ack["packets"].append(connection["sequence_order"])
        socket.send_buffer(self.socket, packets.write_ack(), address)
        
    def send_encapsulated(self, data, address, reliability, reliable_frame_index = 0, sequenced_frame_index = 0, ordered_frame_index = 0, order_channel = 0, compound_size = 0, compound_id = 0, compound_index = 0):
        connection = self.get_connection(address[0], address[1])
        packets.encapsulated["body"] = data
        packets.encapsulated["flags"] = reliability
        packets.encapsulated["sequence_order"] = connection["sequence_order"]
        packets.encapsulated["reliable_frame_index"] = reliable_frame_index
        packets.encapsulated["sequenced_frame_index"] = sequenced_frame_index
        packets.encapsulated["order"]["ordered_frame_index"] = ordered_frame_index
        packets.encapsulated["order"]["order_channel"] = order_channel
        packets.encapsulated["fragment"]["compound_size"] = compound_size
        packets.encapsulated["fragment"]["compound_id"] = compound_id
        packets.encapsulated["fragment"]["index"] = compound_index
        packet = packets.write_encapsulated()
        socket.send_buffer(self.socket, packet, address)
        self.send_ack_queue(address)
        self.add_to_queue(packet, address)

    def broadcast_encapsulated(self, data, reliability, reliable_frame_index = 0, sequenced_frame_index = 0, ordered_frame_index = 0, order_channel = 0, compound_size = 0, compound_id = 0, compound_index = 0, ignore = []):
        for connection in self.connections.values():
            if not connection in ignore:
                self.send_encapsulated(data, connection["address"], reliability, reliable_frame_index = 0, sequenced_frame_index = 0, ordered_frame_index = 0, order_channel = 0, compound_size = 0, compound_id = 0, compound_index = 0)

    def packet_handler(self, data, address):
        id = data[0]

        connection = self.get_connection(address[0], address[1])
        if self.OPTIONS["debug"]: print(f"[RECIEVED] DATA_PACKET -> {hex(id)}")
        if connection != None:
            if id == messages.ID_NACK:
                packets.read_encapsulated(self.get_last_packet(address))
                packets.encapsulated["flags"] = 0
                packets.encapsulated["sequence_order"] = connection["sequence_order"]
                socket.send_buffer(packets.write_encapsulated(), address, self)

            elif id == messages.ID_ACK:
                pass

            else:
                self.send_ack_queue(address)
                packets.read_encapsulated(data)
                data_packet = packets.encapsulated["body"]
                id = data_packet[0]

                self.EVENT_BEFORE(Context(self, data), connection)
                
                for eventID, func in self.EVENTS.items():
                    if self.OPTIONS["debug"]: print(f"{hex(id)} -> {hex(eventID)}: {str(func)}")
                    if id == eventID:
                        func(Context(self, data), connection)
                        break
        
                self.EVENT_AFTER(Context(self, data), connection)

        elif id == messages.ID_UNCONNECTED_PING:
            socket.send_buffer(self.socket, handler.handle_unconnected_ping(data, self), address)

        elif id == messages.ID_UNCONNECTED_PING_OPEN_CONNECTIONS:
            socket.send_buffer(self.socket, handler.handle_unconnected_ping_open_connections(data, self), address)

        elif id == messages.ID_OPEN_CONNECTION_REQUEST_1:
            socket.send_buffer(self.socket, handler.handle_open_connection_request_1(data, self), address)

        elif id == messages.ID_OPEN_CONNECTION_REQUEST_2:
            socket.send_buffer(self.socket, handler.handle_open_connection_request_2(data, (address[0], address[1]), self), address)
            

    def handle_connection_request(self, context, connection):
        address = connection["address"]
        packets.read_encapsulated(context.raw_data)
        data_packet = packets.encapsulated["body"]

        buffer = handler.handle_connection_request(data_packet, connection)
        self.send_encapsulated(buffer, address, 0)

    def handle_new_connection(self, context, connection):
        packets.read_new_connection(packets.encapsulated["body"])
        connection["connecton_state"] = self.STATUS["connected"]

    def handle_connection_closed(self, context, connection):
        address = connection["address"]
        connection["connecton_state"] = self.STATUS["disconnecting"]
        self.remove_connection(address[0], address[1])
        connection["connecton_state"] = self.STATUS["disconnected"]

    def handle_connected_ping(self, context, connection):
        address = connection["address"]
        packets.read_encapsulated(context.raw_data)
        data_packet = packets.encapsulated["body"]

        buffer = handler.handle_connected_ping(data_packet)
        self.send_encapsulated(buffer, address, 0)

    def run(self):
        self.socket_thread = Thread(target = self._run, daemon = True)
        self.socket_thread.start()

    def _run(self):
        stopped = False
        while not stopped:
            try:
                recv = socket.receive_buffer(self.socket)
                if recv != None:
                    data, addr = recv
                    self.packet_handler(data, addr)
            except KeyboardInterrupt:
                stopped = True
