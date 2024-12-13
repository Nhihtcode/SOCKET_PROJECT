import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import socket
import threading
import os

# Cấu hình server
BUFFER_SIZE = 1024               # Kích thước bộ đệm khi nhận/gửi dữ liệu
UPLOAD_DIR = "uploads"           # Thư mục lưu trữ file tải lên
SERVER_PIN = "1234"              # Mã PIN của server để xác thực
server_running = False           # Trạng thái chạy của server
server_socket = None             # Socket chính của server
client_threads = []              # Danh sách các luồng (threads) đang xử lý client

# Hàm khởi động giao diện server
def start_server_gui(host='0.0.0.0', port=12345):
    global server_running, server_socket
    if server_running:      # Nếu server đã đang chạy, không cần khởi động lại
        return

    # Hàm xử lý server
    def server_thread():
        global server_running
        # Tạo thư mục lưu trữ file tải lên nếu chưa tồn tại
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR)

        try:
            # Khởi tạo server socket
            server_socket.bind((host, port))
            server_socket.listen(5)
            log_message(f"Server started on {host}:{port}")
            server_running = True

            while server_running:
                try:
                    # Chấp nhận kết nối từ client
                    client_socket, addr = server_socket.accept()
                    log_message(f"Connection established with {addr}")
                    # Tạo một luồng (thread) để xử lý client
                    thread = threading.Thread(target=handle_client_gui, args=(client_socket, addr), daemon=True)
                    thread.start()
                    client_threads.append(thread) # Thêm luồng vào danh sách
                except Exception as e:
                    log_message(f"Error accepting client connection: {e}")
        except Exception as e:
            log_message(f"Server failed to start: {e}")
        finally:
            # Đóng tất cả các kết nối khi server dừng
            stop_server_gui()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    threading.Thread(target=server_thread, daemon=True).start()

# Hàm dừng server
def stop_server_gui():
    global server_running, server_socket, client_threads
    if not server_running:
        return
    server_running = False              # Dừng server
    try:
        if server_socket:
            server_socket.close()       # Đóng socket chính của server
        log_message("Server stopped.")
    except Exception as e:
        log_message(f"Error stopping server: {e}")
    for thread in client_threads:
        thread.join()                   # Đợi tất cả các luồng xử lý client dừng

# Hàm xử lý client
def handle_client_gui(client_socket, address):
    try:
        # Step 1: Xác thực client
        client_socket.sendall(b"AUTH_REQUIRED")         # Yêu cầu client xác thực
        client_pin = client_socket.recv(BUFFER_SIZE).decode('utf-8').strip()
        if client_pin != SERVER_PIN:                   # Kiểm tra mã PIN
            log_message(f"Authentication failed for {address}")
            client_socket.sendall(b"ERROR: Authentication failed")
            client_socket.close()
            return
        
        log_message(f"Client {address} authenticated successfully")
        client_socket.sendall(b"AUTH_SUCCESS")         # Gửi thông báo xác thực thành công

        # Step 2: Xử lý các yêu cầu từ client
        while True:
            client_socket.settimeout(100)               # Đặt thời gian chờ cho client
            try:
                command = client_socket.recv(BUFFER_SIZE).decode('utf-8').strip()
            except socket.timeout:
                log_message(f"Timeout occurred while waiting for client {address}")
                break
            except (socket.timeout, socket.error) as e:
                log_message(f"Connection error: {e}")
                break
            if not command:
                break

            # Phân loại lệnh: UPLOAD hoặc DOWNLOAD
            if command.upper().startswith("UPLOAD "):
                handle_upload(client_socket, command)
            elif command.upper().startswith("DOWNLOAD "):
                handle_download(client_socket, command)
            else:
                client_socket.sendall(b"ERROR: Invalid command")
    except Exception as e:
        log_message(f"Error from client {address}: {e}")
    finally:
        log_message(f"Closing connection with {address}")
        client_socket.close()                       # Đóng kết nối với client

