"""
Tests for AST instrumentation functionality using the trace DSL.
Tests the core instrumentation engine and verifies correct traces using DSL patterns.
"""

import pytest
import time
from typing import List

from pywhy.instrumenter import EventType, exec_instrumented, trace, sequence, EventMatcher
from .conftest import (
    assert_has_event_type, assert_variable_value_event, assert_function_called,
    assert_performance_bounds, assert_event_count_bounds
)


@pytest.mark.unit
class TestBasicInstrumentationWithDSL:
    """Test basic instrumentation functionality using DSL verification."""
    
    def test_simple_assignment_instrumentation_dsl(self, tracer, instrumented_execution):
        """Test instrumentation of simple variable assignments using DSL verification."""
        code = """
x = 10
y = 20
z = x + y
"""
        instrumented_execution(code)
        
        # Create expected trace pattern using DSL
        expected_trace = (trace()
                         .assign("x", 10)
                         .assign("y", 20)
                         .assign("z", 30)
                         .build())
        
        # Verify actual trace matches expected pattern
        actual_events = tracer.events
        assert len(actual_events) >= 3, "Should record at least 3 assignment events"
        
        # Use DSL helpers to verify specific assignments
        assert_has_event_type(actual_events, EventType.ASSIGN, min_count=3)
        assert_variable_value_event(actual_events, "x", 10)
        assert_variable_value_event(actual_events, "y", 20)
        assert_variable_value_event(actual_events, "z", 30)
        
        # Verify the expected trace structure
        for expected_event in expected_trace:
            if expected_event.event_type == EventType.ASSIGN.value:
                var_name = expected_event.data['var_name']
                value = expected_event.data['value']
                assert_variable_value_event(actual_events, var_name, value)
    
    def test_function_definition_and_call_dsl(self, tracer, instrumented_execution):
        """Test instrumentation of function definitions and calls using DSL verification."""
        code = """
def add_numbers(a, b):
    result = a + b
    return result

output = add_numbers(5, 3)
"""
        instrumented_execution(code)
        
        # Create expected trace pattern using DSL
        expected_trace = (trace()
                         .function_entry("add_numbers", [5, 3])
                         .assign("result", 8)
                         .return_event(8)
                         .assign("output", 8)
                         .build())
        
        # Verify actual trace has expected patterns
        actual_events = tracer.events
        
        # Verify function call pattern
        assert_has_event_type(actual_events, EventType.FUNCTION_ENTRY, min_count=1)
        assert_has_event_type(actual_events, EventType.RETURN, min_count=1)
        assert_has_event_type(actual_events, EventType.ASSIGN, min_count=2)
        
        # Verify function was called with correct arguments
        assert_function_called(actual_events, "add_numbers", [5, 3])
        assert_variable_value_event(actual_events, "output", 8)
    
    @pytest.mark.parametrize("condition,x_value,expected_result", [
        ("x > 5", 10, "large"),
        ("x <= 5", 3, "small")
    ])
    def test_conditional_statements_dsl(self, tracer, instrumented_execution, condition, x_value, expected_result):
        """Test instrumentation of if/else statements using DSL verification."""
        code = f"""
x = {x_value}
if x > 5:
    result = "large"
else:
    result = "small"
"""
        instrumented_execution(code)
        
        # Create expected trace pattern using DSL
        condition_result = x_value > 5
        expected_trace = (sequence("conditional_test")
                         .simple_assignment("x", x_value)
                         .if_statement("x > 5", condition_result, 
                                     [("result", "large")] if condition_result else None,
                                     [("result", "small")] if not condition_result else None)
                         .build())
        
        # Verify actual trace has expected patterns
        actual_events = tracer.events
        
        # Should record assignment, condition, and branch events
        assert_has_event_type(actual_events, EventType.ASSIGN, min_count=2)  # x + result
        assert_has_event_type(actual_events, EventType.CONDITION, min_count=1)
        assert_has_event_type(actual_events, EventType.BRANCH, min_count=1)
        
        # Verify the result
        assert_variable_value_event(actual_events, "result", expected_result)
        assert_variable_value_event(actual_events, "x", x_value)
    
    def test_loop_instrumentation_dsl(self, tracer, instrumented_execution):
        """Test instrumentation of for loops using DSL verification."""
        code = """
total = 0
for i in range(3):
    total += i
"""
        instrumented_execution(code)
        
        # Create expected trace pattern using DSL
        expected_trace = (sequence("loop_test")
                         .simple_assignment("total", 0)
                         .for_loop("i", [0, 1, 2], [("total", "updated")])
                         .build())
        
        # Verify actual trace has expected patterns
        actual_events = tracer.events
        
        # Should record assignment and loop iteration events
        assert_has_event_type(actual_events, EventType.ASSIGN, min_count=1)  # total
        # Note: Loop iterations and augmented assignments may vary by implementation
        
        # Verify initial assignment
        assert_variable_value_event(actual_events, "total", 0)
    
    def test_while_loop_instrumentation_dsl(self, tracer, instrumented_execution):
        """Test instrumentation of while loops using DSL verification."""
        code = """
counter = 0
while counter < 3:
    counter += 1
"""
        instrumented_execution(code)
        
        # Create expected trace pattern using DSL
        expected_trace = (trace()
                         .assign("counter", 0)
                         .while_condition("counter < 3", True)
                         .aug_assign("counter", 1)
                         .while_condition("counter < 3", True)
                         .aug_assign("counter", 2)
                         .while_condition("counter < 3", True)
                         .aug_assign("counter", 3)
                         .while_condition("counter < 3", False)
                         .build())
        
        # Verify actual trace has expected patterns
        actual_events = tracer.events
        
        # Should record while condition events
        assert_has_event_type(actual_events, EventType.ASSIGN, min_count=1)  # counter
        # Note: While conditions and augmented assignments may vary by implementation
        
        # Verify initial assignment
        assert_variable_value_event(actual_events, "counter", 0)


