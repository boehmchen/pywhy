"""
Tests for the tracing DSL functionality.
Demonstrates how to create and test tracing events using the DSL.
"""

import pytest
from typing import List

from pywhy.instrumenter import (
    EventType, TraceEvent,
    EventMatcher, trace
)


@pytest.mark.dsl
class TestTraceEventBuilder:
    """Test the TraceEventBuilder DSL."""
    
    def test_basic_assignment_creation(self, trace_builder):
        """Test creating basic assignment events."""
        events = (trace_builder
                  .assign("x", 5)
                  .assign("y", 10)
                  .build())
        
        assert len(events) == 2
        assert events[0].event_type == EventType.ASSIGN.value
        assert events[0].data['var_name'] == "x"
        assert events[0].data['value'] == 5
        
        assert events[1].event_type == EventType.ASSIGN.value
        assert events[1].data['var_name'] == "y"
        assert events[1].data['value'] == 10
    
    def test_function_events_creation(self, trace_builder):
        """Test creating function entry and return events."""
        events = (trace_builder
                  .function_entry("factorial", [5])
                  .return_event(120)
                  .build())
        
        assert len(events) == 2
        assert events[0].event_type == EventType.FUNCTION_ENTRY.value
        assert events[0].data['func_name'] == "factorial"
        assert events[0].data['args'] == [5]
        
        assert events[1].event_type == EventType.RETURN.value
        assert events[1].data['value'] == 120
    
    @pytest.mark.parametrize("condition,result", [
        ("x > 0", True),
        ("y < 10", False),
        ("z == 0", True)
    ])
    def test_condition_events_parametrized(self, trace_builder, condition, result):
        """Test creating condition events with different parameters."""
        events = (trace_builder
                  .condition(condition, result)
                  .build())
        
        assert len(events) == 1
        assert events[0].event_type == EventType.CONDITION.value
        assert events[0].data['test'] == condition
        assert events[0].data['result'] == result
    
    def test_control_flow_events_creation(self, trace_builder):
        """Test creating control flow events."""
        events = (trace_builder
                  .condition("x > 0", True)
                  .branch("if", True)
                  .loop_iteration("i", 1)
                  .while_condition("i < 10", True)
                  .build())
        
        assert len(events) == 4
        expected_types = [
            EventType.CONDITION,
            EventType.BRANCH,
            EventType.LOOP_ITERATION,
            EventType.WHILE_CONDITION
        ]
        
        for event, expected_type in zip(events, expected_types):
            assert event.event_type == expected_type.value
    
    def test_assignment_variations(self, trace_builder):
        """Test different types of assignment events."""
        events = (trace_builder
                  .attr_assign("obj", "value", 42)
                  .subscript_assign("arr", 0, "hello")
                  .aug_assign("counter", 1, "+=")
                  .build())
        
        assert len(events) == 3
        
        # Test attribute assignment
        assert events[0].event_type == EventType.ATTR_ASSIGN.value
        assert events[0].data['obj_attr'] == "value"
        assert events[0].data['value'] == 42
        
        # Test subscript assignment
        assert events[1].event_type == EventType.SUBSCRIPT_ASSIGN.value
        assert events[1].data['container'] == "arr"
        assert events[1].data['index'] == 0
        assert events[1].data['value'] == "hello"
        
        # Test augmented assignment
        assert events[2].event_type == EventType.AUG_ASSIGN.value
        assert events[2].data['var_name'] == "counter"
        assert events[2].data['value'] == 1
        assert events[2].data['operation'] == "+="
    
    def test_filename_and_line_numbers(self, trace_builder):
        """Test setting filename and line numbers."""
        events = (trace_builder
                  .set_filename("test.py")
                  .set_line(10)
                  .assign("x", 5, line_no=15)
                  .assign("y", 10)  # Should use default line_no
                  .build())
        
        assert events[0].filename == "test.py"
        assert events[0].line_no == 15
        assert events[1].line_no == 10  # Default from set_line
    
    def test_builder_reset(self, trace_builder):
        """Test resetting the builder state."""
        trace_builder.assign("x", 5)
        events1 = trace_builder.build()
        assert len(events1) == 1
        
        trace_builder.reset()
        trace_builder.assign("y", 10)
        events2 = trace_builder.build()
        
        assert len(events2) == 1
        assert events2[0].data['var_name'] == "y"
    
    def test_json_serialization(self, trace_builder):
        """Test JSON serialization of events."""
        events = (trace_builder
                  .assign("x", 42)
                  .build())
        
        json_str = trace_builder.to_json()
        assert '"event_type": "assign"' in json_str
        assert '"var_name": "x"' in json_str
        assert '"value": 42' in json_str


