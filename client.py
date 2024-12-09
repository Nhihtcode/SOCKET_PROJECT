import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import socket
import os

SERVER_HOST = "10.0.143.9"
SERVER_PORT = 12345
BUFFER_SIZE = 1024

def send_command(command, file_path=None):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.settimeout(10)
            status_log.insert(tk.END, f"Attempting to connect to {SERVER_HOST}:{SERVER_PORT}...\n")
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            status_log.insert(tk.END, "Connected to server.\n")
            client_socket.sendall(command.encode('utf-8'))

            if command.upper().startswith("UPLOAD "):
                response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if response == "READY" and file_path:
                    file_size = os.path.getsize(file_path)
                    sent_bytes = 0

                    with open(file_path, "rb") as f:
                        while chunk := f.read(BUFFER_SIZE):
                            client_socket.sendall(chunk)
                            sent_bytes += len(chunk)
                            progress = (sent_bytes / file_size) * 100
                            progress_label.config(text=f"Uploading: {progress:.2f}%")
                            root.update_idletasks()

                    client_socket.sendall(b'EOF')
                    status_log.insert(tk.END, "Upload completed.\n")
                else:
                    status_log.insert(tk.END, f"Unexpected server response: {response}\n")

            elif command.upper().startswith("DOWNLOAD "):
                response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if response.startswith("EXISTS"):
                    file_size = int(response.split(" ")[1])
                    filename = command.split(" ", 1)[1].strip()
                    save_path = filedialog.asksaveasfilename(defaultextension="", initialfile=f"downloaded_{filename}")
                    
                    if not save_path:
                        status_log.insert(tk.END, "Download canceled by user.\n")
                        return

                    with open(save_path, "wb") as f:
                        received_size = 0
                        while received_size < file_size:
                            data = client_socket.recv(BUFFER_SIZE)
                            if data == b'EOF':
                                break
                            f.write(data)
                            received_size += len(data)
                            progress_label.config(text=f"Downloading: {received_size / file_size * 100:.2f}%")
                            root.update_idletasks()

                    status_log.insert(tk.END, "Download completed.\n")
                else:
                    status_log.insert(tk.END, f"Error: {response}\n")
            else:
                response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                status_log.insert(tk.END, f"Server: {response}\n")
    except socket.timeout:
        status_log.insert(tk.END, "Timeout: No response from server.\n")
    except socket.error as e:
        status_log.insert(tk.END, f"Socket error: {e}\n")
    except Exception as e:
        status_log.insert(tk.END, f"Unexpected error: {e}\n")

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

# GUI setup
root = tk.Tk()
root.title("File Client")
root.geometry("700x500")

upload_button = tk.Button(root, text="Upload File", command=upload_file, width=20)
upload_button.pack(pady=10)

tk.Label(root, text="Enter filename to download:").pack()
download_entry = tk.Entry(root, width=40)
download_entry.pack(pady=5)

download_button = tk.Button(root, text="Download File", command=download_file, width=20)
download_button.pack(pady=10)

progress_label = tk.Label(root, text="Status: Ready", fg="blue")
progress_label.pack(pady=5)

status_log = scrolledtext.ScrolledText(root, width=80, height=35, background="light grey")
status_log.pack(pady=10)

root.mainloop()