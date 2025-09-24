"""
Twilio configuration settings for optimized speech recognition
"""

# Default Gather parameters for faster API posting
DEFAULT_GATHER_PARAMS = {
    'speech_timeout': '1.5',  # Shorter timeout for faster endpoint detection
    'timeout': 3,             # Shorter overall timeout
    'enhanced': True,         # Enhanced speech recognition
    'speechModel': 'phone_call',  # Optimized for phone calls
    'speechEndThreshold': 500,    # End detection threshold in milliseconds
    'bargeIn': True,          # Allow user to interrupt
    'profanityFilter': False  # Allow natural speech
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
