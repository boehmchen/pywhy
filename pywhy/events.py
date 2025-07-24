"""
Shared event type definitions for Python Whyline tracing system.
"""

from enum import StrEnum


class EventType(StrEnum):
    """Types of trace events that can be recorded during execution"""
    ASSIGN = "assign"
    ATTR_ASSIGN = "attr_assign"  
    SUBSCRIPT_ASSIGN = "subscript_assign"
    SLICE_ASSIGN = "slice_assign"
    AUG_ASSIGN = "aug_assign"
    FUNCTION_ENTRY = "function_entry"
    RETURN = "return"
    CONDITION = "condition"
    BRANCH = "branch"
    LOOP_ITERATION = "loop_iteration"
    WHILE_CONDITION = "while_condition"
    CALL = "call"
    # Future event types (not yet implemented)
    # EXCEPTION = "exception"
    # IMPORT = "import"