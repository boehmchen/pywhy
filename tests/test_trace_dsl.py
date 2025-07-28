"""
# Tests for the tracing DSL functionality.
Demonstrates how to create and test tracing events using the DSL.
"""

import pytest
from pywhy.events import TraceEvent
from pywhy.events import EventType
from pywhy.trace_dsl import trace
from pywhy.trace_analysis import EventMatcher


@pytest.mark.dsl
class TestTraceEventBuilder:
    """Test the TraceEventBuilder DSL."""

    def test_basic_assignment_creation(self, trace_builder):
        """Test creating basic assignment events."""
        events = trace_builder.assign("x", 5).assign("y", 10).build()

        assert len(events) == 2
        assert events[0].event_type == EventType.ASSIGN.value
        assert events[0].data["var_name"] == "x"
        assert events[0].data["value"] == 5

        assert events[1].event_type == EventType.ASSIGN.value
        assert events[1].data["var_name"] == "y"
        assert events[1].data["value"] == 10

    def test_function_events_creation(self, trace_builder):
        """Test creating function entry and return events."""
        events = (
            trace_builder.function_entry("factorial", [5]).return_event(120).build()
        )

        assert len(events) == 2
        assert events[0].event_type == EventType.FUNCTION_ENTRY.value
        assert events[0].data["func_name"] == "factorial"
        assert events[0].data["args"] == [5]

        assert events[1].event_type == EventType.RETURN.value
        assert events[1].data["value"] == 120

    @pytest.mark.parametrize(
        "condition,result,decision", [("x > 0", True, "if_block"), ("y < 10", False, "skip_block"), ("z == 0", True, "else_block")]
    )
    def test_branch_events_parametrized(self, trace_builder, condition, result, decision):
        """Test creating branch events with integrated condition."""
        events = trace_builder.branch(condition, result, decision).build()

        assert len(events) == 1
        assert events[0].event_type == EventType.BRANCH.value
        assert events[0].data["condition"] == condition
        assert events[0].data["result"] == result
        assert events[0].data["decision"] == decision

    def test_control_flow_events_creation(self, trace_builder):
        """Test creating control flow events."""
        events = (
            trace_builder.branch("x > 0", True, "if_block")
            .loop_iteration("i", 1)
            .while_condition("i < 10", True)
            .build()
        )

        assert len(events) == 3
        expected_types = [
            EventType.BRANCH,
            EventType.LOOP_ITERATION,
            EventType.WHILE_CONDITION,
        ]

        for event, expected_type in zip(events, expected_types):
            assert event.event_type == expected_type.value

    def test_assignment_variations(self, trace_builder):
        """Test different types of assignment events."""
        events = (
            trace_builder.assign("obj.value", 42, "attr", obj_name="obj", attr_name="value")
            .assign("arr[0]", "hello", "index", container_name="arr", index=0)
            .assign("counter", 1, "aug")
            .build()
        )

        assert len(events) == 3

        # Test attribute assignment
        assert events[0].event_type == EventType.ASSIGN.value
        assert events[0].data["obj_attr"] == "value"
        assert events[0].data["obj"] == "obj"
        assert events[0].data["value"] == 42
        assert events[0].data["target_type"] == "attribute"

        # Test index assignment
        assert events[1].event_type == EventType.ASSIGN.value
        assert events[1].data["container"] == "arr"
        assert events[1].data["index"] == 0
        assert events[1].data["value"] == "hello"
        assert events[1].data["target_type"] == "index"

        # Test augmented assignment
        assert events[2].event_type == EventType.ASSIGN.value
        assert events[2].data["var_name"] == "counter"
        assert events[2].data["value"] == 1
        assert events[2].data["assign_type"] == "aug"
        assert events[2].data["target_type"] == "variable"

    def test_filename_and_line_numbers(self, trace_builder):
        """Test setting filename and line numbers."""
        events = (
            trace_builder.set_filename("test.py")
            .set_line(10)
            .assign("x", 5, line_no=15)
            .assign("y", 10)  # Should use default line_no
            .build()
        )

        assert events[0].filename == "test.py"
        assert events[0].lineno == 15
        assert events[1].lineno == 10  # Default from set_line

    def test_builder_reset(self, trace_builder):
        """Test resetting the builder state."""
        trace_builder.assign("x", 5)
        events1 = trace_builder.build()
        assert len(events1) == 1

        trace_builder.reset()
        trace_builder.assign("y", 10)
        events2 = trace_builder.build()

        assert len(events2) == 1
        assert events2[0].data["var_name"] == "y"

    def test_json_serialization(self, trace_builder):
        """Test JSON serialization of events."""
        events = trace_builder.assign("x", 42).build()

        json_str = trace_builder.to_json()
        assert '"event_type": "assign"' in json_str
        assert '"var_name": "x"' in json_str
        assert '"value": 42' in json_str


