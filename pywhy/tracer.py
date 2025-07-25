"""
Core tracing functionality for Python Whyline.
Inspired by the original Whyline's tracing system.
"""

import threading
import inspect
from typing import Any, List, Dict
from collections import defaultdict
import pickle
from .events import EventType, TraceEvent

class WhylineTracer:
    """
       Main tracing class that records execution events.
       In comparison to the instrumenter this injected into the code at runtime.
       
        This class is thread-safe and can be used to record events across multiple threads.
         
        After injection and execution, the tracer can be used to retrieve the events for the given code. 
    """
    
    def __init__(self):
        self.events: List[TraceEvent] = []
        self.event_id_counter = 0
        self.lock = threading.Lock()
        self.object_ids: Dict[id, int] = {}
        self.next_object_id = 1
        self.enabled = True
        
    def get_next_event_id(self) -> int:
        """Get the next unique event ID"""
        with self.lock:
            self.event_id_counter += 1
            return self.event_id_counter
    
    def get_object_id(self, obj: Any) -> int:
        """Get or create a unique ID for an object"""
        obj_id = id(obj)
        if obj_id not in self.object_ids:
            self.object_ids[obj_id] = self.next_object_id
            self.next_object_id += 1
        return self.object_ids[obj_id]
    
    def record_event(self, event_id: int, filename: str, lineno: int, 
                    event_type, *args, **kwargs):
        """Record an instrumentation event"""
        if not self.enabled:
            return
            
        # Convert string event type to EventType enum if needed
        if isinstance(event_type, str):
            event_type = EventType(event_type)
            
        # Get the calling frame to access variables
        frame = inspect.currentframe()
        try:
            # Go up the stack to find the user's frame
            while frame and frame.f_code.co_filename == __file__:
                frame = frame.f_back
            
            if frame is None:
                return
            
            # Build data dict from args and kwargs for unified structure
            data = {}
            if kwargs:
                data.update(kwargs)
            if args:
                # Convert args tuple to proper data dictionary format
                # Args come as: ('var_name', 'x', 'value', 10) -> {'var_name': 'x', 'value': 10}
                for i in range(0, len(args), 2):
                    if i + 1 < len(args):
                        key = args[i]
                        value = args[i + 1]
                        data[key] = value
                
            event = TraceEvent(
                event_id=event_id,
                filename=filename,
                lineno=lineno,
                event_type=event_type,
                data=data,
                # Runtime context will be auto-populated by __post_init__
                locals_snapshot=frame.f_locals.copy(),
                globals_snapshot={k: v for k, v in frame.f_globals.items() 
                                if not k.startswith('__') and not callable(v)}
            )
            
            with self.lock:
                self.events.append(event)
                
        finally:
            del frame
    
    def get_variable_history(self, var_name: str, filename: str = None) -> List[TraceEvent]:
        """Get history of a variable's assignments"""
        history = []
        for event in self.events:
            if (event.event_type == EventType.ASSIGN and 
                var_name in event.locals_snapshot and
                (filename is None or event.filename == filename)):
                history.append(event)
        return history
    
    def get_line_executions(self, filename: str, lineno: int) -> List[TraceEvent]:
        """Get all events that occurred on a specific line"""
        return [event for event in self.events 
                if event.filename == filename and event.lineno == lineno]
    
    def get_function_calls(self, func_name: str = None) -> List[TraceEvent]:
        """Get all function call events"""
        calls = []
        for event in self.events:
            if event.event_type in [EventType.FUNCTION_ENTRY, EventType.CALL]:
                if func_name is None or event.get_func_name() == func_name:
                    calls.append(event)
        return calls
    
    def get_events_in_range(self, start_line: int, end_line: int, 
                           filename: str = None) -> List[TraceEvent]:
        """Get events within a line range"""
        return [event for event in self.events
                if start_line <= event.lineno <= end_line and
                (filename is None or event.filename == filename)]
    
    def save_trace(self, filename: str):
        """Save trace to file"""
        with open(filename, 'wb') as f:
            pickle.dump(self.events, f)
    
    def load_trace(self, filename: str):
        """Load trace from file"""
        with open(filename, 'rb') as f:
            self.events = pickle.load(f)
    
    def clear(self):
        """Clear all recorded events"""
        with self.lock:
            self.events.clear()
            self.event_id_counter = 0
    
    def enable(self):
        """Enable tracing"""
        self.enabled = True
    
    def disable(self):
        """Disable tracing"""
        self.enabled = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tracing statistics"""
        event_types = defaultdict(int)
        files = set()
        
        for event in self.events:
            event_types[event.event_type] += 1
            files.add(event.filename)
        
        return {
            'total_events': len(self.events),
            'event_types': dict(event_types),
            'files_traced': len(files),
            'time_span': (self.events[-1].timestamp - self.events[0].timestamp) 
                        if self.events else 0
        }


# Global tracer instance
_whyline_tracer = WhylineTracer()


def get_tracer() -> WhylineTracer:
    """Get the global tracer instance"""
    return _whyline_tracer


def start_tracing():
    """Start tracing execution"""
    _whyline_tracer.enable()


def stop_tracing():
    """Stop tracing execution"""
    _whyline_tracer.disable()


def clear_trace():
    """Clear all recorded trace events"""
    _whyline_tracer.clear()


def save_trace(filename: str):
    """Save current trace to file"""
    _whyline_tracer.save_trace(filename)


def load_trace(filename: str):
    """Load trace from file"""
    _whyline_tracer.load_trace(filename)
