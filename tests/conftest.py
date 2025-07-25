"""
Test configuration and fixtures for Python Whyline tests
"""

import pytest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pywhy.instrumenter import TraceEvent, exec_instrumented
from pywhy.events import EventType
from pywhy.trace_analysis import EventMatcher
from pywhy.trace_dsl import trace, sequence
from pywhy.tracer import get_tracer
from pywhy.questions import QuestionAsker

# Test configuration constants
TEST_TIMEOUT = 30  # seconds
MAX_EVENTS_FOR_SMALL_TEST = 100
MAX_EVENTS_FOR_LARGE_TEST = 10000
MAX_EXECUTION_TIME = 5.0  # seconds

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / 'data'
TEST_DATA_DIR.mkdir(exist_ok=True)

# Common test code snippets for instrumentation testing
SAMPLE_CODES = {
    'simple_assignment': '''
x = 10
y = 20
z = x + y
''',
    
    'function_call': '''
def add_numbers(a, b):
    return a + b

result = add_numbers(5, 3)
''',
    
    'control_flow': '''
x = 10
if x > 5:
    result = "large"
else:
    result = "small"
''',
    
    'loop': '''
total = 0
for i in range(5):
    total += i
''',
    
    'recursion': '''
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

result = factorial(5)
''',
    
    'class_usage': '''
class Calculator:
    def __init__(self):
        self.value = 0
    
    def add(self, x):
        self.value += x
        return self.value

calc = Calculator()
result = calc.add(10)
''',
    
    'exception_handling': '''
def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return 0

result1 = safe_divide(10, 2)
result2 = safe_divide(10, 0)
''',
    
    'complex_program': '''
def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    
    result.extend(left[i:])
    result.extend(right[j:])
    return result

data = [64, 34, 25, 12, 22, 11, 90]
sorted_data = merge_sort(data)
'''
}


@pytest.fixture
def tracer():
    """Provide a clean tracer instance for each test."""
    tracer = get_tracer()
    tracer.clear()
    yield tracer
    tracer.clear()


@pytest.fixture
def trace_builder():
    """Provide a fresh trace builder instance."""
    return trace()


@pytest.fixture
def trace_sequence():
    """Provide a fresh trace sequence instance."""
    return sequence()


@pytest.fixture
def question_asker(tracer):
    """Provide a QuestionAsker instance with a clean tracer."""
    return QuestionAsker(tracer)


@pytest.fixture
def sample_codes():
    """Provide sample code snippets for testing."""
    return SAMPLE_CODES


@pytest.fixture
def temp_file():
    """Provide a temporary file that is cleaned up after the test."""
    files_created = []
    
    def _create_temp_file(content: str, suffix: str = '.py') -> str:
        fd, path = tempfile.mkstemp(suffix=suffix)
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(content)
            files_created.append(path)
            return path
        except:
            os.close(fd)
            raise
    
    yield _create_temp_file
    
    # Cleanup
    for path in files_created:
        try:
            os.unlink(path)
        except (OSError, FileNotFoundError):
            pass


@pytest.fixture
def temp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    dirs_created = []
    
    def _create_temp_dir() -> str:
        path = tempfile.mkdtemp()
        dirs_created.append(path)
        return path
    
    yield _create_temp_dir
    
    # Cleanup
    for path in dirs_created:
        try:
            shutil.rmtree(path)
        except (OSError, FileNotFoundError):
            pass


@pytest.fixture
def instrumented_execution(tracer):
    """Execute code with instrumentation and return tracer."""
    def _execute(code: str, filename: str = "<string>") -> Any:
        tracer.clear()
        globals_dict = exec_instrumented(code)
        return globals_dict
    
    return _execute


@pytest.fixture(params=list(SAMPLE_CODES.keys()))
def sample_code_execution(request, tracer):
    """Parametrized fixture that executes each sample code."""
    code_name = request.param
    code = SAMPLE_CODES[code_name]
    
    tracer.clear()
    globals_dict = exec_instrumented(code)
    
    return {
        'name': code_name,
        'code': code,
        'globals': globals_dict,
        'events': tracer.events.copy(),
        'tracer': tracer
    }


# Helper functions for assertions
def assert_has_event_type(events: List[TraceEvent], event_type: EventType, min_count: int = 1):
    """Assert that events contain at least min_count of the specified event type."""
    # Use EventType enum directly for consistent comparison
    actual_count = len([e for e in events if e.event_type == event_type])
    assert actual_count >= min_count, f"Expected at least {min_count} {event_type.value} events, got {actual_count}"


def assert_event_sequence(events: List[TraceEvent], expected_types: List[EventType]):
    """Assert that events follow the expected sequence of types."""
    assert EventMatcher.assert_sequence(events, expected_types), \
        f"Event sequence mismatch. Expected: {[t.value for t in expected_types]}, " \
        f"Got: {[e.event_type for e in events]}"


