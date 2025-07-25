"""
Trace visualization and comparison utilities for instrumentation tests.
Provides functions to create string representations and diffs of execution traces.
"""

import difflib
from typing import List
from dataclasses import dataclass
from pywhy.tracer import TraceEvent
from pywhy.events import EventType


@dataclass
class TraceComparison:
    """Result of comparing two traces."""
    actual_trace_str: str
    expected_trace_str: str
    diff_str: str
    matches: bool
    mismatch_details: List[str]


def format_trace_event(event: TraceEvent, include_details: bool = True) -> str:
    """
    Format a single trace event as a readable string.
    
    Args:
        event: The trace event to format
        include_details: Whether to include detailed information
        
    Returns:
        Formatted string representation of the event
    """
    event_type = getattr(event, 'event_type', 'unknown')
    #print(f"Formatting event: {event_type} with data: {event.data}") 
    
    data = event.data
    line_no = getattr(event, 'line_no', 0)
    filename = getattr(event, 'filename', '<unknown>')
    
    # Check if this is actually tracer format data that needs conversion
    if 'args' in data and isinstance(data['args'], tuple):
        # Convert tracer args tuple to proper data format
        converted_data = {}
        args = data['args']
        for i in range(0, len(args), 2):
            if i + 1 < len(args):
                converted_data[args[i]] = args[i + 1]
        data = converted_data
    elif 'arg_0' in data:
        # Convert numbered args to proper data format
        converted_data = {}
        i = 0
        while f'arg_{i}' in data:
            if f'arg_{i+1}' in data:
                key = data[f'arg_{i}']
                value = data[f'arg_{i+1}']
                converted_data[key] = value
                i += 2
            else:
                break
        if converted_data:
            data = converted_data
    
    assert (type(event_type) is EventType or isinstance(event_type, str))
    match event_type:
        case EventType.ASSIGN:
            var_name = data.get('var_name', '?')
            value = data.get('value', '?')
            base_str = f"ASSIGN {var_name} = {repr(value)}"
            
        case EventType.FUNCTION_ENTRY:
            func_name = data.get('func_name', '?')
            args = data.get('args', [])
            base_str = f"FUNCTION_ENTRY {func_name}({', '.join(map(repr, args))})"
        
        case EventType.RETURN:
            value = data.get('value', None)
            base_str = f"RETURN {repr(value)}"
        
        case EventType.BRANCH:
            branch_type = data.get('branch_type', data.get('type', '?'))
            taken = data.get('taken', data.get('result', '?'))
            base_str = f"BRANCH {branch_type} -> {taken}"
        
        case EventType.CONDITION:
            test = data.get('test', '?')
            result = data.get('result', '?')
            base_str = f"CONDITION {test} -> {result}"
        
        case EventType.ATTR_ASSIGN:
            obj_attr = data.get('obj_attr', '?')
            value = data.get('value', '?')
            base_str = f"ATTR_ASSIGN {obj_attr} = {repr(value)}"
        
        case EventType.SUBSCRIPT_ASSIGN:
            target = data.get('target', '?')
            value = data.get('value', '?')
            base_str = f"SUBSCRIPT_ASSIGN {target} = {repr(value)}"
        
        case EventType.SLICE_ASSIGN:
            target = data.get('target', '?')
            value = data.get('value', '?')
            base_str = f"SLICE_ASSIGN {target} = {repr(value)}"
        
        case EventType.AUG_ASSIGN:
            target = data.get('target', '?')
            op = data.get('op', '?')
            value = data.get('value', '?')
            base_str = f"AUG_ASSIGN {target} {op}= {repr(value)}"
        
        case EventType.LOOP_ITERATION:
            loop_var = data.get('loop_var', '?')
            value = data.get('value', '?')
            base_str = f"LOOP_ITERATION {loop_var} = {repr(value)}"
        
        case EventType.WHILE_CONDITION:
            condition = data.get('condition', '?')
            result = data.get('result', '?')
            base_str = f"WHILE_CONDITION {condition} -> {result}"
            
        case EventType.CALL:
            func_name = data.get('func_name', '?')
            args = data.get('args', [])
            base_str = f"CALL {func_name}({', '.join(map(repr, args))})"
        
        case _:
            base_str = f"{event_type.upper()} {data}"
    
    # Add all data information  
    data_info = f" | data: {dict(data)}" if data else ""
    
    if include_details:
        event_id = getattr(event, 'event_id', '?')
        return f"[{event_id:3}] {filename}:{line_no:3} | {base_str}{data_info}"
    else:
        return f"{base_str}{data_info}"


