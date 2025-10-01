import re
from typing import Optional
from datetime import datetime

class InputValidator:
    """Utility class for validating user inputs"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.strip()))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        # Remove common separators and spaces
        cleaned = re.sub(r'[\s\-\(\)\.]+', '', phone)
        
        # Check for valid US phone number patterns
        patterns = [
            r'^\d{10}$',  # 1234567890
            r'^1\d{10}$',  # 11234567890
            r'^\+1\d{10}$'  # +11234567890
        ]
        
        return any(re.match(pattern, cleaned) for pattern in patterns)
    
    @staticmethod
    def validate_name(name: str) -> bool:
        """Validate name format"""
        name = name.strip()
        if len(name) < 2:
            return False
        
        # Allow letters, spaces, hyphens, and apostrophes
        pattern = r"^[a-zA-Z\s\-']+$"
        return bool(re.match(pattern, name))
    
    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize phone number to standard format"""
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        # Remove leading 1 if present (US country code)
        if len(digits) == 11 and digits.startswith('1'):
            digits = digits[1:]
        
        # Format as (XXX) XXX-XXXX
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        
        return phone  # Return original if can't normalize
    
    @staticmethod
    def validate_appointment_datetime(dt: datetime) -> tuple[bool, Optional[str]]:
        """
        Validate appointment datetime
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        now = datetime.now()
        
        # Check if in the future
        if dt <= now:
            return False, "Appointment must be scheduled for a future date and time."
        
        # Check if too far in advance (e.g., more than 6 months)
        max_advance = now.replace(year=now.year + (now.month + 6) // 12, 
                                 month=(now.month + 6) % 12 or 12)
        if dt > max_advance:
            return False, "Appointments can only be scheduled up to 6 months in advance."
        
        # Check if during reasonable hours (6 AM to 10 PM)
        if dt.hour < 6 or dt.hour >= 22:
            return False, "Appointments can only be scheduled between 6:00 AM and 10:00 PM."
        
        # Check if on weekend (optional business rule)
        if dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False, "Appointments are only available Monday through Friday."
        
        return True, None
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input by removing potentially harmful content"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove potentially harmful characters (basic sanitization)
        text = re.sub(r'[<>\"\'&]', '', text)
        
        return text[:500]  # Limit length to prevent abuse
