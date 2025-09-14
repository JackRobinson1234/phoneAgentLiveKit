import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

class Intent(Enum):
    """User intent enumeration"""
    SCHEDULE_APPOINTMENT = "schedule_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"
    RESCHEDULE_APPOINTMENT = "reschedule_appointment"
    CHECK_AVAILABILITY = "check_availability"
    GET_INFO = "get_info"
    GREETING = "greeting"
    GOODBYE = "goodbye"
    UNKNOWN = "unknown"

class NLPProcessor:
    """Natural Language Processing utilities for the health agent"""
    
    def __init__(self):
        self.intent_keywords = {
            Intent.SCHEDULE_APPOINTMENT: [
                'schedule', 'book', 'appointment', 'see doctor', 'visit', 
                'make appointment', 'need appointment', 'want to see'
            ],
            Intent.CANCEL_APPOINTMENT: [
                'cancel', 'cancel appointment', 'remove appointment', 'delete appointment'
            ],
            Intent.RESCHEDULE_APPOINTMENT: [
                'reschedule', 'change appointment', 'move appointment', 'different time'
            ],
            Intent.CHECK_AVAILABILITY: [
                'available', 'availability', 'free', 'open slots', 'when can'
            ],
            Intent.GET_INFO: [
                'information', 'info', 'tell me about', 'what is', 'how does'
            ],
            Intent.GREETING: [
                'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening'
            ],
            Intent.GOODBYE: [
                'goodbye', 'bye', 'see you', 'thank you', 'thanks', 'done', 'finished'
            ]
        }
        
        self.appointment_types = {
            'consultation': ['consultation', 'consult', 'see doctor', 'talk to doctor'],
            'checkup': ['checkup', 'check-up', 'routine', 'physical', 'exam'],
            'follow-up': ['follow-up', 'followup', 'follow up', 'return visit'],
            'vaccination': ['vaccination', 'vaccine', 'shot', 'immunization'],
            'procedure': ['procedure', 'surgery', 'operation', 'treatment']
        }
        
        self.specialties = {
            'general practice': ['general', 'family doctor', 'primary care', 'gp'],
            'cardiology': ['heart', 'cardiology', 'cardiologist', 'cardiac'],
            'dermatology': ['skin', 'dermatology', 'dermatologist', 'rash'],
            'pediatrics': ['pediatrics', 'pediatrician', 'children', 'kids', 'child']
        }
        
        self.urgency_keywords = {
            'urgent': ['urgent', 'emergency', 'asap', 'immediately', 'right away'],
            'soon': ['soon', 'quickly', 'this week', 'next few days'],
            'flexible': ['flexible', 'whenever', 'any time', 'no rush']
        }
    
    def extract_intent(self, text: str) -> Intent:
        """Extract user intent from text"""
        text_lower = text.lower()
        
        # Score each intent based on keyword matches
        intent_scores = {}
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                intent_scores[intent] = score
        
        # Return the intent with the highest score
        if intent_scores:
            return max(intent_scores.items(), key=lambda x: x[1])[0]
        
        return Intent.UNKNOWN
    
    def extract_appointment_type(self, text: str) -> Optional[str]:
        """Extract appointment type from text"""
        text_lower = text.lower()
        
        for apt_type, keywords in self.appointment_types.items():
            if any(keyword in text_lower for keyword in keywords):
                return apt_type
        
        return None
    
    def extract_specialty(self, text: str) -> Optional[str]:
        """Extract medical specialty from text"""
        text_lower = text.lower()
        
        for specialty, keywords in self.specialties.items():
            if any(keyword in text_lower for keyword in keywords):
                return specialty
        
        return None
    
    def extract_doctor_name(self, text: str) -> Optional[str]:
        """Extract doctor name from text"""
        # Look for patterns like "Dr. Smith" or "Doctor Johnson"
        patterns = [
            r'dr\.?\s+([a-zA-Z]+)',
            r'doctor\s+([a-zA-Z]+)',
            r'see\s+([a-zA-Z]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1).title()
        
        return None
    
    def extract_urgency(self, text: str) -> str:
        """Extract urgency level from text"""
        text_lower = text.lower()
        
        for urgency, keywords in self.urgency_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return urgency
        
        return 'normal'
    
    def extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
        """Extract email and phone number from text"""
        result = {'email': None, 'phone': None}
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, text)
        if email_match:
            result['email'] = email_match.group()
        
        # Phone pattern (various formats)
        phone_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # 123-456-7890 or 123.456.7890 or 1234567890
            r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',   # (123) 456-7890
            r'\+1[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}'  # +1-123-456-7890
        ]
        
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text)
            if phone_match:
                result['phone'] = phone_match.group()
                break
        
        return result
    
    def extract_name(self, text: str) -> Optional[str]:
        """Extract person name from text"""
        # Simple name extraction - look for capitalized words
        # This is a basic implementation; in production, you'd use NER
        
        # Remove common non-name words
        stop_words = {'i', 'am', 'my', 'name', 'is', 'the', 'a', 'an', 'and', 'or', 'but'}
        
        words = text.split()
        name_words = []
        
        for word in words:
            # Clean word of punctuation
            clean_word = re.sub(r'[^\w]', '', word)
            
            # Check if it looks like a name (capitalized, not a stop word)
            if (clean_word and 
                clean_word[0].isupper() and 
                clean_word.lower() not in stop_words and
                len(clean_word) > 1):
                name_words.append(clean_word)
        
        if name_words:
            return ' '.join(name_words[:2])  # Take up to 2 words for name
        
        return None
    
    def extract_time_preferences(self, text: str) -> Dict[str, any]:
        """Extract time-related preferences from text"""
        preferences = {
            'time_of_day': None,
            'day_preference': None,
            'flexibility': 'normal'
        }
        
        text_lower = text.lower()
        
        # Time of day preferences
        if any(word in text_lower for word in ['morning', 'am', 'early']):
            preferences['time_of_day'] = 'morning'
        elif any(word in text_lower for word in ['afternoon', 'pm', 'lunch']):
            preferences['time_of_day'] = 'afternoon'
        elif any(word in text_lower for word in ['evening', 'late', 'after work']):
            preferences['time_of_day'] = 'evening'
        
        # Day preferences
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in days:
            if day in text_lower:
                preferences['day_preference'] = day
                break
        
        # Flexibility
        if any(word in text_lower for word in ['flexible', 'any time', 'whenever']):
            preferences['flexibility'] = 'flexible'
        elif any(word in text_lower for word in ['specific', 'only', 'must be']):
            preferences['flexibility'] = 'strict'
        
        return preferences
    
    def calculate_confidence(self, text: str, extracted_data: Dict) -> float:
        """Calculate confidence score for extracted information"""
        confidence = 0.0
        total_checks = 0
        
        # Check if we found clear intent
        if extracted_data.get('intent') != Intent.UNKNOWN:
            confidence += 0.3
        total_checks += 1
        
        # Check if we found specific entities
        entities = ['appointment_type', 'specialty', 'doctor_name', 'contact_info']
        found_entities = sum(1 for entity in entities if extracted_data.get(entity))
        confidence += (found_entities / len(entities)) * 0.4
        
        # Check text length and complexity
        word_count = len(text.split())
        if word_count >= 3:
            confidence += 0.2
        elif word_count >= 1:
            confidence += 0.1
        
        # Penalize very short or unclear responses
        if word_count < 2 or len(text.strip()) < 3:
            confidence *= 0.5
        
        return min(confidence, 1.0)
    
    def process_input(self, text: str) -> Dict[str, any]:
        """
        Process user input and extract all relevant information
        
        Returns:
            Dictionary containing extracted information and confidence score
        """
        if not text or not text.strip():
            return {
                'intent': Intent.UNKNOWN,
                'confidence': 0.0,
                'raw_text': text
            }
        
        # Clean input
        clean_text = text.strip()
        
        # Extract all information
        result = {
            'raw_text': clean_text,
            'intent': self.extract_intent(clean_text),
            'appointment_type': self.extract_appointment_type(clean_text),
            'specialty': self.extract_specialty(clean_text),
            'doctor_name': self.extract_doctor_name(clean_text),
            'urgency': self.extract_urgency(clean_text),
            'contact_info': self.extract_contact_info(clean_text),
            'name': self.extract_name(clean_text),
            'time_preferences': self.extract_time_preferences(clean_text)
        }
        
        # Calculate confidence
        result['confidence'] = self.calculate_confidence(clean_text, result)
        
        return result
