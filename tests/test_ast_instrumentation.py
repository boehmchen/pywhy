"""
Unit tests for AST instrumentation functionality
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from python_whyline import get_tracer, exec_instrumented


class TestASTInstrumentation(unittest.TestCase):
    """Test AST instrumentation with various Python constructs"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tracer = get_tracer()
        self.tracer.clear()
    
    def test_function_instrumentation(self):
        """Test function definition and call instrumentation"""
        code = '''
def simple_func(x):
    return x * 2

result = simple_func(5)
'''
        exec_instrumented(code)
        
        # Check for function entry events
        function_events = [e for e in self.tracer.events if e.event_type == 'function_entry']
        self.assertGreater(len(function_events), 0, "No function entry events recorded")
        
        # Check for return events
        return_events = [e for e in self.tracer.events if e.event_type == 'return']
        self.assertGreater(len(return_events), 0, "No return events recorded")
    
    def test_control_flow_instrumentation(self):
        """Test if/else statement instrumentation"""
        code = '''
x = 10
if x > 5:
    result = "large"
else:
    result = "small"
'''
        exec_instrumented(code)
        
        # Check for branch events
        branch_events = [e for e in self.tracer.events if e.event_type == 'branch']
        self.assertGreater(len(branch_events), 0, "No branch events recorded")
    
    def test_loop_instrumentation(self):
        """Test loop instrumentation"""
        code = '''
total = 0
for i in range(3):
    total += i
'''
        exec_instrumented(code)
        
        # Check for loop iteration events
        loop_events = [e for e in self.tracer.events if e.event_type == 'loop_iteration']
        self.assertGreater(len(loop_events), 0, "No loop iteration events recorded")
    
    def test_class_instrumentation(self):
        """Test class and method instrumentation"""
        code = '''
class Calculator:
    def __init__(self, value=0):
        self.value = value
    
    def add(self, x):
        self.value += x
        return self.value

calc = Calculator(10)
result = calc.add(5)
'''
        exec_instrumented(code)
        
        # Should record assignment and function entry events
        assign_events = [e for e in self.tracer.events if e.event_type == 'assign']
        function_events = [e for e in self.tracer.events if e.event_type == 'function_entry']
        
        self.assertGreater(len(assign_events), 0, "No assignment events for class")
        self.assertGreater(len(function_events), 0, "No function entry events for methods")
    
    def test_nested_functions(self):
        """Test nested function instrumentation"""
        code = '''
def outer_func(n):
    def inner_func(x):
        return x * 2
    result = inner_func(n)
    return result

output = outer_func(8)
'''
        exec_instrumented(code)
        
        # Check for multiple function entries
        function_events = [e for e in self.tracer.events if e.event_type == 'function_entry']
        self.assertGreaterEqual(len(function_events), 2, "Expected at least 2 function entries for nested functions")
    
    def test_exception_handling_instrumentation(self):
        """Test try/except block instrumentation"""
        code = '''
def safe_divide(a, b):
    try:
        result = a / b
        return result
    except ZeroDivisionError:
        return 0

result1 = safe_divide(10, 2)
result2 = safe_divide(10, 0)
'''
        exec_instrumented(code)
        
        # Should record function entries and assignments
        function_events = [e for e in self.tracer.events if e.event_type == 'function_entry']
        assign_events = [e for e in self.tracer.events if e.event_type == 'assign']
        
        self.assertGreater(len(function_events), 0, "No function events in exception handling")
        self.assertGreater(len(assign_events), 0, "No assignment events in exception handling")
    
    def test_complex_expressions(self):
        """Test complex expression instrumentation"""
        code = '''
# List comprehensions
numbers = [1, 2, 3, 4, 5]
squared = [x**2 for x in numbers if x % 2 == 0]

# Dictionary operations
data = {'a': 1, 'b': 2}
data['c'] = 3

# Lambda functions
square = lambda x: x * x
result = square(5)
'''
        exec_instrumented(code)
        
        # Should record assignment events for complex expressions
        assign_events = [e for e in self.tracer.events if e.event_type == 'assign']
        self.assertGreater(len(assign_events), 0, "No assignment events for complex expressions")
    
    def test_recursive_functions(self):
        """Test recursive function instrumentation"""
        code = '''
def factorial(n):
    if n <= 1:
        return 1
    else:
        return n * factorial(n - 1)

result = factorial(4)
'''
        exec_instrumented(code)
        
        # Should record multiple function entries for recursion
        function_events = [e for e in self.tracer.events if e.event_type == 'function_entry']
        self.assertGreater(len(function_events), 4, "Expected multiple function entries for recursion")
        
        # Should record multiple return events
        return_events = [e for e in self.tracer.events if e.event_type == 'return']
        self.assertGreater(len(return_events), 4, "Expected multiple return events for recursion")
    
    def test_instrumentation_error_handling(self):
        """Test that instrumentation handles invalid code gracefully"""
        # This should not crash, but fall back to original execution
        invalid_code = "invalid python syntax !!!"
        
        try:
            exec_instrumented(invalid_code)
        except:
            pass  # Expected to fail, but shouldn't crash the instrumenter
        
        # Should still be able to instrument valid code after error
        valid_code = "x = 1"
        exec_instrumented(valid_code)
        
        assign_events = [e for e in self.tracer.events if e.event_type == 'assign']
        self.assertGreater(len(assign_events), 0, "Cannot instrument after error")


if __name__ == '__main__':
    unittest.main()