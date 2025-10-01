"""
Configuration settings for the Animal Control API
Supports both local development and Railway deployment
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# API settings
API_HOST = os.environ.get('API_HOST', '0.0.0.0')
API_PORT = int(os.environ.get('PORT', 5001))
DEBUG_MODE = os.environ.get('DEBUG', 'False').lower() == 'true'

# OpenAI API settings
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4')

# Railway deployment URL (for client configuration)
RAILWAY_URL = os.environ.get('RAILWAY_URL', '')

# Get the base URL for the API
def get_api_base_url():
    """Get the base URL for the API based on the environment"""
    if RAILWAY_URL:
        return RAILWAY_URL
    else:
        return f"http://localhost:{API_PORT}"
LLM_CONFIG = {
    'provider': 'openrouter',
    'api_base_url': 'https://openrouter.ai/api/v1',
    'model': 'anthropic/claude-3.5-sonnet',  # Default model
    'temperature': 0.7,
    'max_tokens': 1000,
    'timeout': 30,
    'retry_attempts': 3,
    'use_tools': True,
    'fallback_model': 'openai/gpt-3.5-turbo',
}