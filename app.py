from flask import Flask, render_template, request, redirect, url_for
import os
import mysql.connector
import fitz  # PyMuPDF library for PDF processing

app = Flask(__name__)

# Database configuration from environment variables
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

# Allowed file extensions
ALLOWED_EXTENSIONS = {'ppt', 'pptx', 'doc', 'docx', 'pdf'}

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to get total pages for PDF files using PyMuPDF
def get_total_pages(file_path):
    try:
        with fitz.open(file_path) as pdf:
            return pdf.page_count
    except Exception as e:
        print(f"Error calculating total pages for {file_path}: {e}")
        return None

# Function to get or reconnect the MySQL connection and cursor
def get_db_connection():
    if not hasattr(app, 'db_connection') or not app.db_connection.is_connected():
        app.db_connection = mysql.connector.connect(**db_config)
        app.db_cursor = app.db_connection.cursor(dictionary=True)
    return app.db_connection, app.db_cursor

# Make sure uploads directory exists
if not os.path.exists('uploads'):
    os.makedirs('uploads')

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
        file_data = file.read()  # Read file binary data
        file_size = len(file_data)
        
        # Handle PDF files specifically
        if filename.lower().endswith('.pdf'):
            # Save file temporarily to calculate total pages
            file_path = os.path.join('uploads', filename)
            file.save(file_path)

            # Get total pages for PDF files
            total_pages = get_total_pages(file_path)
            if total_pages is None:
                return "Error processing PDF file", 500

            # Clean up the file after processing
            os.remove(file_path)
        else:
            total_pages = "N/A"  # For non-PDF files, we don't calculate total pages

        try:
            # Get the MySQL connection and cursor
            db_connection, db_cursor = get_db_connection()

            # Insert the file into MySQL database
            query = """
                INSERT INTO print_jobs (document_name, document_size, file_data, status, total_pages)
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (filename, file_size, file_data, 'pending', total_pages)
            db_cursor.execute(query, values)
            db_connection.commit()

            return render_template('uploaded_file.html', filename=filename, file_size=file_size, total_pages=total_pages)
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return f"Error uploading file to the database: {err}", 500
    
    return 'Invalid file type, please upload a valid file.'

@app.teardown_appcontext
def close_db_connection(exception):
    if hasattr(app, 'db_connection') and app.db_connection.is_connected():
        app.db_cursor.close()
        app.db_connection.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
