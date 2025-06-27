import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import patch, MagicMock
from ai_handler import AIResponseHandler

@pytest.fixture
def ai_handler():
    return AIResponseHandler()

@patch('ai_handler.requests.Session.post')
def test_get_response_cache_and_fallback(mock_post, ai_handler):
    # Setup mock response for primary model
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Test response"}}]
    }
    mock_post.return_value = mock_response

    question = "What is AI?"
    context = "general"

    # First call should call API and cache response
    response, model_used, response_time = ai_handler.get_response(question, context)
    assert response == "Test response"
    assert model_used in ["openai/gpt-4-turbo", "fallback", "openai/gpt-3.5-turbo"]

    # Second call should use cache
    response2, model_used2, _ = ai_handler.get_response(question, context)
    assert response2 == response
    assert model_used2 == model_used

@patch('ai_handler.requests.Session.post')
def test_get_response_api_failure_then_fallback(mock_post, ai_handler):
    # Setup mock to fail primary model and succeed fallback
    def side_effect(*args, **kwargs):
        if kwargs['json']['model'] == 'primary_model':
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.text = "Server error"
            return mock_resp
        else:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "Fallback response"}}]
            }
            return mock_resp

    mock_post.side_effect = side_effect

    response, model_used, _ = ai_handler.get_response("Test question", "general")
    assert response == "Fallback response"
    assert model_used != "primary_model"

def test_cache_clearing(ai_handler):
    ai_handler.response_cache['key'] = ('response', 'model')
    ai_handler.clear_cache()
    assert len(ai_handler.response_cache) == 0
