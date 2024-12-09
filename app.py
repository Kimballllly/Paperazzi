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

# Database configuration (these should be updated to your actual database credentials)
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'password'),
    'database': os.getenv('DB_NAME', 'paperazzi')
}

# Allowed file extensions
ALLOWED_EXTENSIONS = {'doc', 'docx', 'pdf'}

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to calculate total pages for PDF and Word documents
def get_total_pages(file_path):
    try:
        if file_path.lower().endswith('.pdf'):  # For PDFs
            with fitz.open(file_path) as pdf:
                return pdf.page_count

        elif file_path.lower().endswith(('.doc', '.docx')):  # For Word documents
            doc = Document(file_path)
            total_characters = sum(len(p.text) for p in doc.paragraphs)
            average_chars_per_page = 1500  # Average characters per page (can be adjusted)
            return max(1, total_characters // average_chars_per_page)

        return "N/A"
    except Exception as e:
        print(f"Error processing file: {e}")
        return None

# Function to get a connection to the database
def get_db_connection():
    if not hasattr(app, 'db_connection') or not app.db_connection.is_connected():
        app.db_connection = mysql.connector.connect(**db_config)
        app.db_cursor = app.db_connection.cursor(dictionary=True)
    return app.db_connection, app.db_cursor

# Ensure 'uploads' directory exists to store temporary files
if not os.path.exists('uploads'):
    os.makedirs('uploads')

# 🏠 **Route: Home Page**
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = file.filename
        file_path = os.path.join('uploads', filename)
        file.save(file_path)

        total_pages = get_total_pages(file_path)
        if total_pages is None:
            os.remove(file_path)
            return "Error processing the file.", 500

        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            query = """
                INSERT INTO print_jobs (document_name, status, total_pages)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (filename, 'pending', total_pages))
            connection.commit()

            socketio.emit('file_status_update', {'document_name': filename, 'status': 'pending'})
            
            script_path = os.path.abspath("printingoptions.py")
            subprocess.Popen(['python', script_path])

            return render_template('uploaded_file.html', filename=filename, total_pages=total_pages)
        except Exception as e:
            print(f"Error: {e}")
            return "Internal error occurred.", 500
        finally:
            connection.close()

# 📡 **Route: Generate Wi-Fi QR Code**
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

# 🛠️ **Teardown: Close DB Connection**
@app.teardown_appcontext
def close_db_connection(exception):
    if hasattr(app, 'db_connection') and app.db_connection.is_connected():
        app.db_cursor.close()
        app.db_connection.close()

# 🔄 **SocketIO Event: Update File Status**
@socketio.on('update_status')
def update_status(data):
    document_name = data['document_name']
    status = data['status']

    db_connection, db_cursor = get_db_connection()
    
    query = """
        UPDATE print_jobs SET status = %s WHERE document_name = %s
    """
    db_cursor.execute(query, (status, document_name))
    db_connection.commit()

    socketio.emit('status_update', {'document_name': document_name, 'status': status})

#  **Run Flask Server**
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
