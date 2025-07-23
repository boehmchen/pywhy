"""
Question and answer system for Python Whyline.
Allows users to ask "why" and "why not" questions about program execution.
"""

from abc import ABC, abstractmethod
from typing import List, Any, Optional
from dataclasses import dataclass, field
from .tracer import TraceEvent, WhylineTracer

class Answer:
    """Base class for answers to questions"""
    question: 'Question'
    explanation: str
    evidence: List[TraceEvent]
    
    def __str__(self) -> str:
        return self.explanation


@dataclass
class ValueSourceAnswer(Answer):
    """Answer explaining where a value came from"""
    source_events: List[TraceEvent] = field(default_factory=list)
    
    def __str__(self) -> str:
        if not self.source_events:
            return "No source found for this value"
        
        event = self.source_events[0]
        return f"Value came from line {event.lineno} in {event.filename}"


@dataclass
class ExecutionAnswer(Answer):
    """Answer explaining why code executed or didn't execute"""
    execution_events: List[TraceEvent] = field(default_factory=list)
    dependencies: List[TraceEvent] = field(default_factory=list)
    
    def __str__(self) -> str:
        if self.execution_events:
            return f"Code executed {len(self.execution_events)} times"
        return "Code never executed"


class Question(ABC):
    """Base class for all questions"""
    
    def __init__(self, tracer: WhylineTracer, subject: str, description: str):
        self.tracer = tracer
        self.subject = subject
        self.description = description
        self.answer: Optional[Answer] = None
        
    @abstractmethod
    def analyze(self) -> Answer:
        """Analyze the trace to answer the question"""
        pass
    
    def get_answer(self) -> Answer:
        """Get the answer, computing it if necessary"""
        if self.answer is None:
            self.answer = self.analyze()
        return self.answer
    
    def __str__(self) -> str:
        # Check if the subject is already in the description to avoid duplication
        if self.subject in self.description:
            return f"{self.description}?"
        else:
            return f"{self.description} {self.subject}?"


class WhyDidVariableHaveValue(Question):
    """Question about why a variable had a specific value"""
    
    def __init__(self, tracer: WhylineTracer, var_name: str, value: Any, 
                 filename: str = None, line_no: int = None):
        super().__init__(tracer, var_name, f"Why did variable '{var_name}' have value '{value}'")
        self.var_name = var_name
        self.value = value
        self.filename = filename
        self.line_no = line_no
        
    def analyze(self) -> ValueSourceAnswer:
        """Find where the variable got its value"""
        # Find assignment events for this variable
        assignments = []
        
        for event in self.tracer.events:
            if (event.event_type in ['assign', 'aug_assign'] and 
                event.args and len(event.args) >= 4 and
                event.args[0] == 'var_name' and event.args[1] == self.var_name):
                
                # Check if this is the right file and line
                # Handle filename mismatch between CLI and tracer
                if self.filename and not (event.filename == self.filename or 
                                        event.filename == "<string>" or
                                        self.filename == "<string>"):
                    continue
                if self.line_no and event.lineno > self.line_no:
                    continue
                    
                # Check if the value matches (check both args and locals)
                value_matches = False
                
                # Check the value from the args (more reliable)
                if len(event.args) >= 4 and event.args[2] == 'value':
                    if event.args[3] == self.value:
                        value_matches = True
                
                # Also check locals as backup
                if not value_matches and self.var_name in event.locals_snapshot:
                    actual_value = event.locals_snapshot[self.var_name]
                    if actual_value == self.value:
                        value_matches = True
                
                if value_matches:
                    assignments.append(event)
        
        if not assignments:
            explanation = f"No assignment found for variable '{self.var_name}' with value '{self.value}'"
        else:
            last_assignment = assignments[-1]
            explanation = f"Variable '{self.var_name}' got value '{self.value}' from assignment at line {last_assignment.lineno}"
        
        return ValueSourceAnswer(
            question=self,
            explanation=explanation,
            evidence=assignments,
            source_events=assignments
        )