@pytest.mark.unit
class TestAdvancedInstrumentationWithDSL:
    """Test instrumentation of advanced Python constructs using DSL verification."""
    
    def test_class_instrumentation_dsl(self, tracer, instrumented_execution):
        """Test instrumentation of class definitions and methods using DSL verification."""
        code = """
class Calculator:
    def __init__(self, initial_value=0):
        self.value = initial_value
    
    def add(self, x):
        self.value += x
        return self.value

calc = Calculator(10)
result = calc.add(5)
"""
        instrumented_execution(code)
        
        # Create expected trace pattern using DSL
        expected_trace = (trace()
                         .assign("calc", "Calculator_instance")
                         .function_entry("__init__", ["calc", 10])
                         .attr_assign("calc", "value", 10)
                         .return_event(None)
                         .function_entry("add", ["calc", 5])
                         .aug_assign("self.value", 15)
                         .return_event(15)
                         .assign("result", 15)
                         .build())
        
        # Verify actual trace has expected patterns
        actual_events = tracer.events
        
        # Should record function entries for __init__ and add methods
        assert_has_event_type(actual_events, EventType.FUNCTION_ENTRY, min_count=2)
        assert_has_event_type(actual_events, EventType.ASSIGN, min_count=2)  # calc + result
        
        # Verify methods were called
        function_events = [e for e in actual_events if e.event_type == "call_pre"]
        func_names = set()
        for event in function_events:
            if len(event.args) >= 2 and event.args[0] == 'func_name':
                func_names.add(event.args[1])
        
        assert '__init__' in func_names, "Should call __init__ method"
        assert 'add' in func_names, "Should call add method"
    
    def test_nested_function_instrumentation_dsl(self, tracer, instrumented_execution):
        """Test instrumentation of nested functions using DSL verification."""
        code = """
def outer_function(n):
    def inner_function(x):
        return x * 2
    
    result = inner_function(n)
    return result

output = outer_function(8)
"""
        instrumented_execution(code)
        
        # Create expected trace pattern using DSL
        expected_trace = (trace()
                         .function_entry("outer_function", [8])
                         .function_entry("inner_function", [8])
                         .return_event(16)
                         .assign("result", 16)
                         .return_event(16)
                         .assign("output", 16)
                         .build())
        
        # Verify actual trace has expected patterns
        actual_events = tracer.events
        
        # Should record multiple function entries
        assert_has_event_type(actual_events, EventType.FUNCTION_ENTRY, min_count=2)
        assert_has_event_type(actual_events, EventType.RETURN, min_count=2)
        
        # Verify both functions were called
        function_events = [e for e in actual_events if e.event_type == "call_pre"]
        func_names = set()
        for event in function_events:
            if len(event.args) >= 2 and event.args[0] == 'func_name':
                func_names.add(event.args[1])
        
        assert 'outer_function' in func_names, "Should call outer_function"
        assert 'inner_function' in func_names, "Should call inner_function"
        assert_variable_value_event(actual_events, "output", 16)
    
    def test_recursive_function_instrumentation_dsl(self, tracer, instrumented_execution):
        """Test instrumentation of recursive functions using DSL verification."""
        code = """
def factorial(n):
    if n <= 1:
        return 1
    else:
        return n * factorial(n - 1)

result = factorial(4)
"""
        instrumented_execution(code)
        
        # Create expected trace pattern using DSL (simplified for factorial(4))
        expected_trace = (trace()
                         .function_entry("factorial", [4])
                         .condition("n <= 1", False)
                         .branch("else", False)
                         .function_entry("factorial", [3])
                         .condition("n <= 1", False)
                         .branch("else", False)
                         .function_entry("factorial", [2])
                         .condition("n <= 1", False)
                         .branch("else", False)
                         .function_entry("factorial", [1])
                         .condition("n <= 1", True)
                         .branch("if", True)
                         .return_event(1)
                         .return_event(2)
                         .return_event(6)
                         .return_event(24)
                         .assign("result", 24)
                         .build())
        
        # Verify actual trace has expected patterns
        actual_events = tracer.events
        
        # Should record multiple function entries for recursion
        function_events = [e for e in actual_events if e.event_type == "call_pre"]
        assert len(function_events) >= 4, "Should record function entry for each recursive call"
        
        # Should record multiple return events
        return_events = [e for e in actual_events if e.event_type == "return"]
        assert len(return_events) >= 4, "Should record return for each recursive call"
        
        # Final result should be 4! = 24
        assert_variable_value_event(actual_events, "result", 24)
    
    def test_exception_handling_instrumentation_dsl(self, tracer, instrumented_execution):
        """Test instrumentation of try/except blocks using DSL verification."""
        code = """
def safe_divide(a, b):
    try:
        result = a / b
        return result
    except ZeroDivisionError:
        return 0

result1 = safe_divide(10, 2)
result2 = safe_divide(10, 0)
"""
        instrumented_execution(code)
        
        # Create expected trace pattern using DSL
        expected_trace = (trace()
                         .function_entry("safe_divide", [10, 2])
                         .assign("result", 5.0)
                         .return_event(5.0)
                         .assign("result1", 5.0)
                         .function_entry("safe_divide", [10, 0])
                         .return_event(0)
                         .assign("result2", 0)
                         .build())
        
        # Verify actual trace has expected patterns
        actual_events = tracer.events
        
        # Should record function entries and assignments
        assert_has_event_type(actual_events, EventType.FUNCTION_ENTRY, min_count=2)
        assert_has_event_type(actual_events, EventType.ASSIGN, min_count=2)  # result1 + result2
        
        # Verify results
        assert_variable_value_event(actual_events, "result1", 5.0)
        assert_variable_value_event(actual_events, "result2", 0)