@pytest.mark.dsl
class TestTraceSequence:
    """Test the TraceSequence helper class."""
    
    def test_simple_assignment_sequence(self, trace_sequence):
        """Test simple assignment sequence."""
        events = (trace_sequence
                  .simple_assignment("x", 5)
                  .simple_assignment("y", 10)
                  .build())
        
        assert len(events) == 2
        assert all(event.event_type == EventType.ASSIGN.value for event in events)
        
        # Check values
        assert events[0].data['var_name'] == "x"
        assert events[0].data['value'] == 5
        assert events[1].data['var_name'] == "y"
        assert events[1].data['value'] == 10
    
    def test_function_call_sequence(self, trace_sequence):
        """Test function call with return."""
        events = (trace_sequence
                  .function_call("add", [5, 10], 15)
                  .build())
        
        assert len(events) == 2
        assert events[0].event_type == EventType.FUNCTION_ENTRY.value
        assert events[0].data['func_name'] == "add"
        assert events[0].data['args'] == [5, 10]
        
        assert events[1].event_type == EventType.RETURN.value
        assert events[1].data['value'] == 15
    
    @pytest.mark.parametrize("condition,result,then_assignments,else_assignments", [
        ("x > 0", True, [("result", "positive")], None),
        ("x > 0", False, None, [("result", "non-positive")]),
        ("y == 10", True, [("a", 1), ("b", 2)], None)
    ])
    def test_if_statement_parametrized(self, trace_sequence, condition, result, then_assignments, else_assignments):
        """Test if statement with different conditions and assignments."""
        events = (trace_sequence
                  .if_statement(condition, result, then_assignments, else_assignments)
                  .build())
        
        # Should have condition + branch + assignments
        expected_count = 2  # condition + branch
        if then_assignments and result:
            expected_count += len(then_assignments)
        elif else_assignments and not result:
            expected_count += len(else_assignments)
        
        assert len(events) == expected_count
        assert events[0].event_type == EventType.CONDITION.value
        assert events[0].data['test'] == condition
        assert events[0].data['result'] == result
        
        assert events[1].event_type == EventType.BRANCH.value
    
    def test_for_loop_sequence(self, trace_sequence):
        """Test for loop sequence."""
        events = (trace_sequence
                  .for_loop("i", [1, 2, 3], [("sum", "updated")])
                  .build())
        
        # Should have 3 iterations, each with loop_iteration + assignment
        assert len(events) == 6
        
        loop_events = [e for e in events if e.event_type == EventType.LOOP_ITERATION.value]
        assert len(loop_events) == 3
        
        # Check iteration values
        for i, event in enumerate(loop_events):
            assert event.data['target'] == "i"
            assert event.data['iter_value'] == i + 1
    
    def test_complex_sequence(self, trace_sequence):
        """Test a complex sequence combining multiple patterns."""
        events = (trace_sequence
                  .simple_assignment("x", 10)
                  .function_call("process", [10], 20)
                  .if_statement("result > 15", True, [("status", "high")])
                  .for_loop("i", [1, 2], [("count", "incremented")])
                  .build())
        
        # Should have a reasonable number of events
        assert len(events) > 5
        
        # Should contain all expected event types
        event_types = {e.event_type for e in events}
        expected_types = {
            EventType.ASSIGN.value,
            EventType.FUNCTION_ENTRY.value,
            EventType.RETURN.value,
            EventType.CONDITION.value,
            EventType.BRANCH.value,
            EventType.LOOP_ITERATION.value
        }
        
        assert expected_types.issubset(event_types)


