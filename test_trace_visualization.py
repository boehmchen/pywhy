#!/usr/bin/env python3
"""
Test script to verify trace visualization functionality.
Run this to make sure exec_instrumented produces traces and visualization works.
"""

from pywhy.instrumenter import exec_instrumented
from pywhy.tracer import get_tracer
from pywhy.trace_dsl import trace
from pywhy.trace_visualization import (
    format_trace, compare_traces, display_trace_comparison, 
    print_trace_comparison
)

def test_simple_assignment():
    """Test simple assignment tracing and visualization."""
    print("=" * 60)
    print("Testing Simple Assignment Tracing")
    print("=" * 60)
    
    # Get global tracer and clear it
    tracer = get_tracer()
    tracer.clear()
    
    # Code to trace
    code = """
x = 10
y = 20
z = x + y
"""
    
    # Execute with instrumentation
    print("Executing code with instrumentation...")
    exec_instrumented(code)
    
    # Get actual events
    actual_events = tracer.events
    print(f"Number of events recorded: {len(actual_events)}")
    
    # Create expected trace using DSL
    expected_trace = (
        trace()
        .assign("x", 10)
        .assign("y", 20)
        .assign("z", 30)
        .build()
    )
    
    # Show formatted traces
    print("\nActual trace:")
    print(format_trace(actual_events, "Actual Assignment Trace"))
    
    print("Expected trace:")
    print(format_trace(expected_trace, "Expected Assignment Trace"))
    
    # Show comparison
    print("Trace comparison:")
    print_trace_comparison(actual_events, expected_trace, "Simple Assignment Test")

def test_function_call():
    """Test function call tracing and visualization."""
    print("\n" + "=" * 60)
    print("Testing Function Call Tracing")
    print("=" * 60)
    
    # Get global tracer and clear it
    tracer = get_tracer()
    tracer.clear()
    
    # Code to trace
    code = """
def add_numbers(a, b):
    result = a + b
    return result

output = add_numbers(5, 3)
"""
    
    # Execute with instrumentation
    print("Executing function code with instrumentation...")
    exec_instrumented(code)
    
    # Get actual events
    actual_events = tracer.events
    print(f"Number of events recorded: {len(actual_events)}")
    
    # Create expected trace using DSL
    expected_trace = (
        trace()
        .function_entry("add_numbers", [5, 3])
        .assign("result", 8)
        .return_event(8)
        .assign("output", 8)
        .build()
    )
    
    # Show formatted traces
    print("\nActual trace:")
    print(format_trace(actual_events, "Actual Function Trace"))
    
    print("Expected trace:")
    print(format_trace(expected_trace, "Expected Function Trace"))
    
    # Show comparison
    print("Trace comparison:")
    print_trace_comparison(actual_events, expected_trace, "Function Call Test")

def test_tracer_raw_events():
    """Show raw tracer events for debugging."""
    print("\n" + "=" * 60)
    print("Raw Tracer Events (for debugging)")
    print("=" * 60)
    
    tracer = get_tracer()
    tracer.clear()
    
    code = "x = 42"
    exec_instrumented(code)
    
    print(f"Number of raw events: {len(tracer.events)}")
    for i, event in enumerate(tracer.events):
        print(f"Event {i}: {event}")
        print(f"  Type: {type(event)}")
        print(f"  Attributes: {[attr for attr in dir(event) if not attr.startswith('_')]}")
        if hasattr(event, 'args'):
            print(f"  Args: {event.args}")
        if hasattr(event, 'data'):
            print(f"  Data: {getattr(event, 'data', 'No data attribute')}")
        print()

if __name__ == "__main__":
    print("Testing trace visualization functionality...")
    
    try:
        test_tracer_raw_events()
        test_simple_assignment()
        test_function_call()
        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()