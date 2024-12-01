from flask import Flask, render_template, request, redirect, url_for
import os
import time
import mysql.connector

app = Flask(__name__)

# MySQL Database Configuration
db_config = {
    'host': 'paperazzi.cre40o0wmfru.ap-southeast-2.rds.amazonaws.com',   # Replace with your RDS endpoint
    'user': 'admin',                   # Replace with your RDS username (e.g., 'admin')
    'password': 'paperazzi',               # Replace with your RDS password
    'database': 'paperazzi'                    # Replace with the database name you created
}

@app.route('/test-db-connection')
def test_db_connection():
    try:
        # Try a simple query to check if the database is reachable
        db_cursor.execute("SELECT 1")
        return "Database connection successful!"
    except mysql.connector.Error as err:
        return f"Error connecting to database: {err}", 500
    
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
        
        try:
            # Get the MySQL connection and cursor
            db_connection, db_cursor = get_db_connection()

            # Insert the file into MySQL
            query = """
                INSERT INTO print_jobs (document_name, document_size, file_data, status)
                VALUES (%s, %s, %s, %s)
            """
            values = (filename, file_size, file_data, 'pending')
            db_cursor.execute(query, values)
            db_connection.commit()

            return render_template('uploaded_file.html', filename=filename, file_size=file_size)
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
