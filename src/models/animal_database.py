from typing import List, Optional, Dict
from datetime import datetime, timedelta
import uuid

from .case import Case, CaseType, CaseStatus

class MockAnimalDatabase:
    """Mock database implementation for the animal control agent system"""
    
    def __init__(self):
        self.cases: Dict[str, Case] = {}
        self._populate_sample_data()
    
    def _populate_sample_data(self):
        """Populate the database with sample data"""
        # Sample cases
        sample_cases = [
            Case(
                id="case_001",
                case_type=CaseType.EMERGENCY,
                animal_type="Dog",
                location="123 Main St, Downtown",
                reporter_name="John Smith",
                reporter_contact="(555) 123-4567",
                description="Injured dog on the side of the road",
                status=CaseStatus.IN_PROGRESS,
                details={
                    "condition": "Injured leg",
                    "contained": "Yes",
                    "priority": "High"
                }
            ),
            Case(
                id="case_002",
                case_type=CaseType.FOUND,
                animal_type="Cat",
                location="Central Park, near the fountain",
                reporter_name="Maria Garcia",
                reporter_contact="maria.garcia@email.com",
                description="Found a tabby cat with a blue collar",
                status=CaseStatus.SUBMITTED,
                details={
                    "color": "Brown tabby",
                    "collar": "Blue with no tag",
                    "finder_can_keep": "No"
                }
            ),
            Case(
                id="case_003",
                case_type=CaseType.LOST,
                animal_type="Dog",
                location="Oakwood neighborhood, near the elementary school",
                reporter_name="David Kim",
                reporter_contact="(555) 987-6543",
                description="Lost golden retriever named Max",
                status=CaseStatus.SUBMITTED,
                details={
                    "name": "Max",
                    "color": "Golden",
                    "age": "5 years",
                    "microchipped": "Yes",
                    "last_seen": "Yesterday evening"
                }
            )
        ]
        
        for case in sample_cases:
            self.cases[case.id] = case
    
    # Case operations
    def get_case(self, case_id: str) -> Optional[Case]:
        """Get a case by ID"""
        return self.cases.get(case_id)
    
    def get_cases_by_type(self, case_type: CaseType) -> List[Case]:
        """Get all cases of a specific type"""
        return [case for case in self.cases.values() 
                if case.case_type == case_type]
    
    def get_cases_by_status(self, status: CaseStatus) -> List[Case]:
        """Get all cases with a specific status"""
        return [case for case in self.cases.values() 
                if case.status == status]
    
    def get_all_cases(self) -> List[Case]:
        """Get all cases"""
        return list(self.cases.values())
    
    def create_case(self, case_type: CaseType, animal_type: str, location: str, 
                   reporter_name: Optional[str] = None, reporter_contact: Optional[str] = None,
                   description: Optional[str] = None, details: Optional[Dict] = None) -> Case:
        """Create a new case"""
        case_id = f"case_{uuid.uuid4().hex[:8]}"
        case = Case(
            id=case_id,
            case_type=case_type,
            animal_type=animal_type,
            location=location,
            reporter_name=reporter_name,
            reporter_contact=reporter_contact,
            description=description,
            details=details
        )
        self.cases[case_id] = case
        return case
    
    def update_case_status(self, case_id: str, status: CaseStatus) -> bool:
        """Update a case's status"""
        case = self.get_case(case_id)
        if not case:
            return False
        
        case.update_status(status)
        return True
    
    def add_case_details(self, case_id: str, key: str, value: str) -> bool:
        """Add details to a case"""
        case = self.get_case(case_id)
        if not case:
            return False
        
        case.add_details(key, value)
        return True
    
    def find_matching_lost_pets(self, found_case: Case) -> List[Case]:
        """Find potential matches for a found animal in lost pet reports"""
        if found_case.case_type != CaseType.FOUND:
            return []
        
        lost_cases = self.get_cases_by_type(CaseType.LOST)
        matches = []
        
        for lost_case in lost_cases:
            # Simple matching algorithm - in a real system this would be more sophisticated
            if lost_case.animal_type.lower() == found_case.animal_type.lower():
                # Check for location proximity (simplified)
                if self._is_location_nearby(lost_case.location, found_case.location):
                    matches.append(lost_case)
        
        return matches
    
    def find_matching_found_pets(self, lost_case: Case) -> List[Case]:
        """Find potential matches for a lost animal in found pet reports"""
        if lost_case.case_type != CaseType.LOST:
            return []
        
        found_cases = self.get_cases_by_type(CaseType.FOUND)
        matches = []
        
        for found_case in found_cases:
            # Simple matching algorithm - in a real system this would be more sophisticated
            if found_case.animal_type.lower() == lost_case.animal_type.lower():
                # Check for location proximity (simplified)
                if self._is_location_nearby(found_case.location, lost_case.location):
                    matches.append(found_case)
        
        return matches
    
    def _is_location_nearby(self, location1: str, location2: str) -> bool:
        """
        Determine if two locations are nearby
        This is a simplified implementation - a real system would use geocoding and distance calculation
        """
        # For demo purposes, just check if any words match between the locations
        words1 = set(location1.lower().split())
        words2 = set(location2.lower().split())
        
        # If there's any overlap in the words, consider them nearby
        return len(words1.intersection(words2)) > 0
    
    # Statistics
    def get_statistics(self) -> Dict:
        """Get statistics about cases in the database"""
        all_cases = self.get_all_cases()
        
        return {
            'total_cases': len(all_cases),
            'emergency_cases': len([c for c in all_cases if c.case_type == CaseType.EMERGENCY]),
            'found_reports': len([c for c in all_cases if c.case_type == CaseType.FOUND]),
            'lost_reports': len([c for c in all_cases if c.case_type == CaseType.LOST]),
            'surrenders_scheduled': len([c for c in all_cases if c.case_type == CaseType.SURRENDER]),
            'active_cases': len([c for c in all_cases if c.status != CaseStatus.CLOSED and c.status != CaseStatus.CANCELLED]),
            'resolved_cases': len([c for c in all_cases if c.status == CaseStatus.RESOLVED])
        }