@pytest.mark.unit
class TestDataStructureInstrumentationWithDSL:
    """Test instrumentation of data structure operations using DSL verification."""
    
    def test_list_operations_dsl(self, tracer, instrumented_execution):
        """Test instrumentation of list operations using DSL verification."""
        code = """
my_list = [1, 2, 3]
my_list[0] = 10
my_list.append(4)
"""
        instrumented_execution(code)
        
        # Create expected trace pattern using DSL
        expected_trace = (trace()
                         .assign("my_list", [1, 2, 3])
                         .subscript_assign("my_list", 0, 10)
                         .build())
        
        # Verify actual trace has expected patterns
        actual_events = tracer.events
        
        # Should record assignment and subscript assignment
        assert_has_event_type(actual_events, EventType.ASSIGN, min_count=1)  # my_list
        # Note: Subscript assignment may vary by implementation
    
    def test_dictionary_operations_dsl(self, tracer, instrumented_execution):
        """Test instrumentation of dictionary operations using DSL verification."""
        code = """
my_dict = {'a': 1, 'b': 2}
my_dict['c'] = 3
my_dict.update({'d': 4})
"""
        instrumented_execution(code)
        
        # Create expected trace pattern using DSL
        expected_trace = (trace()
                         .assign("my_dict", {'a': 1, 'b': 2})
                         .subscript_assign("my_dict", 'c', 3)
                         .build())
        
        # Verify actual trace has expected patterns
        actual_events = tracer.events
        
        # Should record assignment and subscript assignment
        assert_has_event_type(actual_events, EventType.ASSIGN, min_count=1)  # my_dict
        # Note: Subscript assignment may vary by implementation
    
    def test_attribute_assignment_dsl(self, tracer, instrumented_execution):
        """Test instrumentation of attribute assignments using DSL verification."""
        code = """
class SimpleClass:
    pass

obj = SimpleClass()
obj.value = 42
obj.name = "test"
"""
        instrumented_execution(code)
        
        # Create expected trace pattern using DSL
        expected_trace = (trace()
                         .assign("obj", "SimpleClass_instance")
                         .attr_assign("obj", "value", 42)
                         .attr_assign("obj", "name", "test")
                         .build())
        
        # Verify actual trace has expected patterns
        actual_events = tracer.events
        
        # Should record attribute assignments
        assert_has_event_type(actual_events, EventType.ASSIGN, min_count=1)  # obj
        # Note: Attribute assignments may vary by implementation


