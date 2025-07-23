"""
Tests for the tracing DSL functionality.
Demonstrates how to create and test tracing events.
"""

import pytest
from pywhy.instrumenter import (
    EventType, TraceEvent, TraceEventBuilder, TraceSequence, 
    EventMatcher, trace, sequence
)


class TestTraceEventBuilder:
    """Test the TraceEventBuilder class"""
    
    def test_basic_assignment(self):
        """Test creating basic assignment events"""
        events = (trace()
                  .assign("x", 5)
                  .assign("y", 10)
                  .build())
        
        assert len(events) == 2
        assert events[0].event_type == "assign"
        assert events[0].data['var_name'] == "x"
        assert events[0].data['value'] == 5
        
        assert events[1].event_type == "assign"
        assert events[1].data['var_name'] == "y"
        assert events[1].data['value'] == 10
    
    def test_function_events(self):
        """Test creating function entry and return events"""
        events = (trace()
                  .function_entry("factorial", [5])
                  .return_event(120)
                  .build())
        
        assert len(events) == 2
        assert events[0].event_type == "function_entry"
        assert events[0].data['func_name'] == "factorial"
        assert events[0].data['args'] == [5]
        
        assert events[1].event_type == "return"
        assert events[1].data['value'] == 120
    
    def test_control_flow_events(self):
        """Test creating control flow events"""
        events = (trace()
                  .condition("x > 0", True)
                  .branch("if", True)
                  .loop_iteration("i", 1)
                  .while_condition("i < 10", True)
                  .build())
        
        assert len(events) == 4
        assert events[0].event_type == "condition"
        assert events[1].event_type == "branch"
        assert events[2].event_type == "loop_iteration"
        assert events[3].event_type == "while_condition"
    
    def test_attribute_and_subscript_assign(self):
        """Test attribute and subscript assignment events"""
        events = (trace()
                  .attr_assign("obj", "value", 42)
                  .subscript_assign("arr", 0, "hello")
                  .aug_assign("counter", 1, "+=")
                  .build())
        
        assert len(events) == 3
        assert events[0].event_type == "attr_assign"
        assert events[1].event_type == "subscript_assign"
        assert events[2].event_type == "aug_assign"
    
    def test_filename_and_line_numbers(self):
        """Test setting filename and line numbers"""
        events = (trace()
                  .set_filename("test.py")
                  .set_line(10)
                  .assign("x", 5, line_no=15)
                  .assign("y", 10)  # Should use default line_no
                  .build())
        
        assert events[0].filename == "test.py"
        assert events[0].line_no == 15
        assert events[1].line_no == 10  # Default from set_line
    
    def test_reset_builder(self):
        """Test resetting the builder state"""
        builder = trace()
        builder.assign("x", 5)
        
        events1 = builder.build()
        assert len(events1) == 1
        
        builder.reset()
        builder.assign("y", 10)
        
        events2 = builder.build()
        assert len(events2) == 1
        assert events2[0].data['var_name'] == "y"


class TestTraceSequence:
    """Test the TraceSequence helper class"""
    
    def test_simple_assignment_sequence(self):
        """Test simple assignment sequence"""
        events = (sequence("test")
                  .simple_assignment("x", 5)
                  .simple_assignment("y", 10)
                  .build())
        
        assert len(events) == 2
        assert all(event.event_type == "assign" for event in events)
    
    def test_function_call_sequence(self):
        """Test function call with return"""
        events = (sequence("func_test")
                  .function_call("add", [5, 10], 15)
                  .build())
        
        assert len(events) == 2
        assert events[0].event_type == "function_entry"
        assert events[1].event_type == "return"
    
    def test_if_statement_sequence(self):
        """Test if statement with branches"""
        # Test if branch taken
        events_if = (sequence("if_test")
                     .if_statement("x > 0", True, [("result", "positive")])
                     .build())
        
        assert len(events_if) == 3  # condition, branch, assign
        assert events_if[0].event_type == "condition"
        assert events_if[1].event_type == "branch"
        assert events_if[2].event_type == "assign"
        
        # Test else branch taken
        events_else = (sequence("else_test")
                       .if_statement("x > 0", False, None, [("result", "non-positive")])
                       .build())
        
        assert len(events_else) == 3  # condition, branch, assign
        assert events_else[1].data['taken'] == "else"
    
    def test_for_loop_sequence(self):
        """Test for loop sequence"""
        events = (sequence("loop_test")
                  .for_loop("i", [1, 2, 3], [("sum", "updated")])
                  .build())
        
        # Should have 3 iterations, each with loop_iteration + assignment
        assert len(events) == 6
        loop_events = [e for e in events if e.event_type == "loop_iteration"]
        assert len(loop_events) == 3