# Hàm xử lý lệnh UPLOAD
def handle_upload(client_socket, command):
    filename = command.split(" ", 1)[1].strip()
    if not filename:
        client_socket.sendall(b"ERROR: No filename provided")
        return

    sanitized_filename = sanitize_filename(filename)                # Làm sạch tên file
    unique_filename = get_unique_filename(f"uploaded_{sanitized_filename}")
    client_socket.sendall(b"READY")                                # Gửi tín hiệu sẵn sàng

    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    try:
        with open(file_path, "wb") as f:
            while True:
                data = client_socket.recv(BUFFER_SIZE)
                if data == b'EOF':                                      # Kết thúc file
                    break
                f.write(data)                                          # Ghi dữ liệu vào file

        log_message(f"File uploaded: {unique_filename}")
        client_socket.sendall(f"Upload completed as {unique_filename}".encode('utf-8'))
    except Exception as e:
        log_message(f"Error during file upload: {e}")
        client_socket.sendall(b"ERROR: Upload failed")

# Hàm xử lý lệnh DOWNLOAD
def handle_download(client_socket, command):
    filename = command.split(" ", 1)[1].strip()
    filepath = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(filepath):
        try:
            file_size = os.path.getsize(filepath)
            client_socket.sendall(f"EXISTS {file_size}".encode('utf-8'))           # Gửi thông báo file tồn tại

            with open(filepath, "rb") as f:
                while chunk := f.read(BUFFER_SIZE):
                    client_socket.sendall(chunk)                                    # Gửi dữ liệu file cho client
            client_socket.sendall(b'EOF')                                           # Kết thúc file
            log_message(f"File sent: {filename}")
        except Exception as e:
            log_message(f"Error during file download: {e}")
            client_socket.sendall(f"ERROR: {str(e)}".encode('utf-8'))
    else:
        client_socket.sendall(b"ERROR: File not found")                             # Gửi thông báo lỗi file không tồn tại

# Hàm làm sạch tên file
def sanitize_filename(filename):
    filename = os.path.basename(filename.replace("\\", "/").strip())
    return filename.replace(" ", "_")

# Hàm tạo tên file không trùng lặp
def get_unique_filename(filename):
    base, ext = os.path.splitext(filename)
    counter = 1
    unique_filename = filename
    while os.path.exists(os.path.join(UPLOAD_DIR, unique_filename)):
        unique_filename = f"{base}_{counter}{ext}"
        counter += 1
    return unique_filename

# Ghi nhật ký hoạt động vào giao diện
def log_message(message):
    log_box.insert(tk.END, f"{message}\n")
    log_box.see(tk.END)

# Hàm khởi động server từ giao diện
def on_start():
    host = host_entry.get()
    port = int(port_entry.get())
    start_server_gui(host, port)

# Hàm dừng server từ giao diện
def on_stop():
    stop_server_gui()

# Tạo cửa sổ chính
root = tk.Tk()
root.title("Server GUI")
root.geometry("1000x800")

# Khung cấu hình
frame_config = tk.LabelFrame(root, text="Cài đặt Server", padx=10, pady=10)
frame_config.pack(pady=10, fill="x")

tk.Label(frame_config, text="Host:").grid(row=0, column=0, padx=5)
host_entry = tk.Entry(frame_config, width=20)
host_entry.insert(0, "0.0.0.0")
host_entry.grid(row=0, column=1, padx=5)

tk.Label(frame_config, text="Port:").grid(row=0, column=2, padx=5)
port_entry = tk.Entry(frame_config, width=10)
port_entry.insert(0, "12345")
port_entry.grid(row=0, column=3, padx=5)

start_button = ttk.Button(frame_config, text="Bật Server", command=start_server_gui)
start_button.grid(row=0, column=4, padx=5)

stop_button = ttk.Button(frame_config, text="Tắt Server", command=stop_server_gui)
stop_button.grid(row=0, column=5, padx=5)

# Khung nhật ký
log_frame = tk.LabelFrame(root, text="Nhật ký hoạt động", padx=10, pady=10)
log_frame.pack(pady=10, fill="both", expand=True)

log_box = scrolledtext.ScrolledText(log_frame, wrap="word", height=20)
log_box.pack(fill="both", expand=True, padx=5, pady=5)

root.mainloop()