from fastapi import FastAPI, File, UploadFile  # FastAPI for creating the API
from pytesseract import image_to_string  # Pytesseract for OCR
from PIL import Image  # Pillow for image processing
import io  # io module for handling byte streams
from azure.storage.blob import BlobServiceClient  # Azure Blob Storage SDK
import os  # os module for environment variables
from dotenv import load_dotenv  # For loading environment variables from .env file
load_dotenv()  # Load environment variables from .env file

# Retrieve Azure Storage connection string and container name from environment variables
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("CONTAINER_NAME")

# Initialize BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

# Create FastAPI app instance
app = FastAPI() 

#Simple get endpoint for testing
@app.get("/")
def read_root():
    return {"Hello": "FastAPI"}

#POST endpoint to upload a file, save it to Azure Blob Storage, and process it with OCR
@app.post("/upload/")
async def create_upload_file(file: UploadFile = File(...)):
    try:
        # Get blob client
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=file.filename)
        contents = await file.read()  # Read file contents
        blob_client.upload_blob(contents)  # Upload file to Azure Blob Storage
        
        image = Image.open(io.BytesIO(contents))  # Open the image file
        text = image_to_string(image)  # Perform OCR to extract text

        return {"filename": file.filename, "text": text}  # Return filename and extracted text
    except Exception as e:
        return {"error": str(e)}