class WhyDidFunctionReturn(Question):
    """Question about why a function returned a specific value"""
    
    def __init__(self, tracer: WhylineTracer, func_name: str, return_value: Any):
        super().__init__(tracer, func_name, f"Why did function '{func_name}' return '{return_value}'")
        self.func_name = func_name
        self.return_value = return_value
        
    def analyze(self) -> ValueSourceAnswer:
        """Find why the function returned this value using dynamic slicing"""
        # Find return events for this function
        return_events = []
        
        for event in self.tracer.events:
            if (event.event_type == 'return' and 
                event.args and len(event.args) >= 2 and
                event.args[0] == 'value'):
                
                # Check if this return matches our expected function and value
                if event.args[1] == self.return_value:
                    return_events.append(event)
        
        if not return_events:
            explanation = f"No return found for function '{self.func_name}' with value '{self.return_value}'"
            return ValueSourceAnswer(
                question=self,
                explanation=explanation,
                evidence=[],
                source_events=[]
            )
        
        # Use the most recent matching return event
        target_return = return_events[-1]
        
        # Perform dynamic slicing to find data dependencies leading to this return
        dependencies = self._find_return_dependencies(target_return)
        
        explanation = f"Function '{self.func_name}' returned '{self.return_value}' at line {target_return.lineno}"
        if dependencies:
            explanation += f" due to {len(dependencies)} data dependencies"
        
        return ValueSourceAnswer(
            question=self,
            explanation=explanation,
            evidence=[target_return] + dependencies,
            source_events=[target_return] + dependencies
        )
    
    def _find_return_dependencies(self, return_event: TraceEvent) -> List[TraceEvent]:
        """Find the chain of events that led to this return value"""
        dependencies = []
        
        # Look for assignments and calculations that contributed to the return value
        for event in self.tracer.events:
            if (event.event_id < return_event.event_id and
                event.event_type in ['assign', 'call_post'] and
                event.filename == return_event.filename):
                
                # Check if any variable in this event's locals matches the return value
                for var_name, var_value in event.locals_snapshot.items():
                    if var_value == self.return_value:
                        dependencies.append(event)
                        break
        
        return dependencies


class WhyWasFunctionCalled(Question):
    """Question about why a function was called"""
    
    def __init__(self,
            tracer: WhylineTracer,
            func_name: str, call_context: str = None):
        super().__init__(tracer, func_name, f"Why was function '{func_name}' called")
        self.func_name = func_name
        self.call_context = call_context
        
    def analyze(self) -> ExecutionAnswer:
        """Find why the function was called using control flow analysis"""
        # Find call events for this function
        call_events = []
        
        for event in self.tracer.events:
            if (event.event_type == 'call_pre' and 
                event.args and len(event.args) >= 2 and
                event.args[0] == 'func_name' and 
                event.args[1] == self.func_name):
                call_events.append(event)
        
        if not call_events:
            explanation = f"Function '{self.func_name}' was never called"
            return ExecutionAnswer(
                question=self,
                explanation=explanation,
                evidence=[],
                execution_events=[],
                dependencies=[]
            )
        
        # Analyze the most recent call
        target_call = call_events[-1]
        
        # Find control flow dependencies that led to this call
        dependencies = self._find_call_dependencies(target_call)
        
        explanation = f"Function '{self.func_name}' was called {len(call_events)} times"
        if dependencies:
            explanation += f" due to {len(dependencies)} control flow decisions"
        
        return ExecutionAnswer(
            question=self,
            explanation=explanation,
            evidence=call_events + dependencies,
            execution_events=call_events,
            dependencies=dependencies
        )
    
    def _find_call_dependencies(self, call_event: TraceEvent) -> List[TraceEvent]:
        """Find the control flow events that led to this function call"""
        dependencies = []
        
        # Look for branch and condition events that occurred before the call
        for event in self.tracer.events:
            if (event.event_id < call_event.event_id and
                event.event_type in ['branch', 'condition'] and
                event.filename == call_event.filename):
                dependencies.append(event)
        
        return dependencies


