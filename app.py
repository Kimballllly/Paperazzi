from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit
import os
import mysql.connector
import fitz  # PyMuPDF for PDF processing
from docx import Document  # For handling Word documents
import subprocess
import qrcode

# Flask application setup
app = Flask(__name__)
socketio = SocketIO(app)

# Database configuration
db_config = {
    'host': os.getenv('DB_HOST', 'your-db-host'),
    'user': os.getenv('DB_USER', 'your-db-user'),
    'password': os.getenv('DB_PASSWORD', 'your-db-password'),
    'database': os.getenv('DB_NAME', 'your-db-name')
}

# Allowed file extensions
ALLOWED_EXTENSIONS = {'doc', 'docx', 'pdf'}

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to calculate total pages
def get_total_pages(file_path):
    try:
        if file_path.lower().endswith('.pdf'):  # For PDFs
            with fitz.open(file_path) as pdf:
                return pdf.page_count

        elif file_path.lower().endswith(('.doc', '.docx')):  # For Word documents
            doc = Document(file_path)
            total_characters = sum(len(p.text) for p in doc.paragraphs)
            average_chars_per_page = 1500
            return max(1, total_characters // average_chars_per_page)

        return "N/A"
    except Exception as e:
        print(f"Error processing file: {e}")
        return None

# Function to get database connection
def get_db_connection():
    if not hasattr(app, 'db_connection') or not app.db_connection.is_connected():
        app.db_connection = mysql.connector.connect(**db_config)
        app.db_cursor = app.db_connection.cursor(dictionary=True)
    return app.db_connection, app.db_cursor

# Ensure 'uploads' directory exists
if not os.path.exists('uploads'):
    os.makedirs('uploads')

# Route: Home page
@app.route('/')
def index():
    return render_template('index.html')

# Route: File upload
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']
    
    if file and allowed_file(file.filename):
        filename = file.filename
        file_path = os.path.join('uploads', filename)
        file.save(file_path)

        file_size = os.path.getsize(file_path)
        total_pages = get_total_pages(file_path)

        if total_pages is None:
            os.remove(file_path)
            return "Error processing the file.", 500

        try:
            db_connection, db_cursor = get_db_connection()

            # Insert the file into database
            query = """
                INSERT INTO print_jobs (document_name, document_size, file_data, status, total_pages)
                VALUES (%s, %s, %s, %s, %s)
            """
            with open(file_path, 'rb') as f:
                file_data = f.read()
            db_cursor.execute(query, (filename, file_size, file_data, 'uploaded', total_pages))
            db_connection.commit()

            # Notify the kiosk in real-time
            socketio.emit('file_uploaded', {'document_name': filename, 'total_pages': total_pages})

            # Optionally launch `printingoptions.py`
            subprocess.Popen(['python', 'printingoptions.py'])

            return render_template('uploaded_file.html', filename=filename, file_size=file_size, total_pages=total_pages)
        except mysql.connector.Error as err:
            print(f"Database Error: {err}")
            return f"Database Error: {err}", 500
        finally:
            os.remove(file_path)

    return "Invalid file type. Please upload a .doc, .docx, or .pdf file."

# Route: Generate QR Code for Wi-Fi
@app.route('/generate_wifi_qr')
def generate_wifi_qr():
    ssid = "YourSSID"
    password = "YourPassword"

    wifi_config = f"WIFI:S:{ssid};T:WPA;P:{password};;"
    qr = qrcode.QRCode()
    qr.add_data(wifi_config)
    qr.make(fit=True)

    img = qr.make_image(fill="black", back_color="white")
    qr_code_path = os.path.join('static', 'wifi_qr_code.png')
    img.save(qr_code_path)
    
    return render_template('wifi_qr.html', qr_code_path=qr_code_path)

# Teardown: Close database connection
@app.teardown_appcontext
def close_db_connection(exception):
    if hasattr(app, 'db_connection') and app.db_connection.is_connected():
        app.db_cursor.close()
        app.db_connection.close()

# Run the Flask-SocketIO app
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
