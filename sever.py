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
            client_socket.settimeout(10)  # Timeout cho kết nối
            try:
                command = client_socket.recv(BUFFER_SIZE).decode('utf-8').strip()
            except socket.timeout:
                print(f"Timeout occurred while waiting for client {address}.")
                break  # Kết thúc kết nối nếu hết thời gian chờ
            if not command:
                break  # Nếu không có lệnh nào gửi đến, thoát khỏi vòng lặp

            if command.upper().startswith("UPLOAD "):
                handle_upload(client_socket, command)

            elif command.upper().startswith("DOWNLOAD "):
                handle_download(client_socket, command)

            else:
                client_socket.sendall(b"ERROR: Invalid command")

    except Exception as e:
        print(f"Error from client {address}: {e}")
    finally:
        print(f"Closing connection from: {address}")
        client_socket.close()

def handle_upload(client_socket, command):
    filename = command.split(" ", 1)[1].strip()
    if not filename:
        client_socket.sendall(b"ERROR: No filename provided")
        return
    
    sanitized_filename = sanitize_filename(filename)
    unique_filename = get_unique_filename(f"uploaded_{sanitized_filename}")
    client_socket.sendall(b"READY")  # Phản hồi READY

    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    try:
        with open(file_path, "wb") as f:
            while True:
                data = client_socket.recv(BUFFER_SIZE)
                if data == b'EOF':
                    break
                f.write(data)

        print(f"File uploaded and saved as: {unique_filename}")
        client_socket.sendall(f"Upload completed as {unique_filename}".encode('utf-8'))
    except Exception as e:
        print(f"Error during file upload: {e}")
        client_socket.sendall(b"ERROR: Upload failed")

def handle_download(client_socket, command):
    filename = command.split(" ", 1)[1].strip()
    filepath = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(filepath):
        try:
            file_size = os.path.getsize(filepath)
            client_socket.sendall(b"EXISTS")
            client_socket.sendall(f"{file_size}".encode('utf-8'))  # Gửi kích thước file

            with open(filepath, "rb") as f:
                while chunk := f.read(BUFFER_SIZE):
                    client_socket.sendall(chunk)  # Gửi dữ liệu từng phần
            client_socket.sendall(b'EOF')  # Gửi tín hiệu EOF chỉ một lần
            print(f"File {filename} sent successfully.")
        except Exception as e:
            print(f"Error during download: {e}")
            client_socket.sendall(f"ERROR: {str(e)}".encode('utf-8'))
    else:
        client_socket.sendall(b"ERROR: File not found")

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
            try:
                client_socket, addr = server.accept()
                print(f"Connection established with {addr}")  # In log khi có kết nối
                threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True).start()
            except Exception as e:
                print(f"Error accepting client connection: {e}")

if __name__ == "__main__":
    start_server()