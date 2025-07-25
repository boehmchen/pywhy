"""
Shared event type definitions and data structures for Python Whyline tracing system.
"""

import json
import pickle
import time
import threading
from enum import StrEnum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


class EventType(StrEnum):
    """Types of trace events that can be recorded during execution"""
    ASSIGN = "assign"
    ATTR_ASSIGN = "attr_assign"  
    SUBSCRIPT_ASSIGN = "subscript_assign"
    SLICE_ASSIGN = "slice_assign"
    AUG_ASSIGN = "aug_assign"
    FUNCTION_ENTRY = "function_entry"
    RETURN = "return"
    BRANCH = "branch"
    LOOP_ITERATION = "loop_iteration"
    WHILE_CONDITION = "while_condition"
    CALL = "call"
    # Future event types (not yet implemented)
    # EXCEPTION = "exception"
    # IMPORT = "import"


@dataclass
class TraceEvent:
    """Unified trace event that serves both runtime execution and static instrumentation needs.
    
    This class combines the functionality of the previous separate TraceEvent classes
    from tracer.py and instrumenter.py into a single, coherent data structure.
    """
    event_id: int
    filename: str
    lineno: int  # Standardized on 'lineno' (matches Python's traceback conventions)
    event_type: EventType
    
    # Core event data - unified approach using data dict
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Runtime execution context (optional - populated during actual execution)
    timestamp: Optional[float] = None
    thread_id: Optional[int] = None
    locals_snapshot: Dict[str, Any] = field(default_factory=dict)
    globals_snapshot: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize runtime fields and sanitize snapshots if present"""
        # Set runtime fields if not provided
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.thread_id is None:
            self.thread_id = threading.get_ident()
            
        # Sanitize snapshots to avoid circular references and unpicklable objects
        if self.locals_snapshot:
            self.locals_snapshot = self._sanitize_dict(self.locals_snapshot)
        if self.globals_snapshot:
            self.globals_snapshot = self._sanitize_dict(self.globals_snapshot)
    
    def _sanitize_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Remove unpicklable objects and internal variables from snapshots"""
        sanitized = {}
        for k, v in d.items():
            if k.startswith('_whyline_'):
                continue
            try:
                # Test if it's serializable
                pickle.dumps(v)
                sanitized[k] = v
            except (TypeError, pickle.PickleError, AttributeError):
                sanitized[k] = f"<unpicklable: {type(v).__name__}>"
        return sanitized
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation for serialization"""
        return {
            'event_id': self.event_id,
            'filename': self.filename,
            'lineno': self.lineno,  # Standardized field name
            'event_type': str(self.event_type),  # Convert enum to string
            'data': self.data,
            'timestamp': self.timestamp,
            'thread_id': self.thread_id,
            'locals_snapshot': self.locals_snapshot,
            'globals_snapshot': self.globals_snapshot
        }
    
    def to_json(self) -> str:
        """Convert to JSON string representation"""
        return json.dumps(self.to_dict(), indent=2, default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TraceEvent':
        """Create TraceEvent from dictionary representation"""
        # Convert string event_type back to enum if needed
        event_type = data.get('event_type')
        if isinstance(event_type, str):
            event_type = EventType(event_type)
            
        return cls(
            event_id=data['event_id'],
            filename=data['filename'],
            lineno=data['lineno'],
            event_type=event_type,
            data=data.get('data', {}),
            timestamp=data.get('timestamp'),
            thread_id=data.get('thread_id'),
            locals_snapshot=data.get('locals_snapshot', {}),
            globals_snapshot=data.get('globals_snapshot', {})
        )
    
    
    # Convenience methods for common data patterns
    def get_var_name(self) -> Optional[str]:
        """Get variable name for assignment events"""
        return self.data.get('var_name')
    
    def get_value(self) -> Any:
        """Get value for assignment/return events"""
        return self.data.get('value')
    
    def get_func_name(self) -> Optional[str]:
        """Get function name for function entry/call events"""
        return self.data.get('func_name')
    
    def get_condition(self) -> Optional[str]:
        """Get condition text for condition/branch events"""
        return self.data.get('condition') or self.data.get('test')
    
    def get_result(self) -> Any:
        """Get result for condition/branch events"""
        return self.data.get('result') or self.data.get('decision') or self.data.get('taken')