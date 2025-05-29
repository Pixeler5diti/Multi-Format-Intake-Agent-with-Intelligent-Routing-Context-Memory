"""
Data Models and Schemas for the Multi-Agent Document Processing System
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime


class ClassificationResult(BaseModel):
    """Schema for document classification results"""
    format: str = Field(..., description="Detected format: pdf, json, email, text")
    intent: str = Field(..., description="Detected intent: invoice, rfq, complaint, regulation, support, order, general")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    timestamp: str = Field(..., description="ISO timestamp of classification")
    error: Optional[str] = Field(None, description="Error message if classification failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "format": "email",
                "intent": "rfq",
                "confidence": 0.85,
                "timestamp": "2024-01-15T10:30:00Z",
                "error": None
            }
        }


class ProcessingResult(BaseModel):
    """Schema for agent processing results"""
    processing_id: str = Field(..., description="Unique identifier for this processing session")
    status: str = Field(..., description="Processing status: processed, error, pending")
    classification: ClassificationResult = Field(..., description="Classification results")
    extracted_data: Dict[str, Any] = Field(..., description="Data extracted by the processing agent")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata and context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "processing_id": "abc123-def456-ghi789",
                "status": "processed",
                "classification": {
                    "format": "json",
                    "intent": "invoice",
                    "confidence": 0.92,
                    "timestamp": "2024-01-15T10:30:00Z"
                },
                "extracted_data": {
                    "invoice_number": "INV-2024-001",
                    "amount": 1250.00,
                    "due_date": "2024-02-15"
                },
                "metadata": {
                    "file_size": 2048,
                    "processing_time_ms": 1500
                }
            }
        }


class EmailRecord(BaseModel):
    """Schema for CRM-style email records"""
    record_id: str = Field(..., description="Unique record identifier")
    conversation_id: str = Field(..., description="Thread/conversation identifier")
    timestamp: str = Field(..., description="Processing timestamp")
    
    # Contact Information
    sender_email: Optional[str] = Field(None, description="Sender's email address")
    sender_name: Optional[str] = Field(None, description="Sender's name")
    sender_organization: Optional[str] = Field(None, description="Sender's organization")
    
    # Email Details
    subject: Optional[str] = Field(None, description="Email subject line")
    date_sent: Optional[str] = Field(None, description="Original email date")
    message_id: Optional[str] = Field(None, description="Email message ID")
    
    # Intent Analysis
    intent: str = Field(..., description="Classified intent")
    request_summary: str = Field(..., description="Summary of the request")
    key_entities: List[str] = Field(default_factory=list, description="Important entities mentioned")
    action_required: str = Field(..., description="Required action")
    sentiment: str = Field(..., description="Email sentiment: positive, neutral, negative")
    
    # Priority
    urgency_level: str = Field(..., description="Urgency level: low, medium, high")
    urgency_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in urgency classification")
    
    # Processing Metadata
    extraction_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall extraction confidence")
    requires_followup: bool = Field(..., description="Whether this record requires follow-up")
    
    class Config:
        json_schema_extra = {
            "example": {
                "record_id": "email_abc123",
                "conversation_id": "conv_xyz789",
                "timestamp": "2024-01-15T10:30:00Z",
                "sender_email": "john.doe@company.com",
                "sender_name": "John Doe",
                "sender_organization": "ABC Corp",
                "subject": "Request for Quote - Office Supplies",
                "date_sent": "2024-01-15T09:15:00Z",
                "message_id": "<message123@company.com>",
                "intent": "rfq",
                "request_summary": "Requesting quote for office supplies including paper, pens, and folders",
                "key_entities": ["office supplies", "paper", "pens", "folders"],
                "action_required": "prepare_quote",
                "sentiment": "positive",
                "urgency_level": "medium",
                "urgency_confidence": 0.75,
                "extraction_confidence": 0.88,
                "requires_followup": True
            }
        }


class JSONExtraction(BaseModel):
    """Schema for JSON data extraction results"""
    processing_id: str = Field(..., description="Processing session ID")
    timestamp: str = Field(..., description="Extraction timestamp")
    source_format: str = Field(default="json", description="Source data format")
    
    # Extracted Structure
    field_count: int = Field(..., description="Number of fields in original JSON")
    nested_levels: int = Field(..., description="Maximum nesting depth")
    data_types: Dict[str, int] = Field(..., description="Count of different data types")
    
    # Key Information
    extracted_fields: Dict[str, Any] = Field(..., description="Key fields and values extracted")
    important_entities: List[str] = Field(default_factory=list, description="Important entities identified")
    
    # Data Quality
    anomalies: List[Dict[str, str]] = Field(default_factory=list, description="Detected anomalies or issues")
    completeness_score: float = Field(..., ge=0.0, le=1.0, description="Data completeness score")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors found")
    
    # FlowBit Schema Compliance
    flowbit_formatted: Dict[str, Any] = Field(..., description="Data formatted to FlowBit schema")
    schema_compliance: float = Field(..., ge=0.0, le=1.0, description="Compliance with target schema")
    
    class Config:
        json_schema_extra = {
            "example": {
                "processing_id": "json_abc123",
                "timestamp": "2024-01-15T10:30:00Z",
                "source_format": "json",
                "field_count": 15,
                "nested_levels": 3,
                "data_types": {"string": 8, "number": 4, "boolean": 2, "array": 1},
                "extracted_fields": {
                    "customer_id": "CUST_001",
                    "order_total": 1250.00,
                    "order_date": "2024-01-15"
                },
                "important_entities": ["customer", "order", "product"],
                "anomalies": [],
                "completeness_score": 0.95,
                "validation_errors": [],
                "flowbit_formatted": {
                    "id": "json_abc123",
                    "type": "order_data",
                    "data": {"customer_id": "CUST_001"},
                    "metadata": {"source": "json_agent"}
                },
                "schema_compliance": 0.92
            }
        }


class MemoryStats(BaseModel):
    """Schema for shared memory statistics"""
    total_entries: int = Field(..., description="Total number of memory entries")
    active_conversations: int = Field(..., description="Number of active conversation threads")
    memory_usage_mb: float = Field(..., description="Estimated memory usage in MB")
    last_cleanup: str = Field(..., description="Timestamp of last cleanup operation")
    average_entry_size: float = Field(..., description="Average size per entry in MB")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_entries": 150,
                "active_conversations": 25,
                "memory_usage_mb": 2.5,
                "last_cleanup": "2024-01-15T08:00:00Z",
                "average_entry_size": 0.017
            }
        }


class AgentStatus(BaseModel):
    """Schema for individual agent status"""
    agent_name: str = Field(..., description="Name of the agent")
    status: str = Field(..., description="Agent status: active, inactive, error")
    last_activity: str = Field(..., description="Timestamp of last activity")
    processed_count: int = Field(default=0, description="Number of documents processed")
    error_count: int = Field(default=0, description="Number of processing errors")
    average_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Average confidence score")
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_name": "json_agent",
                "status": "active",
                "last_activity": "2024-01-15T10:25:00Z",
                "processed_count": 45,
                "error_count": 2,
                "average_confidence": 0.87
            }
        }


class SystemHealth(BaseModel):
    """Schema for overall system health status"""
    status: str = Field(..., description="Overall system status")
    timestamp: str = Field(..., description="Health check timestamp")
    agents: Dict[str, str] = Field(..., description="Status of each agent")
    memory_status: str = Field(..., description="Shared memory system status")
    api_status: str = Field(..., description="External API connectivity status")
    uptime_seconds: Optional[int] = Field(None, description="System uptime in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00Z",
                "agents": {
                    "classifier": "active",
                    "json_agent": "active",
                    "email_agent": "active"
                },
                "memory_status": "active",
                "api_status": "connected",
                "uptime_seconds": 86400
            }
        }


# Error Schemas
class ErrorResponse(BaseModel):
    """Schema for error responses"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Detailed error message")
    processing_id: Optional[str] = Field(None, description="Processing ID if applicable")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Error timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "processing_failed",
                "message": "Unable to parse JSON content",
                "processing_id": "abc123-def456",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class ValidationError(BaseModel):
    """Schema for validation errors"""
    field: str = Field(..., description="Field that failed validation")
    error: str = Field(..., description="Validation error message")
    value: Optional[Any] = Field(None, description="Value that failed validation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "field": "confidence",
                "error": "Value must be between 0 and 1",
                "value": 1.5
            }
        }
