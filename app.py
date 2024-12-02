from flask import Flask, render_template, request, redirect, url_for
import os
import mysql.connector
import fitz  # PyMuPDF library for PDF processing
from docx import Document  # For handling Word documents
from pptx import Presentation  # For handling PowerPoint files

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

# Function to calculate total pages for supported file types
def get_total_pages(file_path):
    try:
        # Handle PDF files
        if file_path.lower().endswith('.pdf'):
            with fitz.open(file_path) as pdf:
                if pdf.is_encrypted:
                    pdf.authenticate('')  # Try opening with an empty password
                return pdf.page_count

        # Handle DOCX files
        elif file_path.lower().endswith('.docx'):
            doc = Document(file_path)
            # Estimate page count by dividing total characters by an approximate characters-per-page value
            total_characters = sum(len(p.text) for p in doc.paragraphs)
            average_chars_per_page = 1500  # Assumes ~1500 characters per page
            estimated_pages = max(1, total_characters // average_chars_per_page)
            return estimated_pages

        # Handle PPTX files
        elif file_path.lower().endswith('.pptx'):
            presentation = Presentation(file_path)
            return len(presentation.slides)  # Count the number of slides

        # Unsupported file type
        return "N/A"
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
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
        file_path = os.path.join('uploads', filename)
        
        # Save the file first
        file.save(file_path)
        
        # Calculate file size after saving
        file_size = os.path.getsize(file_path)
        
        # Calculate total pages for any supported file type
        total_pages = get_total_pages(file_path)
        if total_pages is None:
            os.remove(file_path)
            return f"Error processing the file: {filename}", 500

        try:
            # Read file binary data after saving
            with open(file_path, 'rb') as f:
                file_data = f.read()

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

            print(f"File {filename} inserted into DB with total pages: {total_pages}")

            return render_template('uploaded_file.html', filename=filename, file_size=file_size, total_pages=total_pages)
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return f"Error uploading file to the database: {err}", 500
        finally:
            # Clean up the file after processing
            os.remove(file_path)
    
    return 'Invalid file type, please upload a valid file.'

@app.teardown_appcontext
def close_db_connection(exception):
    if hasattr(app, 'db_connection') and app.db_connection.is_connected():
        app.db_cursor.close()
        app.db_connection.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