class TestEventMatcher:
    """Test the EventMatcher utility class"""
    
    def setup_method(self):
        """Set up test events"""
        self.events = (trace()
                       .assign("x", 5)
                       .assign("y", 10)
                       .function_entry("test", [])
                       .return_event(None)
                       .condition("x > 0", True)
                       .build())
    
    def test_has_event_type(self):
        """Test checking for event type presence"""
        assert EventMatcher.has_event_type(self.events, EventType.ASSIGN)
        assert EventMatcher.has_event_type(self.events, EventType.FUNCTION_ENTRY)
        assert not EventMatcher.has_event_type(self.events, EventType.LOOP_ITERATION)
    
    def test_count_event_type(self):
        """Test counting events by type"""
        assert EventMatcher.count_event_type(self.events, EventType.ASSIGN) == 2
        assert EventMatcher.count_event_type(self.events, EventType.FUNCTION_ENTRY) == 1
        assert EventMatcher.count_event_type(self.events, EventType.LOOP_ITERATION) == 0
    
    def test_find_events(self):
        """Test finding events with filters"""
        # Find all assignment events
        assigns = EventMatcher.find_events(self.events, event_type="assign")
        assert len(assigns) == 2
        
        # Find specific variable assignment
        x_assigns = EventMatcher.find_events(self.events, event_type="assign", var_name="x")
        assert len(x_assigns) == 1
        assert x_assigns[0].data['value'] == 5
    
    def test_assert_sequence(self):
        """Test sequence assertion"""
        expected = [EventType.ASSIGN, EventType.ASSIGN, EventType.FUNCTION_ENTRY, 
                   EventType.RETURN, EventType.CONDITION]
        
        assert EventMatcher.assert_sequence(self.events, expected)
        
        # Test with wrong sequence
        wrong_expected = [EventType.ASSIGN, EventType.FUNCTION_ENTRY]
        assert not EventMatcher.assert_sequence(self.events, wrong_expected)


class TestTraceEvent:
    """Test the TraceEvent class"""
    
    def test_to_dict(self):
        """Test converting event to dictionary"""
        event = TraceEvent(
            event_id=1,
            filename="test.py",
            line_no=10,
            event_type="assign",
            data={"var_name": "x", "value": 5}
        )
        
        result = event.to_dict()
        expected = {
            'event_id': 1,
            'filename': 'test.py',
            'line_no': 10,
            'event_type': 'assign',
            'data': {'var_name': 'x', 'value': 5}
        }
        
        assert result == expected
    
    def test_to_json(self):
        """Test converting event to JSON"""
        event = TraceEvent(
            event_id=1,
            filename="test.py",
            line_no=10,
            event_type="assign",
            data={"var_name": "x", "value": 5}
        )
        
        json_str = event.to_json()
        assert '"event_id": 1' in json_str
        assert '"event_type": "assign"' in json_str


def test_convenience_functions():
    """Test convenience functions"""
    # Test trace() function
    builder = trace()
    assert isinstance(builder, TraceEventBuilder)
    
    # Test sequence() function
    seq = sequence("test")
    assert isinstance(seq, TraceSequence)
    assert seq.name == "test"


def test_full_workflow_example():
    """Test a complete workflow using the DSL"""
    # Simulate a factorial function execution
    events = (trace()
              .set_filename("factorial.py")
              .function_entry("factorial", [5], line_no=1)
              .condition("n <= 1", False, line_no=2)
              .branch("else", False, line_no=4)
              .assign("result", 120, line_no=5)
              .return_event(120, line_no=6)
              .build())
    
    # Verify the sequence
    expected_types = [EventType.FUNCTION_ENTRY, EventType.CONDITION, 
                     EventType.BRANCH, EventType.ASSIGN, EventType.RETURN]
    assert EventMatcher.assert_sequence(events, expected_types)
    
    # Verify specific details
    func_events = EventMatcher.find_events(events, event_type="function_entry")
    assert len(func_events) == 1
    assert func_events[0].data['func_name'] == "factorial"
    assert func_events[0].data['args'] == [5]
    
    return_events = EventMatcher.find_events(events, event_type="return")
    assert len(return_events) == 1
    assert return_events[0].data['value'] == 120


if __name__ == "__main__":
    print("Running DSL tests...")
    
    # Run a simple test manually
    test_full_workflow_example()
    print("✅ Full workflow test passed!")
    
    # Test the convenience functions
    test_convenience_functions()
    print("✅ Convenience functions test passed!")
    
    print("\nRun 'pytest tests/test_trace_dsl.py' for complete test suite.")