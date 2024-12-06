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
            command = client_socket.recv(BUFFER_SIZE).decode('utf-8').strip()
            if not command:
                break

            if command.upper().startswith("UPLOAD "):
                try:
                    original_filename = command.split(" ", 1)[1].strip()
                    if not original_filename:
                        client_socket.sendall(b"ERROR: No filename provided")
                        continue

                    sanitized_filename = sanitize_filename(original_filename)
                    unique_filename = get_unique_filename(f"uploaded_{sanitized_filename}")
                    
                    # Phản hồi "READY" trước khi nhận file
                    client_socket.sendall(b"READY")
                    
                    with open(os.path.join(UPLOAD_DIR, unique_filename), "wb") as f:
                        while True:
                            data = client_socket.recv(BUFFER_SIZE)
                            if data == b'EOF':
                                break
                            f.write(data)
                    print(f"File uploaded and saved as: {unique_filename}")
                    client_socket.sendall(f"Upload completed as {unique_filename}".encode('utf-8'))
                except Exception as e:
                    client_socket.sendall(f"ERROR: {str(e)}".encode())

            elif command.upper().startswith("DOWNLOAD "):
                try:
                    filename = command.split(" ", 1)[1].strip()
                except IndexError:
                    client_socket.sendall(b"ERROR: Invalid DOWNLOAD command")
                    continue

                filepath = os.path.join(UPLOAD_DIR, filename)
                if os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    client_socket.sendall(f"EXISTS {file_size}".encode('utf-8'))
                    print(f"Sending file: {filename} (size: {file_size} bytes)")

                    with open(filepath, "rb") as f:
                        while chunk := f.read(BUFFER_SIZE):
                            client_socket.sendall(chunk)
                            print(f"Sent chunk of size: {len(chunk)} bytes")

                    print("EOF signal sent")
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

def sanitize_filename(filename):
    filename = os.path.basename(filename.replace("\\", "/").strip())
    return filename.replace(" ", "_")

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

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((host, port))
        server.listen(5)
        print(f"Server is listening on {host}:{port}")

        while True:
            client_socket, addr = server.accept()
            threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()