pytest.mark.dsl
class TestEventMatcher:
    """Test the EventMatcher utility class."""

    @pytest.fixture
    def sample_events(self, trace_builder):
        """Create sample events for testing."""
        return (
            trace_builder.assign("x", 5)
            .assign("y", 10)
            .function_entry("test", [])
            .return_event(None)
            .branch("x > 0", True, "if_block")
            .build()
        )

    def test_has_event_type(self, sample_events):
        """Test checking for event type presence."""
        assert EventMatcher.has_event_type(sample_events, EventType.ASSIGN)
        assert EventMatcher.has_event_type(sample_events, EventType.FUNCTION_ENTRY)
        assert not EventMatcher.has_event_type(sample_events, EventType.LOOP_ITERATION)

    @pytest.mark.parametrize(
        "event_type,expected_count",
        [
            (EventType.ASSIGN, 2),
            (EventType.FUNCTION_ENTRY, 1),
            (EventType.RETURN, 1),
            (EventType.BRANCH, 1),
            (EventType.LOOP_ITERATION, 0),
        ],
    )
    def test_count_event_type_parametrized(
        self, sample_events, event_type, expected_count
    ):
        """Test counting events by type with parameters."""
        actual_count = EventMatcher.count_event_type(sample_events, event_type)
        assert actual_count == expected_count

    def test_find_events_with_filters(self, sample_events):
        """Test finding events with filters."""
        # Find all assignment events
        assigns = EventMatcher.find_events(
            sample_events, event_type=EventType.ASSIGN.value
        )
        assert len(assigns) == 2

        # Find specific variable assignment
        x_assigns = EventMatcher.find_events(
            sample_events, event_type=EventType.ASSIGN.value, var_name="x"
        )
        assert len(x_assigns) == 1
        assert x_assigns[0].data["value"] == 5

        # Find function with specific name
        test_functions = EventMatcher.find_events(
            sample_events, event_type=EventType.FUNCTION_ENTRY.value, func_name="test"
        )
        assert len(test_functions) == 1

    def test_assert_sequence(self, sample_events):
        """Test sequence assertion."""
        expected = [
            EventType.ASSIGN,
            EventType.ASSIGN,
            EventType.FUNCTION_ENTRY,
            EventType.RETURN,
            EventType.BRANCH,
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
            lineno=10,
            event_type=EventType.ASSIGN,
            data={"var_name": "x", "value": 5},
        )

        result = event.to_dict()
        expected = {
            "event_id": 1,
            "filename": "test.py",
            "lineno": 10,
            "event_type": EventType.ASSIGN.value,
            "data": {"var_name": "x", "value": 5},
            "timestamp": result["timestamp"],  # Dynamic value
            "thread_id": result["thread_id"],  # Dynamic value
            "locals_snapshot": {},
            "globals_snapshot": {}
        }

        assert result == expected

    def test_to_json_conversion(self):
        """Test converting event to JSON."""
        event = TraceEvent(
            event_id=1,
            filename="test.py",
            lineno=10,
            event_type=EventType.ASSIGN,
            data={"var_name": "x", "value": 5},
        )

        json_str = event.to_json()
        assert '"event_id": 1' in json_str
        assert '"event_type": "assign"' in json_str
        assert '"var_name": "x"' in json_str


