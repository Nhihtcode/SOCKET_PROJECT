import socket
import threading
import os

BUFFER_SIZE = 1024
UPLOAD_DIR = "uploads"
clients = []

def handle_client(client_socket, address):
    print(f"Connection established with {address}")
    clients.append(client_socket)
    try:
        while True:
            data = client_socket.recv(BUFFER_SIZE)
            if not data:
                break
            command = data.decode('utf-8')
            if command.upper().startswith("UPLOAD "):
                filename = command.split(" ", 1)[1]
                unique_filename = get_unique_filename(filename)
                with open(os.path.join(UPLOAD_DIR, unique_filename), "wb") as f:
                    while True:
                        data = client_socket.recv(BUFFER_SIZE)
                        if data == b'EOF':
                            break
                        f.write(data)
                client_socket.sendall(b"Upload completed")

            elif command.upper().startswith("DOWNLOAD "):
                filename = command.split(" ", 1)[1]
                filepath = os.path.join(UPLOAD_DIR, filename)
                if os.path.exists(filepath):
                    client_socket.sendall(b"EXISTS")
                    with open(filepath, "rb") as f:
                        while chunk := f.read(BUFFER_SIZE):
                            client_socket.sendall(chunk)
                    client_socket.sendall(b'EOF')
                else:
                    client_socket.sendall(b"ERROR: File not found")

            else:
                client_socket.sendall(b"ERROR: Invalid command")
    except Exception as e:
        print(f"Error from client {address}: {e}")
    finally:
        print(f"Closing connection from: {address}")
        clients.remove(client_socket)
        client_socket.close()

def get_unique_filename(filename):
    base, ext = os.path.splitext(filename)
    counter = 1
    unique_filename = filename
    while os.path.exists(os.path.join(UPLOAD_DIR, unique_filename)):
        unique_filename = f"{base}_{counter}{ext}"
        counter += 1
    return unique_filename

def start_server(host='0.0.0.0', port=12345):
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)
    print(f"Server is listening on {host}:{port}")

    while True:
        client_socket, addr = server.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
        client_thread.start()

if __name__ == "__main__":
    start_server()