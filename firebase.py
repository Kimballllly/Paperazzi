import firebase_admin
from firebase_admin import credentials, storage
import os

# Initialize Firebase Admin SDK
cred = credentials.Certificate(r'C:\Users\luis ravalo\Desktop\templates\config\database-e9f1a-firebase-adminsdk-mkc3v-c7044dbfa1.json')
firebase_admin.initialize_app(cred, {
    'storageBucket': 'your-app-id.appspot.com'  # Replace with your Firebase Storage bucket ID
})

# Function to upload file to Firebase Storage
def upload_to_firebase(file_path, filename):
    # Get reference to Firebase Storage bucket
    bucket = storage.bucket()
    
    # Create a blob object representing the file to upload
    blob = bucket.blob(filename)
    
    # Upload the file from local system to Firebase Storage
    blob.upload_from_filename(file_path)

    # Optionally: Set metadata or make file public (uncomment below lines if needed)
    # blob.make_public()  # Makes file publicly accessible
    # print(f"File uploaded successfully! Public URL: {blob.public_url}")
    return blob.public_url

# Example usage: Upload a PPT file
local_file_path = 'path/to/your/local/file.pptx'  # Local file path to upload
file_name_in_firebase = 'uploads/your-file.pptx'  # Desired file name in Firebase Storage

upload_url = upload_to_firebase(local_file_path, file_name_in_firebase)
print(f'File uploaded successfully: {upload_url}')
