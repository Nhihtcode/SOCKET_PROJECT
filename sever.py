import tkinter as tk
from tkinter import scrolledtext, messagebox
import socket
import threading
import os

BUFFER_SIZE = 1024
UPLOAD_DIR = "uploads"
server_running = False
server_socket = None
client_threads = []

def start_server_gui(host='0.0.0.0', port=12345):
    global server_running, server_socket
    if server_running:
        return

    def server_thread():
        global server_running
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR)

        try:
            server_socket.bind((host, port))
            server_socket.listen(5)
            log_message(f"Server started on {host}:{port}")
            server_running = True

            while server_running:
                try:
                    client_socket, addr = server_socket.accept()
                    log_message(f"Connection established with {addr}")
                    thread = threading.Thread(target=handle_client_gui, args=(client_socket, addr), daemon=True)
                    thread.start()
                    client_threads.append(thread)
                except Exception as e:
                    log_message(f"Error accepting client connection: {e}")
        except Exception as e:
            log_message(f"Server failed to start: {e}")
        finally:
            stop_server_gui()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    threading.Thread(target=server_thread, daemon=True).start()

def stop_server_gui():
    global server_running, server_socket, client_threads
    if not server_running:
        return
    server_running = False
    try:
        if server_socket:
            server_socket.close()
        log_message("Server stopped.")
    except Exception as e:
        log_message(f"Error stopping server: {e}")
    for thread in client_threads:
        thread.join()

def handle_client_gui(client_socket, address):
    try:
        while True:
            client_socket.settimeout(100)
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
        client_socket.close()

def handle_upload(client_socket, command):
    filename = command.split(" ", 1)[1].strip()
    if not filename:
        client_socket.sendall(b"ERROR: No filename provided")
        return

    sanitized_filename = sanitize_filename(filename)
    unique_filename = get_unique_filename(f"uploaded_{sanitized_filename}")
    client_socket.sendall(b"READY")

    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    try:
        with open(file_path, "wb") as f:
            while True:
                data = client_socket.recv(BUFFER_SIZE)
                if data == b'EOF':
                    break
                f.write(data)

        log_message(f"File uploaded: {unique_filename}")
        client_socket.sendall(f"Upload completed as {unique_filename}".encode('utf-8'))
    except Exception as e:
        log_message(f"Error during file upload: {e}")
        client_socket.sendall(b"ERROR: Upload failed")

def handle_download(client_socket, command):
    filename = command.split(" ", 1)[1].strip()
    filepath = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(filepath):
        try:
            file_size = os.path.getsize(filepath)
            client_socket.sendall(f"EXISTS {file_size}".encode('utf-8'))

            with open(filepath, "rb") as f:
                while chunk := f.read(BUFFER_SIZE):
                    client_socket.sendall(chunk)
            client_socket.sendall(b'EOF')
            log_message(f"File sent: {filename}")
        except Exception as e:
            log_message(f"Error during file download: {e}")
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

def log_message(message):
    log_box.insert(tk.END, f"{message}\n")
    log_box.see(tk.END)

def on_start():
    host = host_entry.get()
    port = int(port_entry.get())
    start_server_gui(host, port)

def on_stop():
    stop_server_gui()

# GUI Setup
root = tk.Tk()
root.title("Server GUI")
root.geometry("700x500")

frame = tk.Frame(root)
frame.pack(pady=10)

tk.Label(frame, text="HOST:").grid(row=0, column=0, padx=5)
host_entry = tk.Entry(frame, width=15)
host_entry.insert(0, "0.0.0.0")
host_entry.grid(row=0, column=1, padx=5)

tk.Label(frame, text="PORT:").grid(row=0, column=2, padx=5)
port_entry = tk.Entry(frame, width=5)
port_entry.insert(0, "12345")
port_entry.grid(row=0, column=3, padx=5)

start_button = tk.Button(frame, text="START SEVER", command=on_start)
start_button.grid(row=0, column=4, padx=5)

stop_button = tk.Button(frame, text="STOP SEVER", command=on_stop)
stop_button.grid(row=0, column=5, padx=5)

log_box = scrolledtext.ScrolledText(root, width=100, height=50, background="light grey")
log_box.pack(pady=10)

root.mainloop()