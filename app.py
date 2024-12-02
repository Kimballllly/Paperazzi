from flask import Flask, render_template, request, redirect, url_for
import os
import mysql.connector
import fitz  # PyMuPDF library

app = Flask(__name__)

# Database configuration from environment variables
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

# Function to get the total pages in the PDF
def get_total_pages(file_data):
    try:
        with fitz.open(stream=file_data, filetype="pdf") as pdf:
            total_pages = pdf.page_count
        return total_pages
    except Exception as e:
        print(f"Error calculating total pages: {e}")
        return None

# Function to get or reconnect the MySQL connection and cursor
def get_db_connection():
    if not hasattr(app, 'db_connection') or not app.db_connection.is_connected():
        app.db_connection = mysql.connector.connect(**db_config)
        app.db_cursor = app.db_connection.cursor(dictionary=True)
    return app.db_connection, app.db_cursor

# Allowed file extensions
ALLOWED_EXTENSIONS = {'ppt', 'pptx', 'doc', 'docx', 'pdf'}

# Check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        
        # Get total pages if the file is PDF
        total_pages = get_total_pages(file_data)
        
        if total_pages is None:
            return "Error: Couldn't read the total pages from the PDF file."
        
        try:
            # Get the MySQL connection and cursor
            db_connection, db_cursor = get_db_connection()

            # Insert the file into MySQL, including total pages
            query = """
                INSERT INTO print_jobs (document_name, document_size, file_data, status)
                VALUES (%s, %s, %s, %s)
            """
            values = (filename, total_pages, file_data, 'pending')
            db_cursor.execute(query, values)
            db_connection.commit()

            return render_template('uploaded_file.html', filename=filename, file_size=total_pages)
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return f"Error uploading file to the database: {err}"  # Print more detailed error message
    
    return 'Invalid file type, please upload a valid file.'

@app.teardown_appcontext
def close_db_connection(exception):
    if hasattr(app, 'db_connection') and app.db_connection.is_connected():
        app.db_cursor.close()
        app.db_connection.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