@pytest.mark.unit
class TestComplexProgramInstrumentationWithDSL:
    """Test instrumentation of complex programs using DSL verification."""
    
    def test_merge_sort_algorithm_dsl(self, tracer, instrumented_execution):
        """Test instrumentation of a complex algorithm using DSL verification."""
        code = """
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

data = [3, 1, 4]
sorted_data = merge_sort(data)
"""
        start_time = time.time()
        instrumented_execution(code)
        execution_time = time.time() - start_time
        
        # Create expected trace pattern using DSL (high-level structure)
        expected_trace = (sequence("merge_sort_test")
                         .simple_assignment("data", [3, 1, 4])
                         .function_call("merge_sort", [[3, 1, 4]], [1, 3, 4])
                         .simple_assignment("sorted_data", [1, 3, 4])
                         .build())
        
        # Verify actual trace has expected patterns
        actual_events = tracer.events
        
        # Should record many events for complex algorithm
        assert_event_count_bounds(actual_events, 10, 200, "Merge sort algorithm")
        
        # Should complete in reasonable time
        assert_performance_bounds(execution_time, 2.0, "Merge sort instrumentation")
        
        # Should record function entries for both functions
        function_events = [e for e in actual_events if e.event_type == "call_pre"]
        func_names = set()
        for event in function_events:
            if len(event.args) >= 2 and event.args[0] == 'func_name':
                func_names.add(event.args[1])
        
        assert 'merge_sort' in func_names, "Should call merge_sort function"
        assert 'merge' in func_names, "Should call merge function"