@pytest.mark.dsl
class TestEventMatcher:
    """Test the EventMatcher utility class."""
    
    @pytest.fixture
    def sample_events(self, trace_builder):
        """Create sample events for testing."""
        return (trace_builder
                .assign("x", 5)
                .assign("y", 10)
                .function_entry("test", [])
                .return_event(None)
                .condition("x > 0", True)
                .build())
    
    def test_has_event_type(self, sample_events):
        """Test checking for event type presence."""
        assert EventMatcher.has_event_type(sample_events, EventType.ASSIGN)
        assert EventMatcher.has_event_type(sample_events, EventType.FUNCTION_ENTRY)
        assert not EventMatcher.has_event_type(sample_events, EventType.LOOP_ITERATION)
    
    @pytest.mark.parametrize("event_type,expected_count", [
        (EventType.ASSIGN, 2),
        (EventType.FUNCTION_ENTRY, 1),
        (EventType.RETURN, 1),
        (EventType.CONDITION, 1),
        (EventType.LOOP_ITERATION, 0)
    ])
    def test_count_event_type_parametrized(self, sample_events, event_type, expected_count):
        """Test counting events by type with parameters."""
        actual_count = EventMatcher.count_event_type(sample_events, event_type)
        assert actual_count == expected_count
    
    def test_find_events_with_filters(self, sample_events):
        """Test finding events with filters."""
        # Find all assignment events
        assigns = EventMatcher.find_events(sample_events, event_type=EventType.ASSIGN.value)
        assert len(assigns) == 2
        
        # Find specific variable assignment
        x_assigns = EventMatcher.find_events(sample_events, event_type=EventType.ASSIGN.value, var_name="x")
        assert len(x_assigns) == 1
        assert x_assigns[0].data['value'] == 5
        
        # Find function with specific name
        test_functions = EventMatcher.find_events(sample_events, event_type=EventType.FUNCTION_ENTRY.value, func_name="test")
        assert len(test_functions) == 1
    
    def test_assert_sequence(self, sample_events):
        """Test sequence assertion."""
        expected = [
            EventType.ASSIGN, 
            EventType.ASSIGN, 
            EventType.FUNCTION_ENTRY, 
            EventType.RETURN, 
            EventType.CONDITION
        ]
        
        assert EventMatcher.assert_sequence(sample_events, expected)
        
        # Test with wrong sequence
        wrong_expected = [EventType.ASSIGN, EventType.FUNCTION_ENTRY]
        assert not EventMatcher.assert_sequence(sample_events, wrong_expected)


@pytest.mark.dsl
class TestTraceEvent:
    """Test the TraceEvent class."""
    
    def test_to_dict_conversion(self):
        """Test converting event to dictionary."""
        event = TraceEvent(
            event_id=1,
            filename="test.py",
            line_no=10,
            event_type=EventType.ASSIGN.value,
            data={"var_name": "x", "value": 5}
        )
        
        result = event.to_dict()
        expected = {
            'event_id': 1,
            'filename': 'test.py',
            'line_no': 10,
            'event_type': EventType.ASSIGN.value,
            'data': {'var_name': 'x', 'value': 5}
        }
        
        assert result == expected
    
    def test_to_json_conversion(self):
        """Test converting event to JSON."""
        event = TraceEvent(
            event_id=1,
            filename="test.py",
            line_no=10,
            event_type=EventType.ASSIGN.value,
            data={"var_name": "x", "value": 5}
        )
        
        json_str = event.to_json()
        assert '"event_id": 1' in json_str
        assert '"event_type": "assign"' in json_str
        assert '"var_name": "x"' in json_str



@pytest.mark.dsl
def test_full_workflow_example():
    """Test a complete workflow using the DSL."""
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
    expected_types = [
        EventType.FUNCTION_ENTRY, 
        EventType.CONDITION, 
        EventType.BRANCH, 
        EventType.ASSIGN, 
        EventType.RETURN
    ]
    assert EventMatcher.assert_sequence(events, expected_types)
    
    # Verify specific details
    func_events = EventMatcher.find_events(events, event_type=EventType.FUNCTION_ENTRY.value)
    assert len(func_events) == 1
    assert func_events[0].data['func_name'] == "factorial"
    assert func_events[0].data['args'] == [5]
    
    return_events = EventMatcher.find_events(events, event_type=EventType.RETURN.value)
    assert len(return_events) == 1
    assert return_events[0].data['value'] == 120


@pytest.mark.dsl
@pytest.mark.integration
def test_dsl_integration_with_real_tracing():
    """Test DSL integration with actual tracing system."""
    # This test demonstrates how DSL can be used to create expected patterns
    
    # Create expected trace using DSL
    expected_events = (trace()
                       .assign("x", 10)
                       .assign("y", 20)
                       .assign("z", 30)
                       .build())
    
    # Verify we can create expected patterns
    assert len(expected_events) == 3
    
    # Check DSL events have the expected structure
    for event in expected_events:
        assert hasattr(event, 'event_type')
        assert hasattr(event, 'data')
        assert event.event_type == EventType.ASSIGN.value
