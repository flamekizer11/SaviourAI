import requests
import json
import time
import threading
from typing import Optional, Dict, Any, Tuple
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import CONFIG
from logger import interview_logger

class AIResponseHandler:
    """Handles AI responses with retry logic, fallback models, and caching"""
    
    def __init__(self):
        self.session = self._create_session()
        self.response_cache = {}  # Simple cache for similar questions
        self.cache_lock = threading.Lock()
        self.request_count = 0
        self.total_response_time = 0.0
        
        # System prompts for different contexts
        self.system_prompts = {
            "data_science": """You are a senior data scientist preparing a candidate for a live technical interview. 
            Provide brief, precise, and confident answers to data science interview questions, including Python, ML, SQL, and statistics. 
            Keep responses under 150 words and focus on key points that demonstrate expertise.""",
            
            "general": """You are an expert technical interview coach. Provide concise, accurate answers to technical questions. 
            Focus on demonstrating deep understanding while keeping responses brief and actionable.""",
            
            "coding": """You are a senior software engineer helping with coding interview preparation. 
            Provide clear, efficient solutions with brief explanations. Focus on optimal approaches and common patterns."""
        }
        
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=CONFIG.ai.MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def get_response(self, question: str, context: str = "data_science") -> Tuple[str, str, float]:
        """
        Get AI response for question
        Returns: (response, model_used, response_time)
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = self._get_cache_key(question, context)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            interview_logger.log_info("Using cached response")
            return cached_response[0], cached_response[1], time.time() - start_time
        
        # Try primary model first
        response, model_used = self._try_model(question, CONFIG.ai.PRIMARY_MODEL, context)
        
        # Fallback to secondary model if primary fails
        if not response:
            interview_logger.log_warning("Primary model failed, trying fallback")
            response, model_used = self._try_model(question, CONFIG.ai.FALLBACK_MODEL, context)
        
        # Final fallback to simple response
        if not response:
            response = "I'm having trouble processing that question right now. Could you please rephrase it?"
            model_used = "fallback"
        
        response_time = time.time() - start_time
        
        # Cache successful responses
        if response and model_used != "fallback":
            self._cache_response(cache_key, (response, model_used))
        
        # Update metrics
        self.request_count += 1
        self.total_response_time += response_time
        
        return response, model_used, response_time
    
    def _try_model(self, question: str, model: str, context: str) -> Tuple[Optional[str], str]:
        """Try to get response from specific model"""
        try:
            headers = {
                "Authorization": f"Bearer {CONFIG.ai.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://localhost:3000",  # Required by OpenRouter
                "X-Title": "StealthAI Interview Assistant"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": self.system_prompts.get(context, self.system_prompts["general"])},
                    {"role": "user", "content": self._enhance_question(question)}
                ],
                "max_tokens": CONFIG.ai.MAX_TOKENS,
                "temperature": CONFIG.ai.TEMPERATURE,
                "top_p": 0.9,
                "frequency_penalty": 0.1,
                "presence_penalty": 0.1
            }
            
            response = self.session.post(
                CONFIG.ai.OPENROUTER_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=CONFIG.ai.TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"].strip()
                    interview_logger.log_info(f"Successful response from {model}")
                    return content, model
                else:
                    interview_logger.log_error(f"No choices in response from {model}")
                    return None, model
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                interview_logger.log_error(f"API error with {model}: {error_msg}")
                return None, model
                
        except requests.exceptions.Timeout:
            interview_logger.log_error(f"Timeout with model {model}")
            return None, model
        except requests.exceptions.RequestException as e:
            interview_logger.log_error(f"Request error with {model}: {e}")
            return None, model
        except Exception as e:
            interview_logger.log_error(f"Unexpected error with {model}: {e}")
            return None, model
    
    def _enhance_question(self, question: str) -> str:
        """Enhance question with context cues"""
        enhanced = question.strip()
        
        # Add context cues for better responses
        if len(enhanced) < 20:
            enhanced = f"Please provide a comprehensive answer to: {enhanced}"
        
        return enhanced
    
    def _get_cache_key(self, question: str, context: str) -> str:
        """Generate cache key for question"""
        # Simple normalization
        normalized = question.lower().strip()
        # Remove common question words that don't affect meaning
        words_to_remove = ["can", "you", "please", "what", "is", "the", "how", "do", "does"]
        words = normalized.split()
        key_words = [w for w in words if w not in words_to_remove and len(w) > 2]
        return f"{context}:{'_'.join(key_words[:5])}"  # Use first 5 meaningful words
    
    def _get_cached_response(self, cache_key: str) -> Optional[Tuple[str, str]]:
        """Get cached response if available"""
        with self.cache_lock:
            return self.response_cache.get(cache_key)
    
    def _cache_response(self, cache_key: str, response_data: Tuple[str, str]):
        """Cache response with simple LRU eviction"""
        with self.cache_lock:
            # Simple cache size limit
            if len(self.response_cache) > 50:
                # Remove oldest entries (simple FIFO)
                keys_to_remove = list(self.response_cache.keys())[:10]
                for key in keys_to_remove:
                    del self.response_cache[key]
            
            self.response_cache[cache_key] = response_data
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        avg_response_time = (self.total_response_time / self.request_count 
                           if self.request_count > 0 else 0)
        
        return {
            "total_requests": self.request_count,
            "avg_response_time": round(avg_response_time, 2),
            "cache_size": len(self.response_cache),
            "cache_hit_rate": 0  # Could implement if needed
        }
    
    def clear_cache(self):
        """Clear response cache"""
        with self.cache_lock:
            self.response_cache.clear()
            interview_logger.log_info("Response cache cleared")