def assert_variable_value_event(events: List[TraceEvent], var_name: str, expected_value: Any):
    """Assert that a variable assignment event exists with the expected value."""
    # Use EventType enum for consistent comparison
    assign_events = [e for e in events if e.event_type == EventType.ASSIGN]
    assert len(assign_events) > 0, f"No assignment events found"
    
    # Find event with matching variable name and value using data dictionary format
    for event in assign_events:
        if (event.data.get('var_name') == var_name and 
            event.data.get('value') == expected_value):
            return  # Found matching event
    
    # If we get here, no matching event was found
    found_vars = []
    for event in assign_events:
        var = event.data.get('var_name', 'unknown')
        val = event.data.get('value', 'unknown')
        found_vars.append(f"{var}={val}")
    
    assert False, f"No assignment event found for '{var_name}' with value {expected_value}. Found: {found_vars}"


def assert_function_called(events: List[TraceEvent], func_name: str, expected_args: List[Any] = None):
    """Assert that a function was called with optional argument checking."""
    # Use EventType enum for consistent comparison
    function_events = [e for e in events if e.event_type == EventType.FUNCTION_ENTRY]
    
    # Find events with matching function name using data dictionary format
    matching_events = []
    for event in function_events:
        if event.data.get('func_name') == func_name:
            matching_events.append(event)
    
    assert len(matching_events) > 0, f"No function call events found for '{func_name}'"
    
    if expected_args is not None:
        # Check if any event has matching arguments
        for event in matching_events:
            if event.data.get('args') == expected_args:
                return  # Found matching event
        
        # If we get here, no matching args were found
        found_args = []
        for event in matching_events:
            args = event.data.get('args', [])
            found_args.append(args)
        
        assert False, f"Function '{func_name}' was not called with expected args {expected_args}. Found args: {found_args}"


def assert_performance_bounds(execution_time: float, max_time: float, operation_name: str = "Operation"):
    """Assert that execution time is within acceptable bounds."""
    assert execution_time <= max_time, \
        f"{operation_name} took {execution_time:.3f}s, expected <= {max_time:.3f}s"


def assert_event_count_bounds(events: List[TraceEvent], min_count: int, max_count: int, operation_name: str = "Operation"):
    """Assert that event count is within expected bounds."""
    actual_count = len(events)
    assert min_count <= actual_count <= max_count, \
        f"{operation_name} recorded {actual_count} events, expected {min_count}-{max_count}"


def assert_trace_matches_pattern(actual_events: List[TraceEvent], expected_events: List[Any], strict: bool = False):
    """Assert that actual tracer events match expected DSL events pattern.
    
    Args:
        actual_events: Events from the tracer
        expected_events: Events created with DSL trace() builder
        strict: If True, requires exact match. If False, allows actual to have more events.
    """
    if not expected_events:
        return
    
    if strict:
        assert len(actual_events) == len(expected_events), \
            f"Expected {len(expected_events)} events, got {len(actual_events)}"
    else:
        assert len(actual_events) >= len(expected_events), \
            f"Expected at least {len(expected_events)} events, got {len(actual_events)}"
    
    # Match events by type and key properties using data dictionary format
    expected_idx = 0
    for actual_event in actual_events:
        if expected_idx >= len(expected_events):
            if strict:
                assert False, f"Too many actual events. Expected {len(expected_events)}, got more"
            break
            
        expected_event = expected_events[expected_idx]
        
        # Check if this actual event matches the next expected event
        if actual_event.event_type == expected_event.event_type:
            # For assign events, also check variable name using data dictionary
            if (actual_event.event_type == EventType.ASSIGN and 
                hasattr(expected_event, 'data') and 
                'var_name' in expected_event.data):
                
                if actual_event.data.get('var_name') == expected_event.data['var_name']:
                    expected_idx += 1
            else:
                expected_idx += 1
    
    if expected_idx < len(expected_events):
        unmatched = len(expected_events) - expected_idx
        assert False, f"Failed to match {unmatched} expected events out of {len(expected_events)}"


# Pytest markers for test organization
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests for individual components")
    config.addinivalue_line("markers", "integration: Integration tests for component interaction")
    config.addinivalue_line("markers", "performance: Performance benchmarking tests")
    config.addinivalue_line("markers", "slow: Tests that take significant time to run")
    config.addinivalue_line("markers", "cli: Command-line interface tests")
    config.addinivalue_line("markers", "dsl: DSL functionality tests")


# Skip conditions
def skip_if_no_module(module_name: str):
    """Skip test if module is not available."""
    try:
        __import__(module_name)
        return pytest.mark.skip(f"Module {module_name} not available")
    except ImportError:
        return lambda func: func