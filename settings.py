# Configuration settings for the Health Agent

# Database settings
DATABASE_CONFIG = {
    'type': 'mock',  # Using mock database for this implementation
    'auto_populate': True,  # Populate with sample data on startup
}

# Agent settings
AGENT_CONFIG = {
    'name': 'HealthBot',
    'greeting_message': "Hello! I'm HealthBot, your AI assistant for scheduling doctor appointments. How can I help you today?",
    'max_retries': 3,  # Maximum retries for failed state transitions
    'session_timeout': 1800,  # 30 minutes in seconds
}

# Appointment settings
APPOINTMENT_CONFIG = {
    'default_duration': 30,  # Default appointment duration in minutes
    'business_hours': {
        'start': '09:00',
        'end': '17:00'
    },
    'working_days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
    'advance_booking_days': 30,  # How far in advance appointments can be booked
}

# NLP settings
NLP_CONFIG = {
    'confidence_threshold': 0.7,
    'fallback_to_structured': True,  # Fall back to structured questions if NLP fails
}

# LLM settings for OpenRouter integration
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

# Available models for different use cases
AVAILABLE_MODELS = {
    'conversation': 'anthropic/claude-3.5-sonnet',
    'intent_detection': 'openai/gpt-4o-mini',
    'entity_extraction': 'openai/gpt-4o-mini',
    'response_generation': 'anthropic/claude-3.5-sonnet',
    'fallback': 'openai/gpt-3.5-turbo'
}
