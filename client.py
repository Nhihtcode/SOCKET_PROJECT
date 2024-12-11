import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
import socket
import os

SERVER_HOST = "10.0.143.9"
SERVER_PORT = 12345
BUFFER_SIZE = 1024
CLIENT_PIN = "1234"  # Mã PIN mặc định của máy khách

def send_command(command, file_path=None):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.settimeout(10)
            log_box.insert(tk.END, f"Attempting to connect to {SERVER_HOST}:{SERVER_PORT}...\n")
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            log_box.insert(tk.END, "Connected to server.\n")

            # Bước 1: Xác thực mã PIN
            response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
            if response == "AUTH_REQUIRED":
                client_socket.sendall(CLIENT_PIN.encode('utf-8'))
                auth_response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if auth_response != "AUTH_SUCCESS":
                    log_box.insert(tk.END, "Authentication failed.\n")
                    return
                log_box.insert(tk.END, "Authentication successful.\n")

            # Bước 2: Gửi lệnh (upload/download)
            client_socket.sendall(command.encode('utf-8'))

            if command.upper().startswith("UPLOAD "):
                response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if response == "READY" and file_path:
                    file_size = os.path.getsize(file_path)
                    sent_bytes = 0
                    progress_bar["maximum"] = file_size

                    with open(file_path, "rb") as f:
                        while chunk := f.read(BUFFER_SIZE):
                            client_socket.sendall(chunk)
                            sent_bytes += len(chunk)
                            progress = (sent_bytes / file_size) * 100
                            progress_label.config(text=f"Uploading: {progress:.2f}%")
                            progress_bar["value"] = sent_bytes
                            root.update_idletasks()

                    client_socket.sendall(b'EOF')
                    log_box.insert(tk.END, "Upload completed.\n")
                else:
                    log_box.insert(tk.END, f"Unexpected server response: {response}\n")

            elif command.upper().startswith("DOWNLOAD "):
                response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if response.startswith("EXISTS"):
                    file_size = int(response.split(" ")[1])
                    filename = command.split(" ", 1)[1].strip()
                    save_path = filedialog.asksaveasfilename(defaultextension="", initialfile=f"downloaded_{filename}")
                    
                    if not save_path:
                        log_box.insert(tk.END, "Download canceled by user.\n")
                        return

                    with open(save_path, "wb") as f:
                        received_size = 0
                        progress_bar["maximum"] = file_size
                        while received_size < file_size:
                            data = client_socket.recv(BUFFER_SIZE)
                            if data == b'EOF':
                                break
                            f.write(data)
                            received_size += len(data)
                            progress = (received_size / file_size) * 100
                            progress_label.config(text=f"Downloading: {progress:.2f}%")
                            progress_bar["value"] = received_size
                            root.update_idletasks()

                    log_box.insert(tk.END, "Download completed.\n")
                else:
                    log_box.insert(tk.END, f"Error: {response}\n")
            else:
                response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                log_box.insert(tk.END, f"Server: {response}\n")
    except socket.timeout:
        log_box.insert(tk.END, "Timeout: No response from server.\n")
    except socket.error as e:
        log_box.insert(tk.END, f"Socket error: {e}\n")
    except Exception as e:
        log_box.insert(tk.END, f"Unexpected error: {e}\n")

def upload_file():
    file_path = filedialog.askopenfilename(title="Select File")
    if file_path:
        filename = os.path.basename(file_path)
        send_command(f"UPLOAD {filename}", file_path)

def download_file():
    filename = download_entry.get().strip()
    if filename:
        send_command(f"DOWNLOAD {filename}")
    else:
        messagebox.showwarning("Input Error", "Please enter a file name to download.")

def set_client_pin():
    global CLIENT_PIN
    new_pin = pin_entry.get().strip()
    if new_pin == CLIENT_PIN:  # Kiểm tra mã PIN
        pin_window.destroy()  # Đóng cửa sổ mã PIN
        show_client_gui()  # Hiển thị giao diện client
    else:
        messagebox.showwarning("Invalid PIN", "Incorrect PIN. Please try again.")

def show_client_gui():
    # Tạo cửa sổ chính client sau khi nhập mã PIN thành công
    global root, log_box, progress_bar, progress_label, upload_button, download_button, download_entry
    root = tk.Tk()
    root.title("Client GUI")
    root.geometry("800x600")

    # Khung điều khiển
    control_frame = tk.LabelFrame(root, text="Chức năng", padx=10, pady=10)
    control_frame.pack(pady=10, fill="x")

    upload_button = ttk.Button(control_frame, text="Tải lên", command=upload_file)
    upload_button.grid(row=0, column=0, padx=5)

    download_label = tk.Label(control_frame, text="Tên tệp tải xuống:")
    download_label.grid(row=0, column=1, padx=5)

    download_entry = ttk.Entry(control_frame, width=30)
    download_entry.grid(row=0, column=2, padx=5)

    download_button = ttk.Button(control_frame, text="Tải xuống", command=download_file)
    download_button.grid(row=0, column=3, padx=5)

    # Thanh tiến trình
    progress_frame = tk.Frame(root)
    progress_frame.pack(pady=10, fill="x")

    progress_label = tk.Label(progress_frame, text="Tiến trình: Đang chờ", anchor="w")
    progress_label.pack(fill="x")

    progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=100, mode="determinate")
    progress_bar.pack(fill="x", padx=10)

    # Khung nhật ký
    log_frame = tk.LabelFrame(root, text="Nhật ký hoạt động", padx=10, pady=10)
    log_frame.pack(pady=10, fill="both", expand=True)

    log_box = scrolledtext.ScrolledText(log_frame, wrap="word", height=20)  # This is where log_box is initialized
    log_box.pack(fill="both", expand=True, padx=5, pady=5)

    root.mainloop()

# Tạo cửa sổ nhập mã PIN
def create_pin_window():
    global pin_window, pin_entry
    pin_window = tk.Toplevel()
    pin_window.title("Nhập Mã PIN")
    pin_window.geometry("300x150")

    tk.Label(pin_window, text="Nhập mã PIN của client:").pack(pady=10)
    pin_entry = tk.Entry(pin_window, show="*", width=20)
    pin_entry.pack(pady=5)

    set_pin_button = tk.Button(pin_window, text="Đặt PIN", command=set_client_pin)
    set_pin_button.pack(pady=10)

    pin_window.mainloop()

# Khởi tạo cửa sổ nhập mã PIN
create_pin_window()