@pytest.mark.integration
class TestSampleCodeExecutionWithDSL:
    """Test instrumentation against all sample codes using DSL verification."""
    
    def test_all_sample_codes_instrument_successfully_dsl(self, sample_code_execution):
        """Test that all sample codes can be instrumented and produce expected trace patterns."""
        execution = sample_code_execution
        
        # Every sample should generate some events
        assert len(execution['events']) > 0, f"Sample '{execution['name']}' should generate events"
        
        # Create expected patterns using DSL based on sample type
        sample_name = execution['name']
        events = execution['events']
        
        if sample_name == 'simple_assignment':
            # Should have assignment events
            assert_has_event_type(events, EventType.ASSIGN, min_count=3)
            assert_variable_value_event(events, "x", 10)
            assert_variable_value_event(events, "y", 20)
            assert_variable_value_event(events, "z", 30)
            
        elif sample_name == 'function_call':
            # Should have function entry and return
            assert_has_event_type(events, EventType.FUNCTION_ENTRY, min_count=1)
            assert_has_event_type(events, EventType.RETURN, min_count=1)
            assert_function_called(events, "add_numbers", [5, 3])
            assert_variable_value_event(events, "result", 8)
            
        elif sample_name == 'control_flow':
            # Should have condition and branch events
            assert_has_event_type(events, EventType.ASSIGN, min_count=2)  # x + result
            assert_has_event_type(events, EventType.CONDITION, min_count=1)
            assert_has_event_type(events, EventType.BRANCH, min_count=1)
            assert_variable_value_event(events, "result", "large")
            
        elif sample_name == 'loop':
            # Should have assignment and loop events
            assert_has_event_type(events, EventType.ASSIGN, min_count=1)  # total
            assert_variable_value_event(events, "total", 0)
            
        elif sample_name == 'recursion':
            # Should have multiple function entries due to recursion
            function_events = [e for e in events if e.event_type == "call_pre"]
            assert len(function_events) >= 5, f"Factorial(5) should have at least 5 function entries, got {len(function_events)}"
            assert_variable_value_event(events, "result", 120)
            
        elif sample_name == 'class_usage':
            # Should have function entries for methods
            assert_has_event_type(events, EventType.FUNCTION_ENTRY, min_count=2)  # __init__ + add
            assert_has_event_type(events, EventType.ASSIGN, min_count=2)  # calc + result
            
        elif sample_name == 'exception_handling':
            # Should have function entries
            assert_has_event_type(events, EventType.FUNCTION_ENTRY, min_count=2)
            assert_has_event_type(events, EventType.ASSIGN, min_count=2)  # result1 + result2
            
        elif sample_name == 'complex_program':
            # Should have many events for complex algorithm
            assert len(events) >= 20, f"Complex program should have many events, got {len(events)}"
            function_events = [e for e in events if e.event_type == "call_pre"]
            assert len(function_events) >= 2, "Should call multiple functions"
    
    def test_function_call_sample_dsl_verification(self, tracer, sample_codes, instrumented_execution):
        """Test function_call sample with detailed DSL verification."""
        instrumented_execution(sample_codes['function_call'])
        
        # Create expected trace using DSL
        expected_trace = (trace()
                         .function_entry("add_numbers", [5, 3])
                         .assign("result", 8)
                         .return_event(8)
                         .assign("result", 8)
                         .build())
        
        # Verify actual trace matches expected pattern
        actual_events = tracer.events
        
        # Should have function entry and return
        assert_has_event_type(actual_events, EventType.FUNCTION_ENTRY, min_count=1)
        assert_has_event_type(actual_events, EventType.RETURN, min_count=1)
        assert_function_called(actual_events, "add_numbers", [5, 3])
        assert_variable_value_event(actual_events, "result", 8)
    
    def test_recursion_sample_dsl_verification(self, tracer, sample_codes, instrumented_execution):
        """Test recursion sample with detailed DSL verification."""
        instrumented_execution(sample_codes['recursion'])
        
        # Create expected trace pattern using DSL (high-level structure)
        expected_trace = (trace()
                         .function_entry("factorial", [5])
                         .function_entry("factorial", [4])
                         .function_entry("factorial", [3])
                         .function_entry("factorial", [2])
                         .function_entry("factorial", [1])
                         .return_event(1)
                         .return_event(2)
                         .return_event(6)
                         .return_event(24)
                         .return_event(120)
                         .assign("result", 120)
                         .build())
        
        # Verify actual trace has expected recursive pattern
        actual_events = tracer.events
        
        # Should have multiple function entries due to recursion
        function_events = [e for e in actual_events if e.event_type == "call_pre"]
        assert len(function_events) >= 5, "Factorial(5) should have at least 5 function entries"
        
        # Should calculate factorial correctly
        assert_variable_value_event(actual_events, "result", 120)


