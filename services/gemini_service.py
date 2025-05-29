"""
Gemini Service - Interface for Google Gemini AI API
"""

import os
import asyncio
import json
from typing import Optional, Dict, Any, List
import aiohttp
from datetime import datetime


class GeminiService:
    """Service for interacting with Google Gemini AI API"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "default_gemini_key")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = "gemini-1.5-flash"
        
        # Request settings
        self.default_temperature = 0.3  # Lower temperature for more consistent results
        self.max_tokens = 2048
        self.timeout = 30
        
        # Rate limiting
        self.requests_per_minute = 60
        self.request_times = []
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens_used": 0,
            "average_response_time": 0.0
        }
    
    async def generate_response(self, prompt: str, temperature: Optional[float] = None, 
                              max_tokens: Optional[int] = None) -> str:
        """Generate a response using Gemini AI"""
        try:
            start_time = datetime.utcnow()
            
            # Rate limiting check
            await self._check_rate_limit()
            
            # Prepare request
            temperature = temperature or self.default_temperature
            max_tokens = max_tokens or self.max_tokens
            
            url = f"{self.base_url}/models/{self.model}:generateContent"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": temperature,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": max_tokens,
                    "stopSequences": []
                },
                "safetySettings": [
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    }
                ]
            }
            
            # Make API request
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    params={"key": self.api_key}
                ) as response:
                    
                    response_data = await response.json()
                    
                    if response.status == 200:
                        # Extract text from response
                        if "candidates" in response_data and len(response_data["candidates"]) > 0:
                            candidate = response_data["candidates"][0]
                            if "content" in candidate and "parts" in candidate["content"]:
                                text_response = candidate["content"]["parts"][0].get("text", "")
                                
                                # Update statistics
                                end_time = datetime.utcnow()
                                response_time = (end_time - start_time).total_seconds()
                                self._update_stats(True, response_time, len(text_response))
                                
                                return text_response
                        
                        # If no valid response found, return empty string
                        self._update_stats(False, 0, 0)
                        return ""
                    
                    else:
                        # Handle API errors
                        error_message = response_data.get("error", {}).get("message", "Unknown API error")
                        print(f"Gemini API error: {response.status} - {error_message}")
                        self._update_stats(False, 0, 0)
                        return f"API Error: {error_message}"
        
        except asyncio.TimeoutError:
            print("Gemini API request timed out")
            self._update_stats(False, 0, 0)
            return "Request timed out"
        
        except aiohttp.ClientError as e:
            print(f"HTTP client error: {str(e)}")
            self._update_stats(False, 0, 0)
            return f"Connection error: {str(e)}"
        
        except Exception as e:
            print(f"Unexpected error in Gemini service: {str(e)}")
            self._update_stats(False, 0, 0)
            return f"Unexpected error: {str(e)}"
    
    async def analyze_document_structure(self, content: str, document_type: str = "unknown") -> Dict[str, Any]:
        """Analyze document structure and extract metadata"""
        prompt = f"""
        Analyze the structure and content of this {document_type} document.
        Provide a detailed analysis in JSON format including:
        
        1. Document type and format
        2. Key sections and their content
        3. Important entities (names, dates, amounts, etc.)
        4. Data quality assessment
        5. Potential issues or anomalies
        
        Document content:
        {content[:2000]}
        
        Respond with valid JSON only.
        """
        
        response = await self.generate_response(prompt, temperature=0.2)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "analysis_error": "Failed to parse AI response as JSON",
                "raw_response": response,
                "document_type": document_type,
                "content_length": len(content)
            }
    
    async def extract_entities(self, content: str, entity_types: List[str] = None) -> Dict[str, List[str]]:
        """Extract specific types of entities from content"""
        if entity_types is None:
            entity_types = ["person", "organization", "location", "date", "money", "email", "phone"]
        
        entity_list = ", ".join(entity_types)
        
        prompt = f"""
        Extract the following types of entities from the given content: {entity_list}
        
        Content: {content[:1500]}
        
        Format your response as JSON with entity types as keys and lists of found entities as values.
        Example: {{"person": ["John Doe", "Jane Smith"], "organization": ["ABC Corp"], "date": ["2024-01-15"]}}
        
        Respond with valid JSON only.
        """
        
        response = await self.generate_response(prompt, temperature=0.1)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback: return empty entities structure
            return {entity_type: [] for entity_type in entity_types}
    
    async def classify_intent_detailed(self, content: str, possible_intents: List[str] = None) -> Dict[str, Any]:
        """Perform detailed intent classification with confidence scores"""
        if possible_intents is None:
            possible_intents = ["invoice", "rfq", "complaint", "regulation", "support", "order", "inquiry", "general"]
        
        intents_list = ", ".join(possible_intents)
        
        prompt = f"""
        Analyze the intent of this content and provide detailed classification.
        
        Possible intents: {intents_list}
        
        Content: {content[:1200]}
        
        Provide analysis in JSON format:
        {{
            "primary_intent": "most_likely_intent",
            "confidence": 0.0-1.0,
            "alternative_intents": [
                {{"intent": "alternative", "confidence": 0.0-1.0}}
            ],
            "reasoning": "explanation of classification",
            "key_indicators": ["list", "of", "keywords", "that", "led", "to", "classification"]
        }}
        
        Respond with valid JSON only.
        """
        
        response = await self.generate_response(prompt, temperature=0.2)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "primary_intent": "general",
                "confidence": 0.5,
                "alternative_intents": [],
                "reasoning": "Failed to parse AI response",
                "key_indicators": [],
                "error": "JSON parsing failed"
            }
    
    async def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        current_time = datetime.utcnow()
        
        # Remove requests older than 1 minute
        self.request_times = [
            req_time for req_time in self.request_times 
            if (current_time - req_time).total_seconds() < 60
        ]
        
        # Check if we're at the rate limit
        if len(self.request_times) >= self.requests_per_minute:
            # Calculate how long to wait
            oldest_request = min(self.request_times)
            wait_time = 60 - (current_time - oldest_request).total_seconds()
            
            if wait_time > 0:
                print(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
        
        # Add current request time
        self.request_times.append(current_time)
    
    def _update_stats(self, success: bool, response_time: float, response_length: int):
        """Update service statistics"""
        self.stats["total_requests"] += 1
        
        if success:
            self.stats["successful_requests"] += 1
            self.stats["total_tokens_used"] += response_length // 4  # Rough token estimation
            
            # Update average response time
            current_avg = self.stats["average_response_time"]
            total_successful = self.stats["successful_requests"]
            self.stats["average_response_time"] = (
                (current_avg * (total_successful - 1) + response_time) / total_successful
            )
        else:
            self.stats["failed_requests"] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service usage statistics"""
        total_requests = self.stats["total_requests"]
        success_rate = (
            self.stats["successful_requests"] / total_requests 
            if total_requests > 0 else 0
        )
        
        return {
            **self.stats,
            "success_rate": success_rate,
            "current_rate_limit_usage": len(self.request_times),
            "rate_limit_max": self.requests_per_minute,
            "estimated_cost_usd": self.stats["total_tokens_used"] * 0.000002  # Rough estimate
        }
    
    def reset_statistics(self):
        """Reset service statistics"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens_used": 0,
            "average_response_time": 0.0
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the Gemini service"""
        try:
            start_time = datetime.utcnow()
            
            # Simple test prompt
            test_response = await self.generate_response(
                "Respond with 'OK' if you can understand this message.",
                temperature=0.0,
                max_tokens=10
            )
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            is_healthy = "ok" in test_response.lower()
            
            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "response_time_seconds": response_time,
                "test_response": test_response,
                "api_key_configured": bool(self.api_key and self.api_key != "default_gemini_key"),
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "api_key_configured": bool(self.api_key and self.api_key != "default_gemini_key"),
                "timestamp": datetime.utcnow().isoformat()
            }
