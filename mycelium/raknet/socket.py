import socket, sys

def create_socket(address):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    
    try:
        sock.bind(address)
    except socket.error as e:
        print("Failed to bind!")
        print(str(e))
    except KeyboardInterrupt:
            sys.exit()
    else:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    return sock
       
def receive_buffer(sock):
    try:
        return sock.recvfrom(65535)
    except:
        pass
          
def send_buffer(sock, buffer, address):
    return sock.sendto(buffer, address)
     
def close_socket(sock):
    sock.close()