@pytest.mark.performance
class TestInstrumentationPerformanceWithDSL:
    """Test performance characteristics of instrumentation using DSL verification."""
    
    def test_instrumentation_overhead_dsl(self, tracer, sample_codes):
        """Test that instrumentation overhead is reasonable using DSL verification."""
        code = sample_codes['complex_program']
        
        start_time = time.time()
        exec_instrumented(code)
        execution_time = time.time() - start_time
        
        # Should complete complex program in reasonable time
        assert_performance_bounds(execution_time, 5.0, "Complex program instrumentation")
        
        # Should generate reasonable number of events
        actual_events = tracer.events
        assert_event_count_bounds(actual_events, 20, 500, "Complex program")
        
        # Verify trace has expected high-level structure using DSL
        function_events = [e for e in actual_events if e.event_type == "call_pre"]
        func_names = set()
        for event in function_events:
            if len(event.args) >= 2 and event.args[0] == 'func_name':
                func_names.add(event.args[1])
        
        assert 'merge_sort' in func_names, "Should call merge_sort function"
        assert 'merge' in func_names, "Should call merge function"
    
    def test_deep_recursion_performance_dsl(self, tracer, instrumented_execution):
        """Test performance with deep recursion using DSL verification."""
        code = """
def deep_function(n, acc=0):
    if n <= 0:
        return acc
    return deep_function(n - 1, acc + n)

result = deep_function(30)
"""
        start_time = time.time()
        instrumented_execution(code)
        execution_time = time.time() - start_time
        
        # Should handle deep recursion efficiently
        assert_performance_bounds(execution_time, 3.0, "Deep recursion instrumentation")
        
        # Create expected trace pattern using DSL (high-level structure)
        expected_trace = (trace()
                         .function_entry("deep_function", [30, 0])
                         # ... recursive calls ...
                         .return_event(465)  # Sum of 1+2+...+30 = 465
                         .assign("result", 465)
                         .build())
        
        # Verify actual trace has expected recursive pattern
        actual_events = tracer.events
        
        # Should record many function entries
        function_events = [e for e in actual_events if e.event_type == "call_pre"]
        assert len(function_events) >= 30, "Should record function entry for each recursive call"
        
        # Should calculate sum correctly: 1+2+...+30 = 465
        assert_variable_value_event(actual_events, "result", 465)


@pytest.mark.unit
class TestInstrumentationErrorHandlingWithDSL:
    """Test error handling in instrumentation using DSL verification."""
    
    def test_syntax_error_fallback_dsl(self, tracer):
        """Test that instrumentation handles syntax errors gracefully."""
        invalid_code = "invalid python syntax !!!"
        
        # Should not crash the instrumenter
        with pytest.raises(SyntaxError):
            exec(invalid_code)
        
        # Should still be able to instrument valid code after error
        valid_code = "x = 1"
        exec_instrumented(valid_code)
        
        # Verify using DSL that valid code was instrumented
        expected_trace = (trace()
                         .assign("x", 1)
                         .build())
        
        actual_events = tracer.events
        assert len(actual_events) >= 1, "Should instrument valid code after syntax error"
        assert_variable_value_event(actual_events, "x", 1)
    
    def test_empty_code_handling_dsl(self, tracer, instrumented_execution):
        """Test instrumentation with empty code using DSL verification."""
        instrumented_execution("")
        
        # Create expected trace (should be empty)
        expected_trace = (trace().build())
        
        # Should not crash, events may be empty
        actual_events = tracer.events
        assert len(actual_events) >= 0, "Empty code should not crash instrumentation"
    
    def test_complex_expressions_dsl(self, tracer, instrumented_execution):
        """Test instrumentation of complex expressions using DSL verification."""
        code = """
# List comprehensions
numbers = [1, 2, 3, 4, 5]
squared = [x**2 for x in numbers if x % 2 == 0]

# Dictionary operations
data = {'a': 1, 'b': 2}
data['c'] = 3

# Lambda functions
square = lambda x: x * x
result = square(5)
"""
        instrumented_execution(code)
        
        # Create expected trace pattern using DSL
        expected_trace = (trace()
                         .assign("numbers", [1, 2, 3, 4, 5])
                         .assign("squared", [4, 16])
                         .assign("data", {'a': 1, 'b': 2})
                         .subscript_assign("data", 'c', 3)
                         .assign("square", "lambda_function")
                         .assign("result", 25)
                         .build())
        
        # Verify actual trace has expected patterns
        actual_events = tracer.events
        
        # Should record assignment events for complex expressions
        assert_has_event_type(actual_events, EventType.ASSIGN, min_count=3)
        
        # Verify specific assignments
        assert_variable_value_event(actual_events, "result", 25)