def format_trace(events: List[TraceEvent], title: str = "Trace", include_details: bool = True) -> str:
    """
    Format a list of trace events as a readable string.
    
    Args:
        events: List of trace events to format
        title: Title for the trace
        include_details: Whether to include detailed information
        
    Returns:
        Formatted string representation of the entire trace
    """
    if not events:
        return f"{title}:\n  <empty trace>\n"
    
    lines = [f"{title}:"]
    for i, event in enumerate(events):
        event_str = format_trace_event(event, include_details)
        lines.append(f"  {i+1:2}. {event_str}")
    
    return "\n".join(lines) + "\n"


def compare_traces(actual_events: List[TraceEvent], 
                  expected_events: List[TraceEvent],
                  actual_title: str = "Actual Trace",
                  expected_title: str = "Expected Trace") -> TraceComparison:
    """
    Compare two traces and generate a detailed comparison.
    
    Args:
        actual_events: The actual execution trace
        expected_events: The expected execution trace
        actual_title: Title for the actual trace
        expected_title: Title for the expected trace
        
    Returns:
        TraceComparison object with detailed comparison results
    """
    # Format both traces
    actual_trace_str = format_trace(actual_events, actual_title, include_details=False)
    expected_trace_str = format_trace(expected_events, expected_title, include_details=False)
    
    # Generate diff
    actual_lines = actual_trace_str.splitlines(keepends=True)
    expected_lines = expected_trace_str.splitlines(keepends=True)
    
    diff_lines = list(difflib.unified_diff(
        expected_lines, 
        actual_lines,
        fromfile=expected_title,
        tofile=actual_title,
        lineterm=''
    ))
    
    diff_str = ''.join(diff_lines)
    
    # Check if traces match
    matches = len(actual_events) == len(expected_events)
    mismatch_details = []
    
    if matches:
        for i, (actual, expected) in enumerate(zip(actual_events, expected_events)):
            actual_formatted = format_trace_event(actual, include_details=False)
            expected_formatted = format_trace_event(expected, include_details=False)
            
            if actual_formatted != expected_formatted:
                matches = False
                mismatch_details.append(
                    f"Event {i+1}: Expected '{expected_formatted}' but got '{actual_formatted}'"
                )
    else:
        mismatch_details.append(
            f"Different number of events: expected {len(expected_events)}, got {len(actual_events)}"
        )
    
    return TraceComparison(
        actual_trace_str=actual_trace_str,
        expected_trace_str=expected_trace_str,
        diff_str=diff_str,
        matches=matches,
        mismatch_details=mismatch_details
    )


def display_trace_comparison(comparison: TraceComparison, show_full_traces: bool = True) -> str:
    """
    Display a formatted trace comparison for Jupyter notebook output.
    
    Args:
        comparison: The trace comparison result
        show_full_traces: Whether to show full traces or just the diff
        
    Returns:
        Formatted string for display
    """
    lines = []
    
    if comparison.matches:
        lines.append("✅ TRACES MATCH")
    else:
        lines.append("❌ TRACES DO NOT MATCH")
        lines.append("")
        lines.append("Mismatch Details:")
        for detail in comparison.mismatch_details:
            lines.append(f"  • {detail}")
    
    lines.append("")
    
    if show_full_traces:
        lines.append("=" * 60)
        lines.append(comparison.expected_trace_str)
        lines.append("=" * 60)
        lines.append(comparison.actual_trace_str)
        lines.append("=" * 60)
    
    if comparison.diff_str:
        lines.append("DIFF:")
        lines.append(comparison.diff_str)
    else:
        lines.append("No differences found.")
    
    return "\n".join(lines)


