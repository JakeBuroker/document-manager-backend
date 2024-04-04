from fastapi import FastAPI, File, UploadFile  # FastAPI for creating the API
from pytesseract import image_to_string  # Pytesseract for OCR
from PIL import Image  # Pillow for image processing
import io  # io module for handling byte streams

# Create a FastAPI instance
app = FastAPI()

# Simple GET endpoint to test the API
@app.get("/")
def read_root():
    return {"Hello": "FastAPI"}

# POST endpoint for uploading files
@app.post("/upload/")
async def create_upload_file(file: UploadFile = File(...)):
    try:
        contents = await file.read()  # Read file contents asynchronously
        image = Image.open(io.BytesIO(contents))  # Open the image file using Pillow
        text = image_to_string(image)  # Use Pytesseract to extract text from the image
        return {"filename": file.filename, "text": text}  # Return the file name and extracted text
    except Exception as e:
        return {"error": str(e)}  # In case of an error, return the error message
