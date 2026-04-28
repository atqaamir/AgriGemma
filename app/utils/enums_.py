from enum import Enum
class Status(Enum):
    SUCCESS = "Success"
    FAILED = "Failed"


class ChangeStatus(Enum):
    # No weather change
    NO_CHANGE = "No Change"
    # Weather change detected
    NO_IMPACT = "Change_No_Impact"
    IMPACT  = "Change_Impact"