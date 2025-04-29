from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import uvicorn
from lab_processor import LabReportProcessor

app = FastAPI(title="Lab Report Processing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

lab_processor = LabReportProcessor()

@app.post("/get-lab-tests")
async def process_lab_report(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Process a lab report image and extract test information.
    
    Args:
        file: Uploaded image file
        
    Returns:
        Dictionary containing extracted lab test information
    """
    try:
        contents = await file.read()
        
        result = lab_processor.process_report(contents)
        
        return {
            "is_success": True,
            "data": result
        }
    except Exception as e:
        return {
            "is_success": False,
            "error": str(e)
        }

@app.get("/")
async def root():
    return {"message": "Lab Report Processing API is running. Use POST /get-lab-tests to process lab reports."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 