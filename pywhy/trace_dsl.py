"""
Domain-specific language for building trace events.
Provides fluent API for creating trace events in tests and utilities.
"""
import json
from typing import List, Dict, Any, Optional
from .events import TraceEvent, EventType


class TraceEventBuilder:
    """Fluent API for building trace events"""
    
    def __init__(self):
        self.events: List[TraceEvent] = []
        self._current_event_id = 0
        self._filename = "<test>"
        self._line_no = 1
        
    def reset(self) -> 'TraceEventBuilder':
        """Reset the builder state"""
        self.events = []
        self._current_event_id = 0
        return self
        
    def set_filename(self, filename: str) -> 'TraceEventBuilder':
        """Set the default filename for events"""
        self._filename = filename
        return self
        
    def set_line(self, line_no: int) -> 'TraceEventBuilder':
        """Set the default line number for events"""
        self._line_no = line_no
        return self
        
    def _next_event_id(self) -> int:
        """Get next event ID"""
        self._current_event_id += 1
        return self._current_event_id
        
    def _create_event(self, event_type: EventType, data: Dict[str, Any], 
                     line_no: Optional[int] = None) -> TraceEvent:
        """Create a new trace event"""
        event = TraceEvent(
            event_id=self._next_event_id(),
            filename=self._filename,
            lineno=line_no or self._line_no,  # Fixed: should be 'lineno' not 'line_no'
            event_type=event_type,  # Fixed: pass EventType enum directly, not .value
            data=data
        )
        self.events.append(event)
        return event
        
    # Variable assignment events
    def assign(self, var_name: str, value: Any, line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create a variable assignment event"""
        self._create_event(EventType.ASSIGN, {
            'var_name': var_name,
            'value': value
        }, line_no)
        return self
        
    def attr_assign(self, obj_name: str, attr: str, value: Any, 
                   line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create an attribute assignment event"""
        self._create_event(EventType.ATTR_ASSIGN, {
            'obj_attr': attr,
            'obj': obj_name,
            'value': value
        }, line_no)
        return self
        
    def subscript_assign(self, container: str, index: Any, value: Any,
                        line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create a subscript assignment event"""
        self._create_event(EventType.SUBSCRIPT_ASSIGN, {
            'container': container,
            'index': index,
            'value': value
        }, line_no)
        return self
        
    def aug_assign(self, var_name: str, value: Any, line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create an augmented assignment event for variables"""
        self._create_event(EventType.AUG_ASSIGN, {
            'var_name': var_name,
            'value': value
        }, line_no)
        return self
        
    def aug_assign_attr(self, obj_attr: str, obj: Any, value: Any, line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create an augmented assignment event for attributes"""
        self._create_event(EventType.AUG_ASSIGN, {
            'obj_attr': obj_attr,
            'obj': obj,
            'value': value
        }, line_no)
        return self
        
    def aug_assign_subscript(self, container: Any, index: Any, value: Any, line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create an augmented assignment event for subscripts"""
        self._create_event(EventType.AUG_ASSIGN, {
            'container': container,
            'index': index,
            'value': value
        }, line_no)
        return self
        
    def slice_assign(self, container: str, lower: Optional[int], upper: Optional[int], 
                    step: Optional[int], value: Any, line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create a slice assignment event (e.g., arr[1:3] = values)"""
        self._create_event(EventType.SLICE_ASSIGN, {
            'container': container,
            'slice_type': 'slice',
            'lower': lower,
            'upper': upper,
            'step': step,
            'value': value
        }, line_no)
        return self
        
    # Function events
    def function_entry(self, func_name: str, args: List[Any], 
                      line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create a function entry event"""
        self._create_event(EventType.FUNCTION_ENTRY, {
            'func_name': func_name,
            'args': args
        }, line_no)
        return self
        
    def return_event(self, value: Any, line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create a return event"""
        self._create_event(EventType.RETURN, {
            'value': value
        }, line_no)
        return self
        
    def call(self, func_name: str, args: List[Any], line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create a general function call event"""
        self._create_event(EventType.CALL, {
            'func_name': func_name,
            'args': args
        }, line_no)
        return self
        
    # Control flow events
        
    def branch(self, condition: str, result: bool, decision: str, line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create a branch event with integrated condition"""
        self._create_event(EventType.BRANCH, {
            'condition': condition,
            'result': result,
            'decision': decision  # Should be "if_block", "else_block", "elif_block", or "skip_block"
        }, line_no)
        return self
        
    def loop_iteration(self, target: str, iter_value: Any,
                      line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create a loop iteration event"""
        self._create_event(EventType.LOOP_ITERATION, {
            'target': target,
            'iter_value': iter_value
        }, line_no)
        return self
        
    def while_condition(self, condition: str, result: bool, line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create a while condition event"""
        self._create_event(EventType.WHILE_CONDITION, {
            'condition': condition,
            'result': result
        }, line_no)
        return self
        
    # Utility methods
    def build(self) -> List[TraceEvent]:
        """Return the built trace events"""
        return self.events.copy()
        
    def print_events(self) -> None:
        """Print all events in a readable format"""
        for event in self.events:
            print(f"Event #{event.event_id} ({event.event_type}) at {event.filename}:{event.lineno}")
            for key, value in event.data.items():
                print(f"  {key}: {value}")
            print()
            
    def to_json(self) -> str:
        """Convert all events to JSON"""
        return json.dumps([event.to_dict() for event in self.events], indent=2)


class TraceSequence:
    """Higher-level builder for creating common trace patterns with all EventTypes"""
    
    def __init__(self):
        self.builder = TraceEventBuilder()
    
    def simple_assignment(self, var_name: str, value: Any) -> 'TraceSequence':
        """Create a simple assignment"""
        self.builder.assign(var_name, value)
        return self
    
    def function_call(self, func_name: str, args: List[Any], return_value: Any) -> 'TraceSequence':
        """Create a function call with entry and return"""
        self.builder.function_entry(func_name, args)
        self.builder.return_event(return_value)
        return self
    
    def if_statement(self, condition: str, result: bool, 
                    then_assignments: Optional[List[tuple]] = None,
                    else_assignments: Optional[List[tuple]] = None) -> 'TraceSequence':
        """Create an if statement with integrated condition and branch"""
        if result:
            # Condition is true, if block taken
            self.builder.branch(condition, result, "if_block")
            if then_assignments:
                for var_name, value in then_assignments:
                    self.builder.assign(var_name, value)
        else:
            # Condition is false
            if else_assignments:
                # Else block exists and taken
                self.builder.branch(condition, result, "else_block")
                for var_name, value in else_assignments:
                    self.builder.assign(var_name, value)
            else:
                # No else block, skip
                self.builder.branch(condition, result, "skip_block")
        
        return self
    
    def for_loop(self, target: str, values: List[Any], 
                assignments: Optional[List[tuple]] = None) -> 'TraceSequence':
        """Create a for loop with iterations"""
        for value in values:
            self.builder.loop_iteration(target, value)
            if assignments:
                for var_name, _ in assignments:
                    # For demo purposes, just mark as updated
                    self.builder.assign(var_name, "updated")
        return self
    
    def while_loop(self, condition: str, iterations: int, 
                  assignments: Optional[List[tuple]] = None) -> 'TraceSequence':
        """Create a while loop with condition checks"""
        for i in range(iterations):
            self.builder.while_condition(condition, True)
            if assignments:
                for var_name, value in assignments:
                    self.builder.assign(var_name, value)
        # Final condition check that ends the loop
        self.builder.while_condition(condition, False)
        return self
    
    def object_operations(self, obj_name: str) -> 'TraceSequence':
        """Create a sequence demonstrating object operations"""
        # Attribute assignment
        self.builder.attr_assign(obj_name, "name", "test_object")
        self.builder.attr_assign(obj_name, "value", 42)
        
        # Subscript assignment (for dict-like objects)
        self.builder.subscript_assign(obj_name, "key1", "value1")
        self.builder.subscript_assign(obj_name, 0, "first_item")
        
        # Slice assignment
        self.builder.slice_assign(obj_name, 1, 3, None, ["new", "items"])
        
        return self
    
    def complex_assignment_pattern(self, var_name: str) -> 'TraceSequence':
        """Create a sequence showing all assignment types"""
        # Simple assignment
        self.builder.assign(var_name, 100)
        
        # Augmented assignments
        self.builder.aug_assign(var_name, 110)  # After += 10
        self.builder.aug_assign(var_name, 220)  # After *= 2
        self.builder.aug_assign(var_name, 215)  # After -= 5
        self.builder.aug_assign(var_name, 71)   # After //= 3
        
        return self
    
    def function_call_chain(self, functions: List[tuple]) -> 'TraceSequence':
        """Create a chain of function calls with returns
        
        Args:
            functions: List of (func_name, args, return_value) tuples
        """
        for func_name, args, return_value in functions:
            self.builder.call(func_name, args)
            self.builder.return_event(return_value)
        return self
    
    def comprehensive_example(self) -> 'TraceSequence':
        """Create a comprehensive example using all EventTypes"""
        # Variable assignments
        self.simple_assignment("x", 10)
        self.simple_assignment("y", 20)
        
        # Object operations
        self.object_operations("my_obj")
        
        # Function call
        self.function_call("add", [10, 20], 30)
        
        # Control flow
        self.if_statement("x > 5", True, [("result", "positive")])
        
        # Loop
        self.for_loop("i", [1, 2, 3], [("sum", "accumulating")])
        
        # Complex assignments
        self.complex_assignment_pattern("counter")
        
        # Function chain
        self.function_call_chain([
            ("process", [30], "processed"),
            ("validate", ["processed"], True),
            ("finalize", [True], "complete")
        ])
        
        return self
    
    def build(self) -> List[TraceEvent]:
        """Build and return the events"""
        return self.builder.build()


def sequence(name: str = "") -> TraceSequence:
    """Create a new trace sequence builder"""
    return TraceSequence()


# Convenience functions for quick event creation
def trace() -> TraceEventBuilder:
    """Create a new trace event builder"""
    return TraceEventBuilder()