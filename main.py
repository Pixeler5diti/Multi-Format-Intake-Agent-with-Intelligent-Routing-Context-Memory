from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
import os
import json
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

from agents.classifier import ClassifierAgent
from agents.json_agent import JSONAgent
from agents.email_agent import EmailAgent
from memory.shared_memory import SharedMemory
from models.schemas import ProcessingResult, ClassificationResult
from services.gemini_service import GeminiService

# Initialize FastAPI app
app = FastAPI(title="Multi-Agent Document Processing System", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize services and agents
gemini_service = GeminiService()
shared_memory = SharedMemory()
classifier_agent = ClassifierAgent(gemini_service, shared_memory)
json_agent = JSONAgent(gemini_service, shared_memory)
email_agent = EmailAgent(gemini_service, shared_memory)

class TextInput(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page"""
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/process/file", response_model=ProcessingResult)
async def process_file(file: UploadFile = File(...)):
    """Process uploaded file (PDF, JSON, or text files)"""
    try:
        # Generate processing ID
        processing_id = str(uuid.uuid4())
        
        # Read file content
        content = await file.read()
        
        # Determine file type and decode content
        if file.filename.lower().endswith('.pdf'):
            # Mock PDF text extraction (in real implementation, use PyPDF2 or similar)
            text_content = f"[PDF Content] Extracted text from {file.filename}. " + \
                          "This is a mock extraction. In production, implement proper PDF parsing."
            file_type = "pdf"
        elif file.filename.lower().endswith('.json'):
            try:
                text_content = content.decode('utf-8')
                json.loads(text_content)  # Validate JSON
                file_type = "json"
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise HTTPException(status_code=400, detail="Invalid JSON file")
        else:
            # Treat as text/email
            try:
                text_content = content.decode('utf-8')
                file_type = "text"
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="Unable to decode file content")
        
        # Store initial metadata
        metadata = {
            "filename": file.filename,
            "file_size": len(content),
            "upload_timestamp": datetime.utcnow().isoformat(),
            "detected_type": file_type
        }
        
        shared_memory.store_metadata(processing_id, metadata)
        
        # Classify the content
        classification = await classifier_agent.classify(text_content, processing_id)
        
        # Route to appropriate agent based on classification
        if classification.format == "json":
            result = await json_agent.process(text_content, processing_id)
        elif classification.format == "email":
            result = await email_agent.process(text_content, processing_id)
        else:
            # Handle PDF or other text documents
            result = ProcessingResult(
                processing_id=processing_id,
                status="processed",
                classification=classification,
                extracted_data={"raw_content": text_content[:500] + "..." if len(text_content) > 500 else text_content},
                metadata=metadata
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/process/text", response_model=ProcessingResult)
async def process_text(input_data: TextInput):
    """Process raw text input (email content, JSON string, etc.)"""
    try:
        # Generate processing ID
        processing_id = str(uuid.uuid4())
        
        # Store initial metadata
        metadata = {
            "input_type": "text",
            "content_length": len(input_data.content),
            "timestamp": datetime.utcnow().isoformat(),
            **(input_data.metadata or {})
        }
        
        shared_memory.store_metadata(processing_id, metadata)
        
        # Classify the content
        classification = await classifier_agent.classify(input_data.content, processing_id)
        
        # Route to appropriate agent
        if classification.format == "json":
            result = await json_agent.process(input_data.content, processing_id)
        elif classification.format == "email":
            result = await email_agent.process(input_data.content, processing_id)
        else:
            result = ProcessingResult(
                processing_id=processing_id,
                status="processed",
                classification=classification,
                extracted_data={"content": input_data.content},
                metadata=metadata
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/memory/{processing_id}")
async def get_memory(processing_id: str):
    """Retrieve stored memory for a processing ID"""
    try:
        memory_data = shared_memory.get_memory(processing_id)
        if not memory_data:
            raise HTTPException(status_code=404, detail="Processing ID not found")
        return memory_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory retrieval failed: {str(e)}")

@app.get("/memory")
async def list_all_memory():
    """List all stored memory entries"""
    try:
        memory_data = shared_memory.get_all_memory()
        return {
            "entries": memory_data.get("entries", {}),
            "conversation_index": memory_data.get("conversation_index", {}),
            "statistics": memory_data.get("statistics", {
                "total_entries": 0,
                "active_conversations": 0,
                "last_cleanup": "never"
            })
        }
    except Exception as e:
        print(f"Memory error: {str(e)}")
        return {
            "entries": {},
            "conversation_index": {},
            "statistics": {
                "total_entries": 0,
                "active_conversations": 0,
                "last_cleanup": "never",
                "error": str(e)
            }
        }

@app.delete("/memory/{processing_id}")
async def clear_memory(processing_id: str):
    """Clear memory for a specific processing ID"""
    try:
        success = shared_memory.clear_memory(processing_id)
        if not success:
            raise HTTPException(status_code=404, detail="Processing ID not found")
        return {"message": "Memory cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory clearing failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "agents": {
            "classifier": "active",
            "json_agent": "active", 
            "email_agent": "active"
        },
        "memory": "active"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
