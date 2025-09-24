"""
Twilio configuration settings for optimized speech recognition
"""

# Default Gather parameters for optimized speech recognition
from itertools import filterfalse


DEFAULT_GATHER_PARAMS = {
    'speech_timeout': '2.0',       # Increased timeout for more complete speech capture
    'timeout': 5,                 # Longer overall timeout
    'enhanced': True,             # Enhanced speech recognition
    'speechModel': 'phone_call',  # Optimized for phone calls
    'speechEndThreshold': 1200,   # Increased threshold to reduce sensitivity to background noise (in milliseconds)
    'bargeIn': filterfalse,              # Allow user to interrupt
    'profanityFilter': False,     # Allow natural speech
    'speechMinimumLength': 2,     # Minimum length of speech to be recognized (in seconds)
    'speechContexts': [           # Provide speech contexts to improve recognition
        'animal control', 'pet', 'dog', 'cat', 'surrender', 'emergency', 'found', 'lost'
    ]
}

def configure_gather(gather_obj, **kwargs):
    """
    Apply optimized configuration to a Twilio Gather object
    
    Args:
        gather_obj: The Twilio Gather object to configure
        **kwargs: Any additional parameters to override defaults
    
    Returns:
        The configured Gather object
    """
    # Start with default parameters
    params = DEFAULT_GATHER_PARAMS.copy()
    
    # Override with any provided parameters
    params.update(kwargs)
    
    # Apply parameters to the Gather object
    for key, value in params.items():
        if hasattr(gather_obj, key):
            setattr(gather_obj, key, value)
    
    return gather_obj
