from enum import Enum, auto

class StateEnum(Enum):
    """Enum of all available states in the animal control system"""
    GREETING = "GREETING"
    EMERGENCY_CASE = "EMERGENCY_CASE"
    REPORT_FOUND = "REPORT_FOUND"
    REPORT_LOST = "REPORT_LOST"
    PET_SURRENDER = "PET_SURRENDER"
    SCHEDULE_SURRENDER = "SCHEDULE_SURRENDER"
    GENERAL_INFO = "GENERAL_INFO"
    CASE_CONFIRMATION = "CASE_CONFIRMATION"
    CASE_COMPLETE = "CASE_COMPLETE"
    ERROR_HANDLING = "ERROR_HANDLING"
    FINAL_SUMMARY = "FINAL_SUMMARY"
    
    @classmethod
    def get_valid_states(cls):
        """Returns a list of all valid state names as strings"""
        return [state.value for state in cls]
    
    @classmethod
    def is_valid_state(cls, state_name):
        """Check if a state name is valid"""
        return state_name in cls.get_valid_states()
    
    @classmethod
    def get_next_state_options(cls, current_state):
        """Get valid next states based on the current state"""
        # Define valid transitions for each state
        transitions = {
            cls.GREETING.value: [
                cls.EMERGENCY_CASE.value,
                cls.REPORT_FOUND.value,
                cls.REPORT_LOST.value,
                cls.PET_SURRENDER.value,
                cls.GENERAL_INFO.value,
                cls.ERROR_HANDLING.value
            ],
            cls.EMERGENCY_CASE.value: [
                cls.CASE_CONFIRMATION.value,
                cls.ERROR_HANDLING.value
            ],
            cls.REPORT_FOUND.value: [
                cls.CASE_CONFIRMATION.value,
                cls.ERROR_HANDLING.value
            ],
            cls.REPORT_LOST.value: [
                cls.CASE_CONFIRMATION.value,
                cls.ERROR_HANDLING.value
            ],
            cls.PET_SURRENDER.value: [
                cls.SCHEDULE_SURRENDER.value,
                cls.ERROR_HANDLING.value
            ],
            cls.SCHEDULE_SURRENDER.value: [
                cls.CASE_CONFIRMATION.value,
                cls.ERROR_HANDLING.value
            ],
            cls.GENERAL_INFO.value: [
                cls.CASE_CONFIRMATION.value,
                cls.ERROR_HANDLING.value
            ],
            cls.CASE_CONFIRMATION.value: [
                cls.CASE_COMPLETE.value,
                cls.ERROR_HANDLING.value
            ],
            cls.CASE_COMPLETE.value: [
                cls.FINAL_SUMMARY.value,
                cls.GREETING.value  # Allow restarting
            ],
            cls.ERROR_HANDLING.value: [
                cls.GREETING.value,
                cls.FINAL_SUMMARY.value
            ],
            cls.FINAL_SUMMARY.value: [
                cls.GREETING.value  # Allow restarting
            ]
        }
        
        return transitions.get(current_state, [])
