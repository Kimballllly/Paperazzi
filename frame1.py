import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import socketio
import mysql.connector
import subprocess

# SocketIO Configuration
SOCKETIO_SERVER = "https://paperazzi.onrender.com"
socketio_client = socketio.Client()

# Global variables
root = None
job_labels = {}

# Function to close the application
def close_application(event=None):
    root.quit()

# Function to transition to Wi-Fi screen
def go_to_wifi():
    """Transition to the Wi-Fi printing screen."""
    main_frame.pack_forget()  # Hide the main frame
    wifi_frame.pack(pady=20)  # Show the Wi-Fi frame

# Function to return to the home screen
def return_home():
    """Return to the welcome screen."""
    wifi_frame.pack_forget()
    main_frame.pack(pady=20)

# Function to show a full-screen transition screen
def show_transition_screen():
    """Display a full-screen transition screen to cover the desktop."""
    transition_frame = tk.Frame(root, bg="white")
    transition_frame.pack(fill="both", expand=True)

    # Display a loading message or logo
    loading_label = tk.Label(
        transition_frame,
        text="Preparing your print job...",
        font=("Bebas Neue", 50),
        bg="white",
        fg="black"
    )
    loading_label.pack(expand=True)

    # Prevent user from closing this screen accidentally
    root.update_idletasks()  # Ensure the GUI updates immediately

    # Launch the printing process after a brief delay
    root.after(2000, lambda: launch_printingoptions(transition_frame))

# Function to launch printingoptions.py and keep the transition frame
def launch_printingoptions(transition_frame):
    try:
        # Launch the external script
        subprocess.Popen([
            "python3",  # Or "python" depending on your setup
            "printingoptions.py",
            file_name,
            file_path,
            str(total_pages),
            str(job_id)
        ])
        # Keep the transition frame visible while the current app quits
        transition_frame.tkraise()  # Ensure the frame is on top
        root.quit()  # Close the main application window
    except Exception as e:
        print(f"Failed to launch printingoptions.py: {e}")

# Database connection function
def connect_to_database():
    try:
        connection = mysql.connector.connect(
            host="paperazzi.cre40o0wmfru.ap-southeast-2.rds.amazonaws.com",
            user="admin",
            password="paperazzi",
            database="paperazzi"
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

# SocketIO listeners
@socketio_client.on('connect')
def on_connect():
    print("Successfully connected to the server.")

@socketio_client.on('disconnect')
def on_disconnect():
    print("Disconnected from the server.")

@socketio_client.on('file_uploaded')
def on_file_uploaded(data):
    """Handles the event when a file is uploaded on the website."""
    global file_name, file_path, total_pages, job_id

    file_name = data.get('file_name')
    file_path = data.get('file_path')
    total_pages = data.get('total_pages')
    job_id = data.get('job_id')

    if not all([file_name, file_path, total_pages, job_id]):
        print("Error: Missing file upload data.")
        return

    print(f"File uploaded: {file_name}, Path: {file_path}, Pages: {total_pages}")
    show_transition_screen()  # Trigger the transition screen before quitting

@socketio_client.on('file_status_update')
def on_status_update(data):
    """Handles status updates from the server."""
    document_name = data.get('document_name')
    status = data.get('status')

    print(f"Received update for {document_name}: {status}")

    if document_name not in job_labels:
        job_labels[document_name] = tk.Label(
            job_frame, 
            text=f"{document_name} - {status.upper()}", 
            font=("Bebas Neue", 16)
        )
        job_labels[document_name].pack(pady=5)
    else:
        job_labels[document_name].config(text=f"{document_name} - {status.upper()}")

# Create the main application window
root = tk.Tk()
root.title("Paperazzi")
root.config(bg="white")
root.attributes('-fullscreen', True)
root.bind("<Escape>", close_application)  # Bind Escape to close the app

# Main frame (Welcome screen)
main_frame = tk.Frame(root, bg="white")
main_frame.pack()

# Logo display
logo_frame = tk.Frame(main_frame, bg="white")
logo_frame.pack(pady=(50, 10))
try:
    logo_image = Image.open("logo.jpg")  # Ensure logo.jpg is in the same directory
    logo_photo = ImageTk.PhotoImage(logo_image)
    logo_label = tk.Label(logo_frame, image=logo_photo, bg="white")
    logo_label.pack()
except Exception as e:
    print(f"Error loading logo: {e}")

# Start printing button
start_button_frame = tk.Frame(main_frame, bg="white")
start_button_frame.pack(pady=40)  # Increased padding at the top

def on_hover(event):
    start_button.config(bg="#d12246", fg="white", relief=tk.RAISED)

def on_leave(event):
    start_button.config(bg="#fd2854", fg="white", relief=tk.FLAT)  # Updated text color to white

start_button = tk.Button(
    start_button_frame,
    text="Start Printing",
    font=("Bebas Neue", 50),
    bg="#fd2854",
    fg="white",
    activebackground="#d12246",
    activeforeground="white",
    relief=tk.FLAT,
    bd=0,
    padx=30,
    pady=20,
    command=go_to_wifi
)

start_button.bind("<Enter>", on_hover)
start_button.bind("<Leave>", on_leave)
start_button.pack(pady=10)

# Wi-Fi frame setup
wifi_frame = tk.Frame(root, bg="white")
wifi_inner_frame = tk.Frame(wifi_frame, bg="white")
wifi_inner_frame.pack(expand=True, fill="both", pady=(50, 0))

wifi_instruction_label = tk.Label(
    wifi_inner_frame, text="Connect to Wi-Fi and scan the QR code:", font=("Bebas Neue", 36), bg="white", fg="black"
)
wifi_instruction_label.pack(pady=10)

# QR code for Wi-Fi printing
try:
    qr_image = Image.open("qr_code.png").resize((600, 600))
    qr_photo = ImageTk.PhotoImage(qr_image)
    qr_label = tk.Label(wifi_inner_frame, image=qr_photo, bg="white")
    qr_label.pack(pady=10)
except Exception as e:
    print(f"Error loading QR code: {e}")

website_link_label = tk.Label(
    wifi_inner_frame, text="or visit https://paperazzi.onrender.com", font=("Bebas Neue", 14), bg="white", fg="blue"
)
website_link_label.pack(pady=5)

# Real-time Status Area
job_frame = tk.Frame(wifi_frame, bg="white")
job_frame.pack(pady=10)

status_label = tk.Label(
    wifi_frame, text="Waiting for files...", font=("Bebas Neue", 20), bg="white"
)
status_label.pack(pady=10)

# Start the SocketIO listener
try:
    socketio_client.connect(SOCKETIO_SERVER)
except Exception as e:
    print(f"Failed to connect to SocketIO server: {e}")

# Start the GUI application
root.mainloop()
