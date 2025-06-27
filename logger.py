import logging
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
from config import CONFIG

class InterviewLogger:
    """Handles logging of questions, answers, and system events"""
    
    def __init__(self):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.qa_log_file = os.path.join(CONFIG.LOG_PATH, f"qa_session_{self.session_id}.json")
        self.system_log_file = os.path.join(CONFIG.LOG_PATH, f"system_{self.session_id}.log")
        
        # Setup system logger
        self.logger = logging.getLogger('StealtAI')
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(self.system_log_file)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Console handler for debugging
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        self.logger.addHandler(console_handler)
        
        self.qa_data = []
        
    def log_qa(self, question: str, answer: str, model_used: str, 
               response_time: float, confidence: Optional[float] = None):
        """Log question-answer pair"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": answer,
            "model_used": model_used,
            "response_time_ms": round(response_time * 1000, 2),
            "confidence": confidence
        }
        
        self.qa_data.append(entry)
        
        # Save to file immediately
        with open(self.qa_log_file, 'w', encoding='utf-8') as f:
            json.dump(self.qa_data, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"Q&A logged: {len(question)} chars question, {len(answer)} chars answer")
    
    def log_error(self, error: str, context: Optional[Dict[str, Any]] = None):
        """Log system errors"""
        self.logger.error(f"Error: {error} | Context: {context}")
    
    def log_info(self, message: str):
        """Log informational messages"""
        self.logger.info(message)
    
    def log_warning(self, message: str):
        """Log warnings"""
        self.logger.warning(message)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session"""
        if not self.qa_data:
            return {"total_questions": 0, "avg_response_time": 0}
        
        total_questions = len(self.qa_data)
        avg_response_time = sum(entry["response_time_ms"] for entry in self.qa_data) / total_questions
        
        return {
            "session_id": self.session_id,
            "total_questions": total_questions,
            "avg_response_time_ms": round(avg_response_time, 2),
            "models_used": list(set(entry["model_used"] for entry in self.qa_data)),
            "session_duration": (datetime.now() - datetime.fromisoformat(self.qa_data[0]["timestamp"])).total_seconds() if self.qa_data else 0
        }

# Global logger instance
interview_logger = InterviewLogger()