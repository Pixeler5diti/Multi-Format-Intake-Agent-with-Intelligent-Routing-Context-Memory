"""
Classifier Agent - Central routing and classification logic
"""

import json
import re
from typing import Dict, Any
from datetime import datetime

from models.schemas import ClassificationResult
from services.gemini_service import GeminiService
from memory.shared_memory import SharedMemory


class ClassifierAgent:
    """Central agent for classifying input format and intent"""
    
    def __init__(self, gemini_service: GeminiService, shared_memory: SharedMemory):
        self.gemini_service = gemini_service
        self.shared_memory = shared_memory
        
        # Intent patterns for quick classification
        self.intent_patterns = {
            "invoice": ["invoice", "bill", "payment", "amount due", "total:", "$", "€", "£"],
            "rfq": ["request for quote", "rfq", "quotation", "price", "estimate", "proposal"],
            "complaint": ["complaint", "issue", "problem", "dissatisfied", "unhappy", "concern"],
            "regulation": ["regulation", "compliance", "policy", "legal", "requirement", "standard"],
            "support": ["help", "support", "assistance", "question", "inquiry"],
            "order": ["order", "purchase", "buy", "procurement", "delivery"]
        }
    
    async def classify(self, content: str, processing_id: str) -> ClassificationResult:
        """Classify input content for format and intent"""
        try:
            # Detect format
            format_type = self._detect_format(content)
            
            # Classify intent using Gemini
            intent = await self._classify_intent(content, format_type)
            
            # Calculate confidence based on pattern matching and content analysis
            confidence = self._calculate_confidence(content, format_type, intent)
            
            # Create classification result
            classification = ClassificationResult(
                format=format_type,
                intent=intent,
                confidence=confidence,
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Store classification in memory
            self.shared_memory.store_classification(processing_id, classification)
            
            return classification
            
        except Exception as e:
            # Fallback classification
            fallback_classification = ClassificationResult(
                format="unknown",
                intent="unknown",
                confidence=0.0,
                timestamp=datetime.utcnow().isoformat(),
                error=f"Classification failed: {str(e)}"
            )
            self.shared_memory.store_classification(processing_id, fallback_classification)
            return fallback_classification
    
    def _detect_format(self, content: str) -> str:
        """Detect the format of input content"""
        content_lower = content.lower().strip()
        
        # Check for JSON format
        if content.strip().startswith('{') and content.strip().endswith('}'):
            try:
                json.loads(content)
                return "json"
            except json.JSONDecodeError:
                pass
        
        # Check for email format
        email_indicators = [
            "from:", "to:", "subject:", "date:",
            "message-id:", "received:", "reply-to:",
            "dear", "hi", "hello", "best regards", "sincerely"
        ]
        
        if any(indicator in content_lower for indicator in email_indicators):
            return "email"
        
        # Check for PDF indicators (if content was extracted from PDF)
        if "[pdf content]" in content_lower or "extracted text from" in content_lower:
            return "pdf"
        
        # Default to text if no specific format detected
        return "text"
    
    async def _classify_intent(self, content: str, format_type: str) -> str:
        """Classify the intent of the content using Gemini AI"""
        try:
            # First try pattern-based classification for speed
            pattern_intent = self._pattern_based_intent(content)
            if pattern_intent != "unknown":
                return pattern_intent
            
            # Use Gemini for more sophisticated classification
            prompt = f"""
            Classify the intent of the following {format_type} content. 
            Choose from these categories: invoice, rfq, complaint, regulation, support, order, general.
            
            Content: {content[:1000]}
            
            Respond with only the category name in lowercase.
            """
            
            response = await self.gemini_service.generate_response(prompt)
            
            # Validate response
            valid_intents = ["invoice", "rfq", "complaint", "regulation", "support", "order", "general"]
            intent = response.strip().lower()
            
            if intent in valid_intents:
                return intent
            else:
                return "general"
                
        except Exception as e:
            print(f"Intent classification error: {str(e)}")
            return self._pattern_based_intent(content)
    
    def _pattern_based_intent(self, content: str) -> str:
        """Classify intent based on keyword patterns"""
        content_lower = content.lower()
        
        # Count matches for each intent category
        intent_scores = {}
        for intent, patterns in self.intent_patterns.items():
            score = sum(1 for pattern in patterns if pattern in content_lower)
            if score > 0:
                intent_scores[intent] = score
        
        if intent_scores:
            # Return intent with highest score
            return max(intent_scores, key=intent_scores.get)
        
        return "unknown"
    
    def _calculate_confidence(self, content: str, format_type: str, intent: str) -> float:
        """Calculate confidence score for classification"""
        confidence = 0.0
        
        # Base confidence based on format detection certainty
        if format_type == "json":
            try:
                json.loads(content)
                confidence += 0.8  # High confidence for valid JSON
            except:
                confidence += 0.3  # Lower confidence if JSON parsing failed
        elif format_type == "email":
            email_indicators = ["from:", "to:", "subject:"]
            matches = sum(1 for indicator in email_indicators if indicator in content.lower())
            confidence += min(0.7, matches * 0.25)
        elif format_type == "pdf":
            confidence += 0.6  # Medium confidence for PDF
        else:
            confidence += 0.4  # Lower confidence for text
        
        # Adjust confidence based on intent classification
        if intent != "unknown":
            pattern_intent = self._pattern_based_intent(content)
            if pattern_intent == intent:
                confidence += 0.2  # Boost if pattern matching agrees
            else:
                confidence += 0.1  # Slight boost for any detected intent
        
        # Normalize confidence to 0-1 range
        return min(1.0, confidence)
