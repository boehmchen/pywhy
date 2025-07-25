"""
Helper functions for displaying trace comparisons in Jupyter Lab.
Import this module in your Jupyter notebook to easily visualize test traces.
"""

from typing import Dict, Any

def run_test_with_trace_comparison(test_class_name: str, test_method_name: str) -> Dict[str, Any]:
    
    """
    Run a specific test and return trace comparison functions.
    
    Args:
        test_class_name: Name of the test class (e.g. 'TestBasicInstrumentation')
        test_method_name: Name of the test method (e.g. 'test_simple_assignment_instrumentation')
    
    Returns:
        Dictionary with trace comparison functions and data
    """
    # Import the test module
    try:
        from tests.test_instrumentation import (
            TestBasicInstrumentation, TestAdvancedInstrumentation,
            TestDataStructureInstrumentation, TestComplexProgramInstrumentation
        )
    except ImportError:
        print("Could not import test classes. Make sure you're running from the pywhy directory.")
        return {}
    
    # Get the test class
    test_classes = {
        'TestBasicInstrumentation': TestBasicInstrumentation,
        'TestAdvancedInstrumentation': TestAdvancedInstrumentation, 
        'TestDataStructureInstrumentation': TestDataStructureInstrumentation,
        'TestComplexProgramInstrumentation': TestComplexProgramInstrumentation
    }
    
    if test_class_name not in test_classes:
        print(f"Unknown test class: {test_class_name}")
        print(f"Available classes: {list(test_classes.keys())}")
        return {}
    
    test_class = test_classes[test_class_name]
    
    # Create test instance and run the test
    test_instance = test_class()
    
    # We need to set up the test fixtures manually
    # This is a simplified version - in a real scenario you'd use pytest fixtures
    try:
        # Mock the fixtures - this is a simplified approach
        class MockTracer:
            def __init__(self):
                self.events = []
        
        def mock_instrumented_execution(code):
            # This would normally run the actual instrumentation
            # For now, we'll just return empty
            return []
        
        tracer = MockTracer()
        
        # Try to run the test method
        method = getattr(test_instance, test_method_name)
        method(tracer, mock_instrumented_execution)
        
        # Extract the trace comparison functions if they were added
        comparison_functions = {}
        for attr_name in dir(test_instance):
            if 'trace' in attr_name.lower() and callable(getattr(test_instance, attr_name)):
                comparison_functions[attr_name] = getattr(test_instance, attr_name)
        
        return {
            'test_instance': test_instance,
            'tracer': tracer,
            'comparison_functions': comparison_functions
        }
        
    except Exception as e:
        print(f"Error running test: {e}")
        return {}


def show_all_test_traces():
    """Show trace comparisons for all major tests."""
    test_methods = [
        ('TestBasicInstrumentation', 'test_simple_assignment_instrumentation'),
        ('TestBasicInstrumentation', 'test_function_definition_and_call'),
        ('TestAdvancedInstrumentation', 'test_recursive_function_instrumentation'),
    ]
    
    for test_class, test_method in test_methods:
        print(f"\n{'='*60}")
        print(f"Running {test_class}.{test_method}")
        print('='*60)
        
        result = run_test_with_trace_comparison(test_class, test_method)
        if result and 'comparison_functions' in result:
            funcs = result['comparison_functions']
            for func_name, func in funcs.items():
                if 'print' in func_name and 'traces' in func_name:
                    try:
                        func()
                        break
                    except Exception as e:
                        print(f"Error calling {func_name}: {e}")


# Simplified functions that can be called directly

def show_simple_assignment_test():
    """Show trace comparison for simple assignment test."""
    print("Simple Assignment Test Trace Comparison")
    print("="*50)
    
    # This would normally run the actual test and show results
    # For now, we'll show a placeholder
    print("""
    This function would show:
    1. Expected trace: assignments to x, y, z, x (reassignment), a, b
    2. Actual trace: what the instrumentation actually recorded
    3. Diff: differences between expected and actual
    
    To use this properly, run the test first and then call the
    trace comparison functions that get attached to the test instance.
    """)


def show_function_call_test():
    """Show trace comparison for function call test."""
    print("Function Call Test Trace Comparison") 
    print("="*50)
    
    print("""
    This function would show:
    1. Expected trace: function entries, returns, variable assignments
    2. Actual trace: what the instrumentation actually recorded  
    3. Diff: differences between expected and actual
    
    To use this properly, run the test first and then call the
    trace comparison functions that get attached to the test instance.
    """)


def show_recursion_test():
    """Show trace comparison for recursion test."""
    print("Recursion Test Trace Comparison")
    print("="*50)
    
    print("""
    This function would show:
    1. Expected trace: recursive function calls with proper nesting
    2. Actual trace: what the instrumentation actually recorded
    3. Diff: differences between expected and actual
    
    To use this properly, run the test first and then call the
    trace comparison functions that get attached to the test instance.
    """)


# Instructions for Jupyter users
JUPYTER_INSTRUCTIONS = """
# Trace Visualization in Jupyter Lab

To visualize trace comparisons in Jupyter Lab:

## Option 1: Run tests and access comparison functions
```python
import pytest
import sys
sys.path.append('/path/to/pywhy')

# Run a specific test
pytest.main(['-v', 'tests/test_instrumentation.py::TestBasicInstrumentation::test_simple_assignment_instrumentation'])

# The test will have attached comparison functions that you can call
# (This requires modifications to the test to store the functions)
```

## Option 2: Import and use visualization functions directly
```python
from pywhy.trace_visualization import show_trace_diff, format_trace, compare_traces
from pywhy.trace_dsl import trace

# Create expected trace
expected = trace().assign("x", 10).assign("y", 20).build()

# Get actual trace from running instrumentation
# actual = run_your_instrumented_code()

# Show comparison
# show_trace_diff(actual, expected, "My Test")
```

## Option 3: Use the helper functions in this module
```python
from jupyter_trace_helpers import show_simple_assignment_test, show_function_call_test

show_simple_assignment_test()
show_function_call_test()
```

Note: For full functionality, you need to run the actual tests with instrumentation enabled.
"""

def show_instructions():
    """Display instructions for using trace visualization in Jupyter."""
    print(JUPYTER_INSTRUCTIONS)


if __name__ == "__main__":
    show_instructions()