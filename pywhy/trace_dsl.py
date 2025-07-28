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
        """Reset the builder state.
        
        Example usage: builder.assign("x", 10).reset().assign("y", 20)
        """
        self.events = []
        self._current_event_id = 0
        return self
        
    def set_filename(self, filename: str) -> 'TraceEventBuilder':
        """Set the default filename for events.
        
        Example usage: trace().set_filename("test.py").assign("x", 10)
        """
        self._filename = filename
        return self
        
    def set_line(self, line_no: int) -> 'TraceEventBuilder':
        """Set the default line number for events.
        
        Example usage: trace().set_line(5).assign("x", 10)
        """
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
        
    # Unified assignment method
    def assign(self, target: str, value: Any, assign_type: str = "simple", deps: List[str] = None, 
               line_no: Optional[int] = None, **kwargs) -> 'TraceEventBuilder':
        """Unified assignment method for all assignment types.
        
        Args:
            target: Assignment target (var name, obj.attr, container[index], etc.)
            value: Value being assigned
            assign_type: Type of assignment - "simple", "attr", "index", "slice", "aug", "aug_attr", "aug_index"
            deps: List of variable dependencies
            line_no: Optional line number
            **kwargs: Additional parameters for specific assignment types
                - For "attr": obj_name, attr_name
                - For "index": container_name, index
                - For "slice": container_name, lower, upper, step
                - For "aug_attr": obj_name, attr_name
                - For "aug_index": container_name, index
        
        Examples:
            .assign("x", 10)                                    # x = 10
            .assign("obj.attr", 10, "attr", obj_name="obj", attr_name="attr")  # obj.attr = 10
            .assign("arr[0]", 10, "index", container_name="arr", index=0)      # arr[0] = 10
            .assign("x", 15, "aug", deps=['x', 'y'])           # x += y (result 15)
            .assign("obj.size", 15, "aug_attr", obj_name="obj", attr_name="size")  # obj.size += 10
            .assign("arr[0]", 15, "aug_index", container_name="arr", index=0)      # arr[0] += 5
            .assign("arr[1:3]", [10, 20], "slice", container_name="arr", lower=1, upper=3)  # arr[1:3] = [10, 20]
        """
        # All assignments now use ASSIGN EventType with different target_type and assign_type
        event_type = EventType.ASSIGN
        
        if assign_type == "simple":
            data = {'var_name': target, 'value': value, 'target_type': 'variable', 'assign_type': 'simple'}
        
        elif assign_type == "attr":
            obj_name = kwargs.get('obj_name', target.split('.')[0] if '.' in target else 'obj')
            attr_name = kwargs.get('attr_name', target.split('.')[1] if '.' in target else target)
            data = {'obj': obj_name, 'obj_attr': attr_name, 'value': value, 'target_type': 'attribute', 'assign_type': 'simple'}
        
        elif assign_type == "index":
            container_name = kwargs.get('container_name', target.split('[')[0] if '[' in target else target)
            index = kwargs.get('index', 0)
            data = {'container': container_name, 'index': index, 'value': value, 'target_type': 'index', 'assign_type': 'simple'}
        
        elif assign_type == "slice":
            container_name = kwargs.get('container_name', target.split('[')[0] if '[' in target else target)
            data = {
                'container': container_name,
                'slice_type': 'slice',
                'lower': kwargs.get('lower'),
                'upper': kwargs.get('upper'), 
                'step': kwargs.get('step'),
                'value': value,
                'target_type': 'slice',
                'assign_type': 'simple'
            }
        
        elif assign_type == "aug":
            data = {'var_name': target, 'value': value, 'target_type': 'variable', 'assign_type': 'aug'}
        
        elif assign_type == "aug_attr":
            obj_name = kwargs.get('obj_name', target.split('.')[0] if '.' in target else 'obj')
            attr_name = kwargs.get('attr_name', target.split('.')[1] if '.' in target else target)
            data = {'obj': obj_name, 'obj_attr': attr_name, 'value': value, 'target_type': 'attribute', 'assign_type': 'aug'}
        
        elif assign_type == "aug_index":
            container_name = kwargs.get('container_name', target.split('[')[0] if '[' in target else target)
            index = kwargs.get('index', 0)
            data = {'container': container_name, 'index': index, 'value': value, 'target_type': 'index', 'assign_type': 'aug'}
        
        else:
            raise ValueError(f"Unknown assignment type: {assign_type}")
        
        if deps:
            data['deps'] = deps
        
        self._create_event(event_type, data, line_no)
        return self
        
    # Function events
    def function_entry(self, func_name: str, args: List[Any], 
                      line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create a function entry event.
        
        Example Python code: def add(a, b): ...  # when called with add(3, 4)
        DSL usage: .function_entry("add", [3, 4])
        """
        self._create_event(EventType.FUNCTION_ENTRY, {
            'func_name': func_name,
            'args': args
        }, line_no)
        return self
        
    def return_event(self, value: Any, line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create a return event.
        
        Example Python code: return a + b  # returns 7
        DSL usage: .return_event(7)
        """
        self._create_event(EventType.RETURN, {
            'value': value
        }, line_no)
        return self
        
    def call(self, func_name: str, args: List[Any], line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create a general function call event.
        
        Example Python code: result = len([1, 2, 3])
        DSL usage: .call("len", [[1, 2, 3]])
        """
        self._create_event(EventType.CALL, {
            'func_name': func_name,
            'args': args
        }, line_no)
        return self
        
    # Control flow events
        
    def branch(self, condition: str, result: bool, decision: str, deps: List[str] = None, line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create a branch event with integrated condition.
        
        Example Python code: if x > 5: ...  # x is 10, condition is True, takes if branch
        DSL usage: .branch("x > 5", True, "if_block", deps=['x'])
        """
        data = {
            'condition': condition,
            'result': result,
            'decision': decision  # Should be "if_block", "else_block", "elif_block", or "skip_block"
        }
        if deps:
            data['deps'] = deps
        self._create_event(EventType.BRANCH, data, line_no)
        return self
        
    def loop_iteration(self, target: str, iter_value: Any,
                      line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create a loop iteration event.
        
        Example Python code: for i in [1, 2, 3]: ...  # first iteration with i=1
        DSL usage: .loop_iteration("i", 1)
        """
        self._create_event(EventType.LOOP_ITERATION, {
            'target': target,
            'iter_value': iter_value
        }, line_no)
        return self
        
    def while_condition(self, condition: str, result: bool, deps: List[str] = None, line_no: Optional[int] = None) -> 'TraceEventBuilder':
        """Create a while condition event.
        
        Example Python code: while x < 10: ...  # x is 5, condition is True
        DSL usage: .while_condition("x < 10", True, deps=['x'])
        """
        data = {
            'condition': condition,
            'result': result
        }
        if deps:
            data['deps'] = deps
        self._create_event(EventType.WHILE_CONDITION, data, line_no)
        return self
    
        
    # Utility methods
    def build(self) -> List[TraceEvent]:
        """Return the built trace events.
        
        Example usage: events = trace().assign("x", 10).build()
        """
        return self.events.copy()
        
    def print_events(self) -> None:
        """Print all events in a readable format.
        
        Example usage: trace().assign("x", 10).print_events()
        """
        for event in self.events:
            print(f"Event #{event.event_id} ({event.event_type}) at {event.filename}:{event.lineno}")
            for key, value in event.data.items():
                print(f"  {key}: {value}")
            print()
            
    def to_json(self) -> str:
        """Convert all events to JSON.
        
        Example usage: json_str = trace().assign("x", 10).to_json()
        """
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
        self.builder.assign(f"{obj_name}.name", "test_object", "attr", obj_name=obj_name, attr_name="name")
        self.builder.assign(f"{obj_name}.value", 42, "attr", obj_name=obj_name, attr_name="value")
        
        # Index assignment (for dict-like objects)
        self.builder.assign(f"{obj_name}[key1]", "value1", "index", container_name=obj_name, index="key1")
        self.builder.assign(f"{obj_name}[0]", "first_item", "index", container_name=obj_name, index=0)
        
        # Slice assignment
        self.builder.assign(f"{obj_name}[1:3]", ["new", "items"], "slice", container_name=obj_name, lower=1, upper=3, step=None)
        
        return self
    
    def complex_assignment_pattern(self, var_name: str) -> 'TraceSequence':
        """Create a sequence showing all assignment types"""
        # Simple assignment
        self.builder.assign(var_name, 100)
        
        # Augmented assignments
        self.builder.assign(var_name, 110, "aug")  # After += 10
        self.builder.assign(var_name, 220, "aug")  # After *= 2
        self.builder.assign(var_name, 215, "aug")  # After -= 5
        self.builder.assign(var_name, 71, "aug")   # After //= 3
        
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