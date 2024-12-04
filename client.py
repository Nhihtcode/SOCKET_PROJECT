import socket
import os
import sys

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 12345
BUFFER_SIZE = 1024

def send_command(command):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        try:
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            client_socket.sendall(command.encode('utf-8'))

            if command.upper().startswith("UPLOAD "):
                filename = command.split(" ", 1)[1].strip()
                if not os.path.isfile(filename):
                    print(f"Error: File '{filename}' does not exist.")
                    return
                
                # Đợi xác nhận từ server
                response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if response == "READY":
                    with open(filename, "rb") as f:
                        while chunk := f.read(BUFFER_SIZE):
                            client_socket.sendall(chunk)
                    client_socket.sendall(b'EOF')
                    print(client_socket.recv(BUFFER_SIZE).decode('utf-8'))
                else:
                    print(f"Error from server: {response}")

            elif command.upper().startswith("DOWNLOAD "):
                response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if response == "EXISTS":
                    filename = command.split(" ", 1)[1].strip()
                    with open(f"downloaded_{filename}", "wb") as f:
                        total_bytes = 0
                        while True:
                            data = client_socket.recv(BUFFER_SIZE)
                            if data.endswith(b'EOF'):  # Phát hiện EOF ở cuối
                                f.write(data[:-3])  # Bỏ EOF ra khỏi dữ liệu ghi vào tệp
                                break
                            f.write(data)
                            total_bytes += len(data)
                            print(f"Downloading: {total_bytes} bytes received", end="\r")
                    print("\nDownload completed.")
                else:
                    response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                    print(f"Error: {response}")
            else:
                response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                print("Server:", response)

        except socket.error as e:
            print(f"Connection error: {e}")
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