class WhyDidntFieldChange(Question):
    """Question about why a field's value didn't change after a certain time"""
    
    def __init__(self, tracer: WhylineTracer, field_name: str, after_time: float, 
                 object_id: int = None):
        super().__init__(tracer, field_name, f"Why didn't field '{field_name}' change after time {after_time}")
        self.field_name = field_name
        self.after_time = after_time
        self.object_id = object_id
        
    def analyze(self) -> ExecutionAnswer:
        """Find why the field wasn't assigned after the given time"""
        # Find all assignment events to this field after the specified time
        field_assignments = []
        potential_assignments = []
        
        for event in self.tracer.events:
            if event.timestamp > self.after_time:
                # Check for actual assignments
                if (event.event_type == 'assign' and 
                    event.args and len(event.args) >= 2 and
                    event.args[0] == 'var_name' and 
                    event.args[1] == self.field_name):
                    field_assignments.append(event)
                
                # Check for potential assignment sites (lines that could assign to this field)
                elif self.field_name in event.locals_snapshot:
                    potential_assignments.append(event)
        
        if field_assignments:
            explanation = f"Field '{self.field_name}' actually did change {len(field_assignments)} times after the specified time"
            return ExecutionAnswer(
                question=self,
                explanation=explanation,
                evidence=field_assignments,
                execution_events=field_assignments,
                dependencies=[]
            )
        
        # Analyze why potential assignment sites didn't execute or assign
        blocking_control_flow = self._find_blocking_control_flow_for_field()
        
        explanation = f"Field '{self.field_name}' didn't change after the specified time"
        if blocking_control_flow:
            explanation += f" due to {len(blocking_control_flow)} control flow decisions"
        elif potential_assignments:
            explanation += f", though {len(potential_assignments)} potential assignment sites were reached"
        
        return ExecutionAnswer(
            question=self,
            explanation=explanation,
            evidence=blocking_control_flow + potential_assignments,
            execution_events=[],
            dependencies=blocking_control_flow
        )
    
    def _find_blocking_control_flow_for_field(self) -> List[TraceEvent]:
        """Find control flow events that prevented field assignment"""
        blocking_events = []
        
        # Look for branch events after the specified time that might have blocked assignment
        for event in self.tracer.events:
            if (event.timestamp > self.after_time and
                event.event_type in ['branch', 'condition']):
                blocking_events.append(event)
        
        return blocking_events


class WhyDidObjectGetCreated(Question):
    """Question about why an object was created"""
    
    def __init__(self, tracer: WhylineTracer, object_type: str, object_id: int = None):
        super().__init__(tracer, object_type, f"Why did object of type '{object_type}' get created")
        self.object_type = object_type
        self.object_id = object_id
        
    def analyze(self) -> ExecutionAnswer:
        """Find why the object was instantiated"""
        # Find instantiation events (assignments that create new objects)
        creation_events = []
        
        for event in self.tracer.events:
            if event.event_type == 'assign':
                # Check if any value in locals looks like an object creation
                for var_name, var_value in event.locals_snapshot.items():
                    if (hasattr(var_value, '__class__') and 
                        var_value.__class__.__name__ == self.object_type):
                        creation_events.append(event)
                        break
        
        if not creation_events:
            explanation = f"No creation found for objects of type '{self.object_type}'"
            return ExecutionAnswer(
                question=self,
                explanation=explanation,
                evidence=[],
                execution_events=[],
                dependencies=[]
            )
        
        # Analyze the most recent creation
        target_creation = creation_events[-1]
        
        # Find control flow dependencies that led to this creation
        dependencies = self._find_creation_dependencies(target_creation)
        
        explanation = f"Object of type '{self.object_type}' was created {len(creation_events)} times"
        if dependencies:
            explanation += f" due to {len(dependencies)} control flow decisions"
        
        return ExecutionAnswer(
            question=self,
            explanation=explanation,
            evidence=creation_events + dependencies,
            execution_events=creation_events,
            dependencies=dependencies
        )
    
    def _find_creation_dependencies(self, creation_event: TraceEvent) -> List[TraceEvent]:
        """Find the control flow events that led to object creation"""
        dependencies = []
        
        # Look for branch and condition events that occurred before the creation
        for event in self.tracer.events:
            if (event.event_id < creation_event.event_id and
                event.event_type in ['branch', 'condition'] and
                event.filename == creation_event.filename):
                dependencies.append(event)
        
        return dependencies


