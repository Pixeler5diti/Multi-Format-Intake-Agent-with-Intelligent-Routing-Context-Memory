"""
Email Agent - Specialized agent for processing email content
"""

import re
from typing import Dict, Any, Optional
from datetime import datetime
import hashlib

from models.schemas import ProcessingResult, ClassificationResult
from services.gemini_service import GeminiService
from memory.shared_memory import SharedMemory


class EmailAgent:
    """Agent specialized in processing email content and extracting CRM-style records"""
    
    def __init__(self, gemini_service: GeminiService, shared_memory: SharedMemory):
        self.gemini_service = gemini_service
        self.shared_memory = shared_memory
        
        # Email header patterns
        self.header_patterns = {
            'from': r'from:\s*(.+?)(?:\n|$)',
            'to': r'to:\s*(.+?)(?:\n|$)',
            'subject': r'subject:\s*(.+?)(?:\n|$)',
            'date': r'date:\s*(.+?)(?:\n|$)',
            'message_id': r'message-id:\s*(.+?)(?:\n|$)',
            'reply_to': r'reply-to:\s*(.+?)(?:\n|$)'
        }
        
        # Urgency indicators
        self.urgency_indicators = {
            'high': ['urgent', 'asap', 'emergency', 'critical', 'immediate', 'rush', '!!!'],
            'medium': ['soon', 'priority', 'important', 'quickly', 'expedite'],
            'low': ['when possible', 'no rush', 'low priority', 'convenience']
        }
    
    async def process(self, email_content: str, processing_id: str) -> ProcessingResult:
        """Process email content and extract CRM-style record"""
        try:
            # Extract email headers and metadata
            headers = self._extract_headers(email_content)
            
            # Extract sender information
            sender_info = await self._extract_sender_info(headers, email_content)
            
            # Classify urgency
            urgency = self._classify_urgency(email_content)
            
            # Extract intent and request details using AI
            intent_analysis = await self._analyze_intent_and_request(email_content, processing_id)
            
            # Generate conversation ID
            conversation_id = self._generate_conversation_id(headers, email_content)
            
            # Create CRM-style record
            crm_record = self._create_crm_record(
                headers, sender_info, urgency, intent_analysis, conversation_id, processing_id
            )
            
            # Get classification from memory
            classification = self.shared_memory.get_classification(processing_id)
            if not classification:
                classification = ClassificationResult(
                    format="email",
                    intent=intent_analysis.get("intent", "general"),
                    confidence=0.8,
                    timestamp=datetime.utcnow().isoformat()
                )
            
            # Store processed data in memory
            self.shared_memory.store_extracted_data(processing_id, crm_record)
            self.shared_memory.store_conversation_id(processing_id, conversation_id)
            
            # Create processing result
            result = ProcessingResult(
                processing_id=processing_id,
                status="processed",
                classification=classification,
                extracted_data=crm_record,
                metadata={
                    "conversation_id": conversation_id,
                    **(self.shared_memory.get_metadata(processing_id) or {})
                }
            )
            
            return result
            
        except Exception as e:
            error_result = ProcessingResult(
                processing_id=processing_id,
                status="error",
                classification=ClassificationResult(
                    format="email",
                    intent="unknown",
                    confidence=0.0,
                    timestamp=datetime.utcnow().isoformat()
                ),
                extracted_data={"error": f"Email processing failed: {str(e)}"},
                metadata={"error_type": "email_processing_error"}
            )
            return error_result
    
    def _extract_headers(self, email_content: str) -> Dict[str, str]:
        """Extract email headers from content"""
        headers = {}
        content_lower = email_content.lower()
        
        for header_name, pattern in self.header_patterns.items():
            match = re.search(pattern, content_lower, re.IGNORECASE | re.MULTILINE)
            if match:
                headers[header_name] = match.group(1).strip()
        
        return headers
    
    async def _extract_sender_info(self, headers: Dict[str, str], email_content: str) -> Dict[str, Any]:
        """Extract detailed sender information"""
        sender_info = {
            "email": None,
            "name": None,
            "domain": None,
            "organization": None
        }
        
        # Extract from 'from' header
        from_field = headers.get('from', '')
        if from_field:
            # Extract email address
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', from_field)
            if email_match:
                sender_info["email"] = email_match.group(1)
                sender_info["domain"] = sender_info["email"].split('@')[1]
            
            # Extract name (usually before email or in quotes)
            name_match = re.search(r'([^<@]+?)(?:\s*<|@)', from_field)
            if name_match:
                sender_info["name"] = name_match.group(1).strip().strip('"\'')
        
        # Try to extract organization from email signature using AI
        try:
            if len(email_content) > 100:  # Only for substantial emails
                org_prompt = f"""
                Extract the sender's organization/company name from this email content.
                Look for signatures, company names, or organizational identifiers.
                
                Email content: {email_content[-500:]}  # Last 500 chars for signature
                
                Respond with only the organization name, or "Unknown" if not found.
                """
                
                org_response = await self.gemini_service.generate_response(org_prompt)
                if org_response.strip().lower() not in ["unknown", "not found", ""]:
                    sender_info["organization"] = org_response.strip()
        except:
            pass  # Continue without organization if extraction fails
        
        return sender_info
    
    def _classify_urgency(self, email_content: str) -> Dict[str, Any]:
        """Classify the urgency level of the email"""
        content_lower = email_content.lower()
        
        urgency_scores = {}
        for level, indicators in self.urgency_indicators.items():
            score = sum(1 for indicator in indicators if indicator in content_lower)
            if score > 0:
                urgency_scores[level] = score
        
        if urgency_scores:
            # Return the urgency level with highest score
            top_urgency = max(urgency_scores, key=urgency_scores.get)
            confidence = urgency_scores[top_urgency] / len(self.urgency_indicators[top_urgency])
        else:
            top_urgency = "medium"  # Default urgency
            confidence = 0.3
        
        # Check for urgency indicators in subject
        subject_indicators = ["urgent", "asap", "important", "priority"]
        subject_urgency = any(indicator in email_content.lower()[:200] for indicator in subject_indicators)
        
        if subject_urgency and top_urgency == "medium":
            top_urgency = "high"
            confidence += 0.2
        
        return {
            "level": top_urgency,
            "confidence": min(1.0, confidence),
            "indicators_found": urgency_scores
        }
    
    async def _analyze_intent_and_request(self, email_content: str, processing_id: str) -> Dict[str, Any]:
        """Use AI to analyze email intent and extract request details"""
        try:
            prompt = f"""
            Analyze this email and extract the following information in JSON format:
            
            1. Intent: What is the sender trying to achieve? (inquiry, request, complaint, order, support, etc.)
            2. Request summary: Brief summary of what they're asking for
            3. Key entities: Important names, products, services, or topics mentioned
            4. Action required: What action, if any, is needed from the recipient
            5. Sentiment: positive, neutral, or negative
            
            Email content: {email_content[:1500]}
            
            Respond with valid JSON only.
            """
            
            response = await self.gemini_service.generate_response(prompt)
            
            # Try to parse as JSON
            try:
                import json
                analysis = json.loads(response)
                return analysis
            except json.JSONDecodeError:
                # Fallback to basic analysis if JSON parsing fails
                return {
                    "intent": "general",
                    "request_summary": response[:200],
                    "key_entities": [],
                    "action_required": "review",
                    "sentiment": "neutral",
                    "ai_response": response
                }
                
        except Exception as e:
            return {
                "intent": "general",
                "request_summary": "Unable to analyze request",
                "key_entities": [],
                "action_required": "manual_review",
                "sentiment": "neutral",
                "error": str(e)
            }
    
    def _generate_conversation_id(self, headers: Dict[str, str], email_content: str) -> str:
        """Generate a conversation ID for email threading"""
        # Try to use Message-ID if available
        message_id = headers.get('message_id')
        if message_id:
            return hashlib.md5(message_id.encode()).hexdigest()[:16]
        
        # Fallback: use combination of sender, subject, and date
        sender = headers.get('from', '')
        subject = headers.get('subject', '')
        date = headers.get('date', '')
        
        # Remove "Re:" and "Fwd:" prefixes from subject for better threading
        clean_subject = re.sub(r'^(re:|fwd?:)\s*', '', subject.lower()).strip()
        
        conversation_string = f"{sender}|{clean_subject}|{date[:10]}"  # Use first 10 chars of date
        return hashlib.md5(conversation_string.encode()).hexdigest()[:16]
    
    def _create_crm_record(self, headers: Dict[str, str], sender_info: Dict[str, Any], 
                          urgency: Dict[str, Any], intent_analysis: Dict[str, Any], 
                          conversation_id: str, processing_id: str) -> Dict[str, Any]:
        """Create a CRM-style record from extracted email data"""
        return {
            "record_id": processing_id,
            "conversation_id": conversation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "email_communication",
            
            # Contact Information
            "contact": {
                "email": sender_info.get("email"),
                "name": sender_info.get("name"),
                "organization": sender_info.get("organization"),
                "domain": sender_info.get("domain")
            },
            
            # Email Details
            "email_details": {
                "subject": headers.get("subject"),
                "date": headers.get("date"),
                "message_id": headers.get("message_id"),
                "reply_to": headers.get("reply_to")
            },
            
            # Intent and Request Analysis
            "request": {
                "intent": intent_analysis.get("intent", "general"),
                "summary": intent_analysis.get("request_summary", ""),
                "key_entities": intent_analysis.get("key_entities", []),
                "action_required": intent_analysis.get("action_required", "review"),
                "sentiment": intent_analysis.get("sentiment", "neutral")
            },
            
            # Priority and Urgency
            "priority": {
                "urgency_level": urgency["level"],
                "urgency_confidence": urgency["confidence"],
                "urgency_indicators": urgency["indicators_found"]
            },
            
            # Processing Metadata
            "processing": {
                "agent": "email_agent",
                "processing_id": processing_id,
                "extraction_confidence": self._calculate_extraction_confidence(
                    headers, sender_info, intent_analysis
                ),
                "requires_followup": urgency["level"] in ["high", "medium"],
                "auto_categorized": True
            }
        }
    
    def _calculate_extraction_confidence(self, headers: Dict[str, str], 
                                       sender_info: Dict[str, Any], 
                                       intent_analysis: Dict[str, Any]) -> float:
        """Calculate confidence score for email extraction"""
        confidence = 0.0
        
        # Base confidence for email format
        confidence += 0.4
        
        # Boost for extracted headers
        header_score = len([h for h in headers.values() if h]) * 0.1
        confidence += min(0.3, header_score)
        
        # Boost for sender information
        if sender_info.get("email"):
            confidence += 0.15
        if sender_info.get("name"):
            confidence += 0.05
        if sender_info.get("organization"):
            confidence += 0.05
        
        # Boost for successful intent analysis
        if intent_analysis.get("intent") != "general":
            confidence += 0.1
        if intent_analysis.get("request_summary"):
            confidence += 0.05
        
        return min(1.0, confidence)
