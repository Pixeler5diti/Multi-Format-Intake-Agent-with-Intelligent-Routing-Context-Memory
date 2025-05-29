"""
JSON Agent - Specialized agent for processing JSON data
"""

import json
from typing import Dict, Any, List
from datetime import datetime

from models.schemas import ProcessingResult, ClassificationResult
from services.gemini_service import GeminiService
from memory.shared_memory import SharedMemory


class JSONAgent:
    """Agent specialized in processing and extracting data from JSON inputs"""
    
    def __init__(self, gemini_service: GeminiService, shared_memory: SharedMemory):
        self.gemini_service = gemini_service
        self.shared_memory = shared_memory
        
        # Define FlowBit schema structure for standardization
        self.flowbit_schema = {
            "id": str,
            "timestamp": str,
            "source": str,
            "type": str,
            "data": dict,
            "metadata": dict,
            "anomalies": list,
            "confidence": float
        }
    
    async def process(self, json_content: str, processing_id: str) -> ProcessingResult:
        """Process JSON content and extract structured data"""
        try:
            # Parse JSON content
            parsed_data = json.loads(json_content)
            
            # Analyze and extract key information
            extracted_data = await self._extract_structured_data(parsed_data, processing_id)
            
            # Identify anomalies or missing fields
            anomalies = self._detect_anomalies(parsed_data)
            
            # Format to FlowBit schema
            formatted_data = self._format_to_flowbit_schema(
                extracted_data, parsed_data, anomalies, processing_id
            )
            
            # Get classification from memory
            classification = self.shared_memory.get_classification(processing_id)
            if not classification:
                classification = ClassificationResult(
                    format="json",
                    intent="general",
                    confidence=0.8,
                    timestamp=datetime.utcnow().isoformat()
                )
            
            # Store processed data in memory
            self.shared_memory.store_extracted_data(processing_id, formatted_data)
            
            # Create processing result
            result = ProcessingResult(
                processing_id=processing_id,
                status="processed",
                classification=classification,
                extracted_data=formatted_data,
                metadata=self.shared_memory.get_metadata(processing_id) or {}
            )
            
            return result
            
        except json.JSONDecodeError as e:
            error_result = ProcessingResult(
                processing_id=processing_id,
                status="error",
                classification=ClassificationResult(
                    format="json",
                    intent="unknown",
                    confidence=0.0,
                    timestamp=datetime.utcnow().isoformat()
                ),
                extracted_data={"error": f"Invalid JSON format: {str(e)}"},
                metadata={"error_type": "json_decode_error"}
            )
            return error_result
            
        except Exception as e:
            error_result = ProcessingResult(
                processing_id=processing_id,
                status="error",
                classification=ClassificationResult(
                    format="json",
                    intent="unknown",
                    confidence=0.0,
                    timestamp=datetime.utcnow().isoformat()
                ),
                extracted_data={"error": f"Processing failed: {str(e)}"},
                metadata={"error_type": "processing_error"}
            )
            return error_result
    
    async def _extract_structured_data(self, parsed_data: Dict[str, Any], processing_id: str) -> Dict[str, Any]:
        """Extract and structure key information from JSON data"""
        try:
            # Use Gemini to intelligently extract key information
            prompt = f"""
            Analyze the following JSON data and extract the most important information.
            Identify key fields, values, and relationships. Format the response as a JSON object
            with clear field names and organized structure.
            
            JSON Data: {json.dumps(parsed_data, indent=2)[:2000]}
            
            Extract:
            1. Main entity/subject
            2. Key identifiers (IDs, names, codes)
            3. Important values (amounts, dates, quantities)
            4. Relationships between entities
            5. Any business-relevant information
            
            Response format: Valid JSON object with extracted information.
            """
            
            response = await self.gemini_service.generate_response(prompt)
            
            # Try to parse Gemini's response as JSON
            try:
                ai_extracted = json.loads(response)
                return {
                    "ai_extracted": ai_extracted,
                    "raw_structure": self._analyze_structure(parsed_data),
                    "key_fields": self._identify_key_fields(parsed_data)
                }
            except json.JSONDecodeError:
                # Fallback to manual extraction if AI response isn't valid JSON
                return {
                    "ai_analysis": response,
                    "raw_structure": self._analyze_structure(parsed_data),
                    "key_fields": self._identify_key_fields(parsed_data)
                }
                
        except Exception as e:
            # Fallback to basic structure analysis
            return {
                "extraction_error": str(e),
                "raw_structure": self._analyze_structure(parsed_data),
                "key_fields": self._identify_key_fields(parsed_data)
            }
    
    def _analyze_structure(self, data: Any, path: str = "") -> Dict[str, Any]:
        """Analyze the structure of JSON data"""
        if isinstance(data, dict):
            structure = {
                "type": "object",
                "fields": len(data),
                "keys": list(data.keys())[:10],  # Limit to first 10 keys
                "nested_objects": sum(1 for v in data.values() if isinstance(v, dict)),
                "arrays": sum(1 for v in data.values() if isinstance(v, list))
            }
            
            # Analyze nested structures
            for key, value in data.items():
                if isinstance(value, (dict, list)) and len(str(value)) < 1000:
                    structure[f"nested_{key}"] = self._analyze_structure(value, f"{path}.{key}")
            
            return structure
            
        elif isinstance(data, list):
            return {
                "type": "array",
                "length": len(data),
                "sample_types": list(set(type(item).__name__ for item in data[:5])),
                "first_item": self._analyze_structure(data[0], f"{path}[0]") if data else None
            }
        else:
            return {
                "type": type(data).__name__,
                "value": str(data)[:100] if len(str(data)) <= 100 else str(data)[:100] + "..."
            }
    
    def _identify_key_fields(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify potentially important fields in JSON data"""
        key_fields = []
        
        # Common important field patterns
        important_patterns = [
            "id", "uuid", "key", "name", "title", "email", "phone",
            "amount", "total", "price", "cost", "value", "quantity",
            "date", "time", "timestamp", "created", "updated",
            "status", "state", "type", "category", "priority",
            "address", "location", "country", "city"
        ]
        
        def extract_fields(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    full_key = f"{prefix}.{key}" if prefix else key
                    
                    # Check if field name matches important patterns
                    is_important = any(pattern in key.lower() for pattern in important_patterns)
                    
                    # Add field info
                    field_info = {
                        "field": full_key,
                        "type": type(value).__name__,
                        "important": is_important,
                        "value_sample": str(value)[:50] if not isinstance(value, (dict, list)) else None
                    }
                    key_fields.append(field_info)
                    
                    # Recurse into nested objects (limited depth)
                    if isinstance(value, dict) and len(prefix.split('.')) < 3:
                        extract_fields(value, full_key)
        
        extract_fields(data)
        
        # Sort by importance
        key_fields.sort(key=lambda x: x["important"], reverse=True)
        
        return key_fields[:20]  # Limit to top 20 fields
    
    def _detect_anomalies(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect potential anomalies or issues in JSON data"""
        anomalies = []
        
        def check_anomalies(obj, path=""):
            if isinstance(obj, dict):
                # Check for empty objects
                if not obj:
                    anomalies.append({
                        "type": "empty_object",
                        "path": path,
                        "description": "Empty object detected"
                    })
                
                # Check for null/None values in important fields
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    if value is None:
                        anomalies.append({
                            "type": "null_value",
                            "path": current_path,
                            "description": f"Null value in field '{key}'"
                        })
                    
                    # Check for unusually long strings (potential data corruption)
                    elif isinstance(value, str) and len(value) > 1000:
                        anomalies.append({
                            "type": "oversized_string",
                            "path": current_path,
                            "description": f"Very long string in field '{key}' ({len(value)} chars)"
                        })
                    
                    # Recurse into nested structures
                    elif isinstance(value, (dict, list)):
                        check_anomalies(value, current_path)
            
            elif isinstance(obj, list):
                # Check for empty arrays
                if not obj:
                    anomalies.append({
                        "type": "empty_array",
                        "path": path,
                        "description": "Empty array detected"
                    })
                
                # Check for inconsistent types in array
                if obj:
                    types = set(type(item).__name__ for item in obj)
                    if len(types) > 1:
                        anomalies.append({
                            "type": "mixed_types",
                            "path": path,
                            "description": f"Array contains mixed types: {', '.join(types)}"
                        })
        
        check_anomalies(data)
        return anomalies
    
    def _format_to_flowbit_schema(self, extracted_data: Dict[str, Any], 
                                  raw_data: Dict[str, Any], anomalies: List[Dict[str, Any]], 
                                  processing_id: str) -> Dict[str, Any]:
        """Format processed data to FlowBit schema"""
        return {
            "id": processing_id,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "json_agent",
            "type": "structured_data",
            "data": {
                "extracted": extracted_data,
                "structure_analysis": extracted_data.get("raw_structure", {}),
                "key_fields_count": len(extracted_data.get("key_fields", []))
            },
            "metadata": {
                "original_size": len(json.dumps(raw_data)),
                "field_count": len(raw_data) if isinstance(raw_data, dict) else 0,
                "processing_agent": "json_agent",
                "schema_version": "1.0"
            },
            "anomalies": anomalies,
            "confidence": self._calculate_processing_confidence(extracted_data, anomalies)
        }
    
    def _calculate_processing_confidence(self, extracted_data: Dict[str, Any], 
                                       anomalies: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for JSON processing"""
        base_confidence = 0.8
        
        # Reduce confidence based on anomalies
        anomaly_penalty = len(anomalies) * 0.1
        confidence = base_confidence - anomaly_penalty
        
        # Boost confidence if AI extraction was successful
        if "ai_extracted" in extracted_data:
            confidence += 0.1
        
        # Boost confidence based on identified key fields
        key_fields_count = len(extracted_data.get("key_fields", []))
        confidence += min(0.1, key_fields_count * 0.01)
        
        return max(0.0, min(1.0, confidence))