def create_test_trace_comparison_function(test_name: str):
    """
    Create a trace comparison function for a specific test.
    
    Args:
        test_name: Name of the test
        
    Returns:
        Function that can be called to compare traces for this test
    """
    def compare_test_traces(actual_events: List[TraceEvent], 
                           expected_events: List[TraceEvent],
                           show_details: bool = True) -> str:
        """
        Compare traces for this specific test and return formatted output.
        """
        comparison = compare_traces(
            actual_events, 
            expected_events,
            actual_title=f"Actual Trace ({test_name})",
            expected_title=f"Expected Trace ({test_name})"
        )
        
        return display_trace_comparison(comparison, show_details)
    
    return compare_test_traces


def create_jupyter_trace_display(actual_events: List[TraceEvent], 
                                expected_events: List[TraceEvent],
                                test_name: str = "Test") -> str:
    """
    Create a Jupyter-friendly display of trace comparison.
    
    Args:
        actual_events: The actual execution trace
        expected_events: The expected execution trace
        test_name: Name of the test for display purposes
        
    Returns:
        HTML-formatted string for Jupyter display
    """
    comparison = compare_traces(actual_events, expected_events)
    
    # Create HTML output
    html_parts = []
    
    # Header
    status_color = "green" if comparison.matches else "red"
    status_icon = "✅" if comparison.matches else "❌"
    html_parts.append(f'<h3 style="color: {status_color};">{status_icon} {test_name}</h3>')
    
    if not comparison.matches:
        html_parts.append('<div style="background-color: #ffe6e6; padding: 10px; margin: 10px 0;">')
        html_parts.append('<strong>Mismatch Details:</strong><ul>')
        for detail in comparison.mismatch_details:
            html_parts.append(f'<li>{detail}</li>')
        html_parts.append('</ul></div>')
    
    # Traces in columns
    html_parts.append('<div style="display: flex; gap: 20px;">')
    
    # Expected trace
    html_parts.append('<div style="flex: 1;">')
    html_parts.append('<h4>Expected Trace:</h4>')
    html_parts.append('<pre style="background-color: #f0f0f0; padding: 10px; font-family: monospace; font-size: 12px;">')
    html_parts.append(comparison.expected_trace_str.replace('<', '&lt;').replace('>', '&gt;'))
    html_parts.append('</pre></div>')
    
    # Actual trace
    html_parts.append('<div style="flex: 1;">')
    html_parts.append('<h4>Actual Trace:</h4>')
    html_parts.append('<pre style="background-color: #f0f0f0; padding: 10px; font-family: monospace; font-size: 12px;">')
    html_parts.append(comparison.actual_trace_str.replace('<', '&lt;').replace('>', '&gt;'))
    html_parts.append('</pre></div>')
    
    html_parts.append('</div>')
    
    # Diff
    if comparison.diff_str:
        html_parts.append('<h4>Diff:</h4>')
        html_parts.append('<pre style="background-color: #f8f8f8; padding: 10px; font-family: monospace; font-size: 11px;">')
        html_parts.append(comparison.diff_str.replace('<', '&lt;').replace('>', '&gt;'))
        html_parts.append('</pre>')
    
    return ''.join(html_parts)


# Convenience functions for common use cases

def show_trace_diff(actual_events: List[TraceEvent], 
                   expected_events: List[TraceEvent],
                   test_name: str = "Test") -> None:
    """
    Display trace comparison in Jupyter notebook.
    """
    from IPython.display import HTML, display
    html_output = create_jupyter_trace_display(actual_events, expected_events, test_name)
    display(HTML(html_output))


def print_trace_comparison(actual_events: List[TraceEvent], 
                          expected_events: List[TraceEvent],
                          test_name: str = "Test") -> None:
    """
    Print trace comparison to console.
    """
    comparison = compare_traces(actual_events, expected_events)
    output = display_trace_comparison(comparison)
    print(f"\n{test_name}:")
    print(output)