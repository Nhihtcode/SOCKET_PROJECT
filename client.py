import socket
import os
import sys

SERVER_HOST = "192.168.138.1"
SERVER_PORT = 12345
BUFFER_SIZE = 1024

def send_command(command):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        try:
            client_socket.settimeout(10)  # Thêm timeout cho client
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            client_socket.sendall(command.encode('utf-8'))

            if command.upper().startswith("UPLOAD "):
                response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                
                if response == "READY":
                    filename = command.split(" ", 1)[1].strip()
                    if not os.path.isfile(filename):
                        print(f"Error: File '{filename}' does not exist.")
                        return
                    
                    file_size = os.path.getsize(filename)
                    sent_bytes = 0

                    with open(filename, "rb") as f:
                        while chunk := f.read(BUFFER_SIZE):
                            client_socket.sendall(chunk)
                            sent_bytes += len(chunk)
                            progress = (sent_bytes / file_size) * 100
                            print(f"Uploading: {progress:.2f}%", end="\r", flush=True)

                    client_socket.sendall(b'EOF')
                    print("\nUpload completed.")
                    print(client_socket.recv(BUFFER_SIZE).decode('utf-8'))
                else:
                    print(f"Unexpected server response: {response}")

            elif command.upper().startswith("DOWNLOAD "):
                response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if response == "EXISTS":
                    file_size = int(client_socket.recv(BUFFER_SIZE).decode('utf-8'))  # Nhận kích thước file
                    received_size = 0
                    filename = command.split(" ", 1)[1].strip()

                    with open(f"downloaded_{filename}", "wb") as f:
                        while received_size < file_size:
                            data = client_socket.recv(BUFFER_SIZE)
                            if data == b'EOF':  # Kiểm tra tín hiệu EOF
                                break
                            to_write = min(file_size - received_size, len(data))  # Chỉ ghi phần cần thiết
                            f.write(data[:to_write])
                            received_size += to_write
                            print(f"Downloading: {received_size / file_size * 100:.2f}% (Received: {received_size} / {file_size} bytes)", end="\r")

                    if received_size == file_size:
                        print("\nDownload completed successfully.")
                    else:
                        print(f"\nError: Expected {file_size} bytes, but received {received_size} bytes.")
                else:
                    print(f"Error: {response}")

            else:
                response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                print("Server:", response)
        except socket.timeout:
            print("Timeout: No response from server.")
        except socket.error as e:
            print(f"Socket error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

def main():
    while True:
        try:
            command = input("Enter command (UPLOAD <file> / DOWNLOAD <file> / EXIT): ").strip()
            if command.upper() == "EXIT":
                print("Closing connection.")
                break
            elif command.upper().startswith("UPLOAD ") or command.upper().startswith("DOWNLOAD "):
                parts = command.split(" ", 1)
                if len(parts) < 2 or not parts[1].strip():
                    print("Error: File name required.")
                    continue
                send_command(command)
            else:
                send_command(command)
        except KeyboardInterrupt:
            print("\nConnection closed by user.")
            sys.exit()

if __name__ == "__main__":
    main()