@pytest.mark.dsl
def test_full_workflow_example():
    """Test a complete workflow using the DSL."""
    # Simulate a factorial function execution
    events = (
        trace()
        .set_filename("factorial.py")
        .function_entry("factorial", [5], line_no=1)
        .branch("n <= 1", False, "else_block", line_no=2)
        .assign("result", 120, line_no=5)
        .return_event(120, line_no=6)
        .build()
    )

    # Verify the sequence
    expected_types = [
        EventType.FUNCTION_ENTRY,
        EventType.BRANCH,
        EventType.ASSIGN,
        EventType.RETURN,
    ]
    assert EventMatcher.assert_sequence(events, expected_types)

    # Verify specific details
    func_events = EventMatcher.find_events(
        events, event_type=EventType.FUNCTION_ENTRY.value
    )
    assert len(func_events) == 1
    assert func_events[0].data["func_name"] == "factorial"
    assert func_events[0].data["args"] == [5]

    return_events = EventMatcher.find_events(events, event_type=EventType.RETURN.value)
    assert len(return_events) == 1
    assert return_events[0].data["value"] == 120


@pytest.mark.dsl
@pytest.mark.integration
def test_dsl_integration_with_real_tracing():
    """Test DSL integration with actual tracing system."""
    # This test demonstrates how DSL can be used to create expected patterns

    # Create expected trace using DSL
    expected_events = trace().assign("x", 10).assign("y", 20).assign("z", 30).build()

    # Verify we can create expected patterns
    assert len(expected_events) == 3

    # Check DSL events have the expected structure
    for event in expected_events:
        assert hasattr(event, "event_type")
        assert hasattr(event, "data")
        assert event.event_type == EventType.ASSIGN.value


