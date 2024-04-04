from fastapi import FastAPI, File, UploadFile  # FastAPI for creating the API
from pytesseract import image_to_string  # Pytesseract for OCR
from PIL import Image  # Pillow for image processing
import io  # io module for handling byte streams
from azure.storage.blob import BlobServiceClient  # Azure Blob Storage SDK
import os  # os module for environment variables
import psycopg2  # PostgreSQL database adapter
import uuid  # Import UUID library
from dotenv import load_dotenv  # For loading environment variables from .env file
load_dotenv()  # Load environment variables from .env file

# Retrieve Azure Storage connection string and container name from environment variables
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("CONTAINER_NAME")
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_USER = os.getenv("DATABASE_USER")
PORT = os.getenv("PORT")


# Initialize BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

# Function to save text to PostgreSQL
def save_text_to_postgres(filename, blob_url, text):
    try:
        # Establish connection to PostgreSQL database
        connection = psycopg2.connect(
            dbname=DATABASE_NAME,
            user=DATABASE_USER,
            password="",
            host="localhost",
            port=PORT
        )
        cursor = connection.cursor()

        sql_query = "INSERT INTO documents (filename, blob_url, text) VALUES (%s, %s, %s)"   
        # Execute SQL query with filename, blob_url, and extracted text as parameters
        cursor.execute(sql_query, (filename, blob_url, text))
        # Commit changes to the database
        connection.commit()
        # Close cursor and connection
        cursor.close()
        connection.close()
        
        print("Text saved to PostgreSQL successfully.")
    except Exception as e:
        print("Error saving text to PostgreSQL:", e)

# Create FastAPI app instance
app = FastAPI() 

# GET endpoint for testing
@app.get("/")
def read_root():
    return {"Hello": "FastAPI"}

# POST endpoint for uploading files and processing them
@app.post("/upload/")
async def create_upload_file(file: UploadFile = File(...)):
    try:
        # Generate a unique name for the blob using UUID
        unique_filename = f"{uuid.uuid4()}_{file.filename}" # Append UUID to filename
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=unique_filename) # Use the unique filename
        contents = await file.read()

        blob_client.upload_blob(contents)

        image = Image.open(io.BytesIO(contents))
        text = image_to_string(image)

        # Construct the unique blob URL; adjust this according to how you want to structure your URL
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{unique_filename}"

        # Save the extracted text to PostgreSQL with the unique blob URL
        save_text_to_postgres(file.filename, blob_url, text)
        
        return {"filename": file.filename, "blob_url": blob_url, "text": text}
    except Exception as e:
        return {"error": str(e)}