class WhyDidPropertyGetAssigned(Question):
    """Question about why a property got assigned a specific value"""
    
    def __init__(self, tracer: WhylineTracer, property_name: str, value: Any, 
                 object_id: int = None):
        super().__init__(tracer, property_name, f"Why did property '{property_name}' get assigned '{value}'")
        self.property_name = property_name
        self.value = value
        self.object_id = object_id
        
    def analyze(self) -> ValueSourceAnswer:
        """Find why the property was assigned this value using data flow analysis"""
        # Find assignment events for this property
        assignments = []
        
        for event in self.tracer.events:
            if event.event_type == 'assign':
                # Check if this looks like a property assignment
                if (event.args and len(event.args) >= 4 and
                    event.args[0] == 'var_name' and 
                    event.args[1] == self.property_name and
                    event.args[2] == 'value' and
                    event.args[3] == self.value):
                    assignments.append(event)
                
                # Also check locals for the property
                elif self.property_name in event.locals_snapshot:
                    if event.locals_snapshot[self.property_name] == self.value:
                        assignments.append(event)
        
        if not assignments:
            explanation = f"No assignment found for property '{self.property_name}' with value '{self.value}'"
            return ValueSourceAnswer(
                question=self,
                explanation=explanation,
                evidence=[],
                source_events=[]
            )
        
        # Use the most recent assignment
        target_assignment = assignments[-1]
        
        # Find the source of this value through data dependencies
        dependencies = self._find_value_source_dependencies(target_assignment)
        
        explanation = f"Property '{self.property_name}' got value '{self.value}' from assignment at line {target_assignment.lineno}"
        if dependencies:
            explanation += f" via {len(dependencies)} data dependencies"
        
        return ValueSourceAnswer(
            question=self,
            explanation=explanation,
            evidence=assignments + dependencies,
            source_events=assignments + dependencies
        )
    
    def _find_value_source_dependencies(self, assignment_event: TraceEvent) -> List[TraceEvent]:
        """Find where the assigned value originally came from"""
        dependencies = []
        
        # Look for earlier events that produced this value
        for event in self.tracer.events:
            if (event.event_id < assignment_event.event_id and
                event.event_type in ['assign', 'call_post', 'return']):
                
                # Check if any value in this event matches our target value
                if event.args and self.value in event.args:
                    dependencies.append(event)
                elif self.value in event.locals_snapshot.values():
                    dependencies.append(event)
        
        return dependencies


class QuestionAsker:
    """Factory class for creating questions"""
    
    def __init__(self, tracer: WhylineTracer):
        self.tracer = tracer
        
    def why_did_variable_have_value(self, var_name: str, value: Any, 
                                   filename: str = None, line_no: int = None) -> WhyDidVariableHaveValue:
        """Create a question about why a variable had a specific value"""
        return WhyDidVariableHaveValue(self.tracer, var_name, value, filename, line_no)
    
    def why_did_function_return(self, func_name: str, return_value: Any) -> WhyDidFunctionReturn:
        """Create a question about why a function returned a specific value"""
        return WhyDidFunctionReturn(self.tracer, func_name, return_value)
    
    def why_was_function_called(self, func_name: str, call_context: str = None) -> WhyWasFunctionCalled:
        """Create a question about why a function was called"""
        return WhyWasFunctionCalled(self.tracer, func_name, call_context)
    
    def why_didnt_field_change(self, field_name: str, after_time: float, 
                              object_id: int = None) -> WhyDidntFieldChange:
        """Create a question about why a field didn't change after a certain time"""
        return WhyDidntFieldChange(self.tracer, field_name, after_time, object_id)
    
    def why_did_object_get_created(self, object_type: str, object_id: int = None) -> WhyDidObjectGetCreated:
        """Create a question about why an object was created"""
        return WhyDidObjectGetCreated(self.tracer, object_type, object_id)
    
    def why_did_property_get_assigned(self, property_name: str, value: Any, 
                                    object_id: int = None) -> WhyDidPropertyGetAssigned:
        """Create a question about why a property got assigned a specific value"""
        return WhyDidPropertyGetAssigned(self.tracer, property_name, value, object_id)