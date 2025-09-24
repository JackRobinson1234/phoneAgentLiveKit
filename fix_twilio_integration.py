"""
Script to fix the timeout_url attributes in twilio_integration.py
"""

import re
import os

def fix_timeout_url_attributes():
    """Remove timeout_url attributes from Gather elements in twilio_integration.py"""
    
    # Path to the file
    file_path = '/Users/jackrobinson/wrapperAndAgent/phoneAgent/twilio_integration.py'
    
    # Read the file content
    with open(file_path, 'r') as file:
        content = file.read()
    
    # Replace timeout_url attributes
    # This pattern matches 'timeout_url='/timeout_handler',' or similar variations
    pattern = r"timeout_url\s*=\s*['\"][^'\"]+['\"],?"
    fixed_content = re.sub(pattern, "# timeout_url removed - not supported by Twilio Gather", content)
    
    # Write the fixed content back to the file
    with open(file_path, 'w') as file:
        file.write(fixed_content)
    
    print(f"✅ Fixed timeout_url attributes in {file_path}")

if __name__ == "__main__":
    fix_timeout_url_attributes()
