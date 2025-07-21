"""
Unit tests for edge cases and complex scenarios
"""

import unittest
import sys
import os
import threading
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from python_whyline import get_tracer, exec_instrumented, QuestionAsker


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and complex scenarios"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tracer = get_tracer()
        self.tracer.clear()
    
    def test_empty_code(self):
        """Test instrumentation with empty code"""
        exec_instrumented("")
        # Should not crash, events may be empty
        self.assertGreaterEqual(len(self.tracer.events), 0, "Empty code should not crash")
    
    def test_syntax_error_fallback(self):
        """Test fallback behavior with syntax errors"""
        # Should fall back to original execution (which will fail)
        with self.assertRaises(SyntaxError):
            exec("invalid python syntax !!!")
        
        # Should still be able to instrument valid code after error
        exec_instrumented("x = 1")
        assign_events = [e for e in self.tracer.events if e.event_type == 'assign']
        self.assertGreater(len(assign_events), 0, "Should work after syntax error")
    
    def test_complex_python_constructs(self):
        """Test complex Python language constructs"""
        code = '''
# Lambda functions
square = lambda x: x * x
result1 = square(5)

# Generators
def fibonacci_gen(n):
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b

fib_list = list(fibonacci_gen(5))

# Decorators
def my_decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs) * 2
    return wrapper

@my_decorator
def multiply(x, y):
    return x * y

decorated_result = multiply(3, 4)

# Context managers
class MyContext:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

with MyContext() as ctx:
    context_var = 42
'''
        
        exec_instrumented(code)
        
        # Should record various events
        self.assertGreater(len(self.tracer.events), 5, "Complex constructs should generate events")
        
        # Should be able to ask questions
        asker = QuestionAsker(self.tracer)
        question = asker.why_did_variable_have_value('result1', 25)
        answer = question.get_answer()
        self.assertIsNotNone(answer, "Should answer questions about complex constructs")
    
    def test_deep_recursion(self):
        """Test deep recursion handling"""
        code = '''
def deep_recursive(n, depth=0):
    if n <= 0:
        return depth
    else:
        return deep_recursive(n - 1, depth + 1)

result = deep_recursive(20)
'''
        
        exec_instrumented(code)
        
        # Should handle deep recursion without crashing
        self.assertGreater(len(self.tracer.events), 20, "Deep recursion should generate many events")
        
        # Should be able to ask questions
        asker = QuestionAsker(self.tracer)
        question = asker.why_did_variable_have_value('result', 20)
        answer = question.get_answer()
        self.assertIsNotNone(answer, "Should answer questions about recursive results")
    
    def test_variable_scoping(self):
        """Test variable scoping scenarios"""
        code = '''
global_var = 10

def outer_function():
    outer_var = 20
    
    def inner_function():
        nonlocal outer_var
        outer_var = 30
        local_var = 40
        return local_var + outer_var
    
    inner_result = inner_function()
    return inner_result + global_var

final_result = outer_function()
'''
        
        exec_instrumented(code)
        
        # Should handle scoping correctly
        self.assertGreater(len(self.tracer.events), 5, "Scoping should generate events")
        
        # Should be able to ask questions about scoped variables
        asker = QuestionAsker(self.tracer)
        question = asker.why_did_variable_have_value('final_result', 80)
        answer = question.get_answer()
        self.assertIsNotNone(answer, "Should answer questions about scoped variables")
    
    def test_exception_handling_scenarios(self):
        """Test exception handling scenarios"""
        code = '''
def risky_function(x):
    if x == 0:
        raise ValueError("Cannot be zero")
    return 10 / x

results = []
for i in range(-2, 3):
    try:
        result = risky_function(i)
        results.append(result)
    except ValueError as e:
        results.append(str(e))
    except ZeroDivisionError:
        results.append("Division by zero")

final_count = len(results)
'''
        
        exec_instrumented(code)
        
        # Should handle exceptions without crashing
        self.assertGreater(len(self.tracer.events), 5, "Exception handling should generate events")
        
        # Should be able to ask questions
        asker = QuestionAsker(self.tracer)
        question = asker.why_did_variable_have_value('final_count', 5)
        answer = question.get_answer()
        self.assertIsNotNone(answer, "Should answer questions about exception handling")
    
    def test_data_structure_operations(self):
        """Test various data structure operations"""
        code = '''
# Lists
my_list = [1, 2, 3]
my_list.append(4)
my_list[0] = 10

# Dictionaries
my_dict = {'a': 1, 'b': 2}
my_dict['c'] = 3
my_dict.update({'d': 4})

# Sets
my_set = {1, 2, 3}
my_set.add(4)
my_set.discard(1)

# Tuples
my_tuple = (1, 2, 3)
tuple_sum = sum(my_tuple)

# List comprehensions
squared = [x**2 for x in [1, 2, 3] if x % 2 == 1]
'''
        
        exec_instrumented(code)
        
        # Should handle data structures
        self.assertGreater(len(self.tracer.events), 5, "Data structures should generate events")
        
        # Should be able to ask questions
        asker = QuestionAsker(self.tracer)
        question = asker.why_did_variable_have_value('tuple_sum', 6)
        answer = question.get_answer()
        self.assertIsNotNone(answer, "Should answer questions about data structures")
    
    def test_import_scenarios(self):
        """Test import scenarios"""
        code = '''
import math
import os.path as path
from datetime import datetime
from collections import defaultdict

# Using imported modules
pi_value = math.pi
current_time = datetime.now()
file_exists = path.exists("nonexistent_file.txt")

# Using collections
dd = defaultdict(int)
dd['key1'] += 1
dd['key2'] += 2
'''
        
        exec_instrumented(code)
        
        # Should handle imports
        self.assertGreater(len(self.tracer.events), 3, "Import scenarios should generate events")
        
        # Should be able to ask questions
        asker = QuestionAsker(self.tracer)
        question = asker.why_did_variable_have_value('file_exists', False)
        answer = question.get_answer()
        self.assertIsNotNone(answer, "Should answer questions about imported functionality")
    
    def test_thread_safety(self):
        """Test thread safety of tracer"""
        self.tracer.clear()
        
        def threaded_execution():
            exec_instrumented("import threading; thread_var = threading.current_thread().name")
        
        threads = []
        for i in range(3):
            t = threading.Thread(target=threaded_execution)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should handle concurrent execution
        self.assertGreater(len(self.tracer.events), 0, "Thread safety should allow concurrent execution")
    
    def test_large_program_handling(self):
        """Test handling of larger programs"""
        code = '''
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

# Test with array
data = [64, 34, 25, 12, 22, 11, 90]
sorted_data = merge_sort(data)
'''
        
        start_time = time.time()
        exec_instrumented(code)
        execution_time = time.time() - start_time
        
        # Should handle larger programs efficiently
        self.assertGreater(len(self.tracer.events), 50, "Large program should generate many events")
        self.assertLess(execution_time, 10.0, "Large program should execute in reasonable time")
    
    def test_memory_management(self):
        """Test memory management with many events"""
        code = '''
total = 0
for i in range(100):
    total += i
    temp = total * 2
    if temp > 1000:
        break
'''
        
        exec_instrumented(code)
        
        # Should handle many events without memory issues
        self.assertGreater(len(self.tracer.events), 50, "Should generate many events")
        
        # Clear should free memory
        initial_count = len(self.tracer.events)
        self.tracer.clear()
        self.assertEqual(len(self.tracer.events), 0, "Clear should free all events")


if __name__ == '__main__':
    unittest.main()