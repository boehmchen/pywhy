"""
Question and answer system for Python Whyline.
Allows users to ask "why" and "why not" questions about program execution.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from .tracer import TraceEvent, WhylineTracer


class QuestionType(Enum):
    WHY_DID = "why_did"
    WHY_DIDNT = "why_didnt"


@dataclass
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
    source_events: List[TraceEvent] = None
    
    def __post_init__(self):
        if self.source_events is None:
            self.source_events = []
    
    def __str__(self) -> str:
        if not self.source_events:
            return "No source found for this value"
        
        event = self.source_events[0]
        return f"Value came from line {event.lineno} in {event.filename}"


@dataclass
class ExecutionAnswer(Answer):
    """Answer explaining why code executed or didn't execute"""
    execution_events: List[TraceEvent] = None
    dependencies: List[TraceEvent] = None
    
    def __post_init__(self):
        if self.execution_events is None:
            self.execution_events = []
        if self.dependencies is None:
            self.dependencies = []
    
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


class WhyDidLineExecute(Question):
    """Question about why a specific line executed"""
    
    def __init__(self, tracer: WhylineTracer, filename: str, line_no: int):
        super().__init__(tracer, f"line {line_no}", f"Why did line {line_no} execute")
        self.filename = filename
        self.line_no = line_no
        
    def analyze(self) -> ExecutionAnswer:
        """Find why the line executed"""
        # Find all events on this line
        # Handle filename mismatch between CLI (example.py) and tracer (<string>)
        line_events = [event for event in self.tracer.events
                      if event.lineno == self.line_no and 
                      (event.filename == self.filename or 
                       event.filename == "<string>" or
                       self.filename == "<string>")]
        
        if not line_events:
            explanation = f"Line {self.line_no} never executed"
            return ExecutionAnswer(
                question=self,
                explanation=explanation,
                evidence=[],
                execution_events=[],
                dependencies=[]
            )
        
        # Find control flow dependencies
        dependencies = self._find_control_dependencies(line_events[0])
        
        explanation = f"Line {self.line_no} executed {len(line_events)} times"
        if dependencies:
            explanation += f" due to {len(dependencies)} control flow decisions"
        
        return ExecutionAnswer(
            question=self,
            explanation=explanation,
            evidence=line_events + dependencies,
            execution_events=line_events,
            dependencies=dependencies
        )
    
    def _find_control_dependencies(self, target_event: TraceEvent) -> List[TraceEvent]:
        """Find control flow events that led to this execution"""
        dependencies = []
        
        # Look for branch events that occurred before this event
        for event in self.tracer.events:
            if (event.event_id < target_event.event_id and
                event.event_type in ['branch', 'condition'] and
                (event.filename == self.filename or 
                 event.filename == "<string>" or
                 self.filename == "<string>")):
                dependencies.append(event)
        
        return dependencies


class WhyDidntLineExecute(Question):
    """Question about why a specific line didn't execute"""
    
    def __init__(self, tracer: WhylineTracer, filename: str, line_no: int):
        super().__init__(tracer, f"line {line_no}", f"Why didn't line {line_no} execute")
        self.filename = filename
        self.line_no = line_no
        
    def analyze(self) -> ExecutionAnswer:
        """Find why the line didn't execute"""
        # Check if the line actually did execute
        # Handle filename mismatch between CLI (example.py) and tracer (<string>)
        line_events = [event for event in self.tracer.events
                      if event.lineno == self.line_no and 
                      (event.filename == self.filename or 
                       event.filename == "<string>" or
                       self.filename == "<string>")]
        
        if line_events:
            explanation = f"Line {self.line_no} actually did execute {len(line_events)} times"
            return ExecutionAnswer(
                question=self,
                explanation=explanation,
                evidence=line_events,
                execution_events=line_events,
                dependencies=[]
            )
        
        # Find nearby control flow to understand why it didn't execute
        control_flow = self._find_blocking_control_flow()
        
        explanation = f"Line {self.line_no} didn't execute"
        if control_flow:
            explanation += f" due to control flow decisions on lines {[e.lineno for e in control_flow]}"
        
        return ExecutionAnswer(
            question=self,
            explanation=explanation,
            evidence=control_flow,
            execution_events=[],
            dependencies=control_flow
        )
    
    def _find_blocking_control_flow(self) -> List[TraceEvent]:
        """Find control flow events that prevented execution"""
        blocking_events = []
        
        # Look for branch events in the same file
        for event in self.tracer.events:
            if (event.event_type in ['branch', 'condition'] and
                (event.filename == self.filename or 
                 event.filename == "<string>" or
                 self.filename == "<string>") and
                event.lineno < self.line_no):
                blocking_events.append(event)
        
        return blocking_events


class WhyDidFunctionReturn(Question):
    """Question about why a function returned a specific value"""
    
    def __init__(self, tracer: WhylineTracer, func_name: str, return_value: Any):
        super().__init__(tracer, func_name, f"Why did function '{func_name}' return '{return_value}'")
        self.func_name = func_name
        self.return_value = return_value
        
    def analyze(self) -> ValueSourceAnswer:
        """Find why the function returned this value"""
        # Find return events for this function
        return_events = []
        
        for event in self.tracer.events:
            if (event.event_type == 'return' and 
                event.args and len(event.args) >= 2 and
                event.args[0] == 'value'):
                
                # For now, include all return events since function context is complex
                # In a more sophisticated implementation, we'd track function call stack
                return_events.append(event)
        
        matching_returns = [e for e in return_events 
                           if e.args[1] == self.return_value]
        
        if not matching_returns:
            explanation = f"No return found for function '{self.func_name}' with value '{self.return_value}'"
        else:
            last_return = matching_returns[-1]
            explanation = f"Function '{self.func_name}' returned '{self.return_value}' at line {last_return.lineno}"
        
        return ValueSourceAnswer(
            question=self,
            explanation=explanation,
            evidence=matching_returns,
            source_events=matching_returns
        )


class QuestionAsker:
    """Factory class for creating questions"""
    
    def __init__(self, tracer: WhylineTracer):
        self.tracer = tracer
        
    def why_did_variable_have_value(self, var_name: str, value: Any, 
                                   filename: str = None, line_no: int = None) -> WhyDidVariableHaveValue:
        """Create a question about why a variable had a specific value"""
        return WhyDidVariableHaveValue(self.tracer, var_name, value, filename, line_no)
    
    def why_did_line_execute(self, filename: str, line_no: int) -> WhyDidLineExecute:
        """Create a question about why a line executed"""
        return WhyDidLineExecute(self.tracer, filename, line_no)
    
    def why_didnt_line_execute(self, filename: str, line_no: int) -> WhyDidntLineExecute:
        """Create a question about why a line didn't execute"""
        return WhyDidntLineExecute(self.tracer, filename, line_no)
    
    def why_did_function_return(self, func_name: str, return_value: Any) -> WhyDidFunctionReturn:
        """Create a question about why a function returned a specific value"""
        return WhyDidFunctionReturn(self.tracer, func_name, return_value)