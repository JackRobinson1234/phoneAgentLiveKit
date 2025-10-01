from datetime import datetime, timedelta
from typing import Optional
import re
from dateutil import parser

class DateTimeParser:
    """Utility class for parsing natural language date and time expressions"""
    
    def __init__(self):
        self.relative_day_mapping = {
            'today': 0,
            'tomorrow': 1,
            'day after tomorrow': 2,
            'next week': 7,
        }
        
        self.day_name_mapping = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        self.time_keywords = {
            'morning': 9,
            'afternoon': 14,
            'evening': 18,
            'noon': 12,
            'midnight': 0
        }
    
    def parse_datetime(self, input_str: str) -> Optional[datetime]:
        """
        Parse a natural language datetime string into a datetime object.
        
        Args:
            input_str: Natural language datetime string
            
        Returns:
            Parsed datetime object or None if parsing fails
        """
        input_str = input_str.lower().strip()
        
        try:
            # Try relative date parsing first
            parsed_dt = self._parse_relative_datetime(input_str)
            if parsed_dt:
                return parsed_dt
            
            # Try day name parsing
            parsed_dt = self._parse_day_name_datetime(input_str)
            if parsed_dt:
                return parsed_dt
            
            # Fall back to dateutil parser
            return parser.parse(input_str, fuzzy=True)
            
        except Exception:
            return None
    
    def _parse_relative_datetime(self, input_str: str) -> Optional[datetime]:
        """Parse relative date expressions like 'tomorrow at 2pm'"""
        now = datetime.now()
        
        # Check for relative day keywords
        for keyword, days_offset in self.relative_day_mapping.items():
            if keyword in input_str:
                base_date = now + timedelta(days=days_offset)
                
                # Extract time if provided
                time_part = self._extract_time(input_str)
                if time_part:
                    return base_date.replace(
                        hour=time_part['hour'],
                        minute=time_part['minute'],
                        second=0,
                        microsecond=0
                    )
                else:
                    # Default to 9 AM if no time specified
                    return base_date.replace(hour=9, minute=0, second=0, microsecond=0)
        
        return None
    
    def _parse_day_name_datetime(self, input_str: str) -> Optional[datetime]:
        """Parse day name expressions like 'monday at 3pm'"""
        now = datetime.now()
        
        for day_name, target_weekday in self.day_name_mapping.items():
            if day_name in input_str:
                # Calculate days until target weekday
                current_weekday = now.weekday()
                days_ahead = target_weekday - current_weekday
                
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                
                target_date = now + timedelta(days=days_ahead)
                
                # Extract time if provided
                time_part = self._extract_time(input_str)
                if time_part:
                    return target_date.replace(
                        hour=time_part['hour'],
                        minute=time_part['minute'],
                        second=0,
                        microsecond=0
                    )
                else:
                    # Default to 9 AM if no time specified
                    return target_date.replace(hour=9, minute=0, second=0, microsecond=0)
        
        return None
    
    def _extract_time(self, input_str: str) -> Optional[dict]:
        """Extract time from input string"""
        # Pattern for time like "2pm", "14:30", "2:30 PM"
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)',  # 2:30 pm
            r'(\d{1,2})\s*(am|pm)',          # 2 pm
            r'(\d{1,2}):(\d{2})',            # 14:30
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, input_str.lower())
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2)) if len(match.groups()) >= 2 and match.group(2) else 0
                
                # Handle AM/PM
                if len(match.groups()) >= 3 and match.group(3):
                    period = match.group(3).lower()
                    if period == 'pm' and hour != 12:
                        hour += 12
                    elif period == 'am' and hour == 12:
                        hour = 0
                
                # Validate hour and minute
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return {'hour': hour, 'minute': minute}
        
        # Check for time keywords
        for keyword, default_hour in self.time_keywords.items():
            if keyword in input_str:
                return {'hour': default_hour, 'minute': 0}
        
        return None
    
    def format_datetime(self, dt: datetime) -> str:
        """Format datetime for display"""
        return dt.strftime("%A, %B %d, %Y at %I:%M %p")
    
    def is_business_hours(self, dt: datetime, start_hour: int = 9, end_hour: int = 17) -> bool:
        """Check if datetime falls within business hours"""
        return start_hour <= dt.hour < end_hour
    
    def is_business_day(self, dt: datetime) -> bool:
        """Check if datetime falls on a business day (Monday-Friday)"""
        return dt.weekday() < 5  # 0-4 are Monday-Friday
