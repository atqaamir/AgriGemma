from enum import Enum


class Status(Enum):
    SUCCESS = "Success"
    FAILED = "Failed"


class ChangeStatus(Enum):
    NO_CHANGE = "No Change"
    NO_IMPACT = "Change_No_Impact"
    IMPACT_PLAN = "Change_Impact_Plan"
    IMPACT_TASKS = "Change_Impact_Tasks"


class Region(Enum):
    LAHORE = "lahore"
    KARACHI = "karachi"
    ISLAMABAD = "islamabad"


class NotificationType(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    RECOMMENDATION = "recommendation"
    CHANGE = "change"  # triggers a popup on creation/unread


class IntelligencePriorityLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