@pytest.mark.dsl
class TestTraceEventBuilderExamples:
    """Test that the documentation examples in TraceEventBuilder work correctly."""
    
    def test_assign_example(self):
        """Test assign example from docstring: x = 10 + y"""
        events = trace().assign("x", 10, deps=['y']).build()
        assert len(events) == 1
        assert events[0].event_type == EventType.ASSIGN
        assert events[0].data == {'var_name': 'x', 'value': 10, 'target_type': 'variable', 'assign_type': 'simple', 'deps': ['y']}
    
    def test_attr_assign_example(self):
        """Test attr_assign example from docstring: obj.x = 10"""
        events = trace().assign("obj.x", 10, "attr", obj_name="obj", attr_name="x").build()
        assert len(events) == 1
        assert events[0].event_type == EventType.ASSIGN
        assert events[0].data == {'obj_attr': 'x', 'obj': 'obj', 'value': 10, 'target_type': 'attribute', 'assign_type': 'simple'}
    
    def test_index_assign_example(self):
        """Test index assign example from docstring: arr[i] = 10"""
        events = trace().assign("arr[0]", 10, "index", container_name="arr", index=0, deps=['i']).build()
        assert len(events) == 1
        assert events[0].event_type == EventType.ASSIGN
        assert events[0].data == {'container': 'arr', 'index': 0, 'value': 10, 'target_type': 'index', 'assign_type': 'simple', 'deps': ['i']}
    
    def test_aug_assign_example(self):
        """Test aug_assign example from docstring: x += y (x was 5, y was 3, now x is 8)"""
        events = trace().assign("x", 8, "aug", deps=['x', 'y']).build()
        assert len(events) == 1
        assert events[0].event_type == EventType.ASSIGN
        assert events[0].data == {'var_name': 'x', 'value': 8, 'target_type': 'variable', 'assign_type': 'aug', 'deps': ['x', 'y']}
    
    def test_aug_assign_attr_example(self):
        """Test aug_assign_attr example from docstring: obj.size += 10 (obj.size was 5, now it's 15)"""
        events = trace().assign("obj.size", 15, "aug_attr", obj_name="obj", attr_name="size", deps=['obj']).build()
        assert len(events) == 1
        assert events[0].event_type == EventType.ASSIGN
        assert events[0].data == {'obj_attr': 'size', 'obj': 'obj', 'value': 15, 'target_type': 'attribute', 'assign_type': 'aug', 'deps': ['obj']}
    
    def test_aug_assign_index_example(self):
        """Test aug_assign_index example from docstring: arr[0] += 5 (arr[0] was 10, now it's 15)"""
        events = trace().assign("arr[0]", 15, "aug_index", container_name="arr", index=0, deps=['arr']).build()
        assert len(events) == 1
        assert events[0].event_type == EventType.ASSIGN
        assert events[0].data == {'container': 'arr', 'index': 0, 'value': 15, 'target_type': 'index', 'assign_type': 'aug', 'deps': ['arr']}
    
    def test_slice_assign_example(self):
        """Test slice_assign example from docstring: arr[1:3] = [10, 20]"""
        events = trace().assign("arr[1:3]", [10, 20], "slice", container_name="arr", lower=1, upper=3, step=None).build()
        assert len(events) == 1
        assert events[0].event_type == EventType.ASSIGN
        assert events[0].data == {
            'container': 'arr', 
            'slice_type': 'slice',
            'lower': 1, 
            'upper': 3, 
            'step': None, 
            'value': [10, 20],
            'target_type': 'slice',
            'assign_type': 'simple'
        }
    
    def test_function_entry_example(self):
        """Test function_entry example from docstring: def add(a, b): ... when called with add(3, 4)"""
        events = trace().function_entry("add", [3, 4]).build()
        assert len(events) == 1
        assert events[0].event_type == EventType.FUNCTION_ENTRY
        assert events[0].data == {'func_name': 'add', 'args': [3, 4]}
    
    def test_return_event_example(self):
        """Test return_event example from docstring: return a + b # returns 7"""
        events = trace().return_event(7).build()
        assert len(events) == 1
        assert events[0].event_type == EventType.RETURN
        assert events[0].data == {'value': 7}
    
    def test_call_example(self):
        """Test call example from docstring: result = len([1, 2, 3])"""
        events = trace().call("len", [[1, 2, 3]]).build()
        assert len(events) == 1
        assert events[0].event_type == EventType.CALL
        assert events[0].data == {'func_name': 'len', 'args': [[1, 2, 3]]}
    
    def test_branch_example(self):
        """Test branch example from docstring: if x > 5: ... # x is 10, condition is True, takes if branch"""
        events = trace().branch("x > 5", True, "if_block", deps=['x']).build()
        assert len(events) == 1
        assert events[0].event_type == EventType.BRANCH
        assert events[0].data == {
            'condition': 'x > 5', 
            'result': True, 
            'decision': 'if_block', 
            'deps': ['x']
        }
    
    def test_loop_iteration_example(self):
        """Test loop_iteration example from docstring: for i in [1, 2, 3]: ... # first iteration with i=1"""
        events = trace().loop_iteration("i", 1).build()
        assert len(events) == 1
        assert events[0].event_type == EventType.LOOP_ITERATION
        assert events[0].data == {'target': 'i', 'iter_value': 1}
    
    def test_while_condition_example(self):
        """Test while_condition example from docstring: while x < 10: ... # x is 5, condition is True"""
        events = trace().while_condition("x < 10", True, deps=['x']).build()
        assert len(events) == 1
        assert events[0].event_type == EventType.WHILE_CONDITION
        assert events[0].data == {'condition': 'x < 10', 'result': True, 'deps': ['x']}
    
    def test_utility_methods_examples(self):
        """Test utility method examples from docstrings"""
        # Test build() example
        events = trace().assign("x", 10).build()
        assert len(events) == 1
        assert events[0].data['var_name'] == 'x'
        
        # Test reset() example - builder.assign("x", 10).reset().assign("y", 20)
        builder = trace()
        builder.assign("x", 10)
        assert len(builder.events) == 1
        builder.reset()
        assert len(builder.events) == 0
        builder.assign("y", 20)
        assert len(builder.events) == 1
        assert builder.events[0].data['var_name'] == 'y'
        
        # Test set_filename() example
        events = trace().set_filename("test.py").assign("x", 10).build()
        assert events[0].filename == "test.py"
        
        # Test set_line() example
        events = trace().set_line(5).assign("x", 10).build()
        assert events[0].lineno == 5
