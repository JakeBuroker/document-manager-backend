from fastapi import FastAPI, File, UploadFile  # FastAPI for creating the API
from pytesseract import image_to_string  # Pytesseract for OCR
from PIL import Image  # To open and process images
import io  # io module for handling byte streams
from azure.storage.blob import BlobServiceClient  # Azure Blob Storage SDK
import os  # os module for environment variables
import psycopg2  # PostgreSQL database adapter
import uuid  # To generate unique identifiers
from dotenv import load_dotenv  # For loading environment variables from .env file
load_dotenv() # Load environment variables from .env file

# Retrieve Azure Storage connection string and container name from environment variables
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("CONTAINER_NAME")
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_USER = os.getenv("DATABASE_USER")
PORT = os.getenv("PORT")

# Initialize Azure Blob Service Client
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

# Function to save OCR text to PostgreSQL
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
        
        # Insert document details into database and return the new row's ID
        sql_query = "INSERT INTO documents (filename, blob_url, text) VALUES (%s, %s, %s) RETURNING id"   
        cursor.execute(sql_query, (filename, blob_url, text))
        document_id = cursor.fetchone()[0]  # Fetch the generated id
        connection.commit()
        
        # Close cursor and connection
        cursor.close()
        connection.close()
        
        return document_id
    except Exception as e:
        print(f"Error saving text to PostgreSQL: {e}")
        return None

# Function to retrieve document details by ID from PostgreSQL database
def get_text_from_postgres_by_id(document_id):
    try:
        connection = psycopg2.connect(
            dbname=DATABASE_NAME,
            user=DATABASE_USER,
            password="",
            host="localhost",
            port=PORT
        )
        cursor = connection.cursor()
        
        sql_query = "SELECT id, filename, blob_url, text FROM documents WHERE id=%s"
        cursor.execute(sql_query, (document_id,))
        result = cursor.fetchone()
        
        # Close cursor and connection
        cursor.close()
        connection.close()
        
        # Check if a document was found
        if result:
            return {"id": result[0], "filename": result[1], "blob_url": result[2], "text": result[3]}
        else:
            return None
    except Exception as e:
        print(f"Error retrieving document from PostgreSQL: {e}")
        return None

# Initialize FastAPI app instance
app = FastAPI()

# GET endpoint for retrieving documents by ID
@app.get("/documents/{document_id}")
def get_document(document_id: int):
    document_details = get_text_from_postgres_by_id(document_id)
    if document_details:
        return document_details
    else:
        raise HTTPException(status_code=404, detail="Document not found")
    
# POST endpoint for uploading and processing files
@app.post("/upload/")
async def create_upload_file(file: UploadFile = File(...)):
    try:
        # Generate a unique name for the blob using UUID
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        
        # Upload the file to Azure Blob Storage
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=unique_filename) # Append UUID to filename
        contents = await file.read()
        blob_client.upload_blob(contents)
        
        # Perform OCR on the uploaded file
        image = Image.open(io.BytesIO(contents))
        text = image_to_string(image)
        
        # Construct blob URL and save document details to database
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{unique_filename}"
        document_id = save_text_to_postgres(file.filename, blob_url, text)
        
        # Return the document ID and details
        return {"id": document_id, "filename": file.filename, "blob_url": blob_url, "text": text}
    except Exception as e:
        return {"error uploading file": str(e)}