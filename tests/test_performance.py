"""
Performance tests for Python Whyline
"""

import unittest
import sys
import os
import time
import gc

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from python_whyline import get_tracer, exec_instrumented, QuestionAsker


class TestPerformance(unittest.TestCase):
    """Test performance characteristics"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tracer = get_tracer()
        self.tracer.clear()
        gc.collect()  # Start with clean memory
    
    def tearDown(self):
        """Clean up after each test"""
        self.tracer.clear()
        gc.collect()
    
    def test_basic_execution_performance(self):
        """Test basic execution performance"""
        code = '''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(10)
'''
        
        start_time = time.time()
        exec_instrumented(code)
        execution_time = time.time() - start_time
        
        # Should complete in reasonable time (less than 2 seconds)
        self.assertLess(execution_time, 2.0, 
                       f"Basic execution took {execution_time:.3f}s, expected < 2.0s")
        
        # Should record reasonable number of events
        event_count = len(self.tracer.events)
        self.assertGreater(event_count, 100, "Should record substantial events for recursion")
        
        # Calculate events per second
        events_per_second = event_count / execution_time if execution_time > 0 else float('inf')
        self.assertGreater(events_per_second, 1000, 
                          f"Performance: {events_per_second:.0f} events/s, expected > 1000")
    
    def test_large_program_performance(self):
        """Test performance with larger programs"""
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

# Test with larger array
data = list(range(50, 0, -1))  # Reverse sorted for worst case
sorted_data = merge_sort(data)
'''
        
        start_time = time.time()
        exec_instrumented(code)
        execution_time = time.time() - start_time
        
        # Should complete in reasonable time (less than 5 seconds)
        self.assertLess(execution_time, 5.0, 
                       f"Large program took {execution_time:.3f}s, expected < 5.0s")
        
        # Should record many events
        event_count = len(self.tracer.events)
        self.assertGreater(event_count, 1000, "Large program should record many events")
    
    def test_deep_recursion_performance(self):
        """Test performance with deep recursion"""
        code = '''
def deep_function(n, acc=0):
    if n <= 0:
        return acc
    return deep_function(n - 1, acc + n)

result = deep_function(100)
'''
        
        start_time = time.time()
        exec_instrumented(code)
        execution_time = time.time() - start_time
        
        # Should handle deep recursion efficiently
        self.assertLess(execution_time, 3.0, 
                       f"Deep recursion took {execution_time:.3f}s, expected < 3.0s")
        
        # Should record many function entry events
        function_events = [e for e in self.tracer.events if e.event_type == 'function_entry']
        self.assertGreater(len(function_events), 100, "Should record many function entries")
    
    @unittest.skipIf(not HAS_PSUTIL, "psutil not available")
    def test_memory_usage(self):
        """Test memory usage characteristics"""
        process = psutil.Process(os.getpid())
        
        # Get initial memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Execute code that generates many events
        code = '''
total = 0
for i in range(1000):
    for j in range(10):
        temp = i * j
        total += temp
        if temp % 100 == 0:
            result = temp
'''
        
        exec_instrumented(code)
        
        # Get memory usage after execution
        after_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = after_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for this test)
        self.assertLess(memory_increase, 100, 
                       f"Memory increased by {memory_increase:.1f}MB, expected < 100MB")
        
        # Clear events and check memory is freed
        event_count = len(self.tracer.events)
        self.assertGreater(event_count, 1000, "Should have generated many events")
        
        self.tracer.clear()
        gc.collect()
        
        cleared_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_freed = after_memory - cleared_memory
        
        # Should free some memory after clearing (at least 10% of what was allocated)
        self.assertGreater(memory_freed, memory_increase * 0.1, 
                          f"Should free memory after clear, freed {memory_freed:.1f}MB")
    
    def test_question_performance(self):
        """Test question answering performance"""
        # Execute code first
        code = '''
def calculate_factorial(n):
    if n <= 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result

values = []
for i in range(1, 11):
    factorial_value = calculate_factorial(i)
    values.append(factorial_value)

final_sum = sum(values)
'''
        
        exec_instrumented(code)
        asker = QuestionAsker(self.tracer)
        
        # Test question answering performance
        questions = [
            lambda: asker.why_did_variable_have_value('final_sum', sum([1, 1, 2, 6, 24, 120, 720, 5040, 40320, 362880])),
            lambda: asker.why_did_line_execute('<string>', 5),
            lambda: asker.why_didnt_line_execute('<string>', 999),
            lambda: asker.why_did_function_return('calculate_factorial', 120)
        ]
        
        total_question_time = 0
        for question_func in questions:
            start_time = time.time()
            question = question_func()
            answer = question.get_answer()
            question_time = time.time() - start_time
            total_question_time += question_time
            
            # Each question should be answered quickly (< 0.1 seconds)
            self.assertLess(question_time, 0.1, 
                           f"Question took {question_time:.3f}s, expected < 0.1s")
            self.assertIsNotNone(answer, "Question should have an answer")
        
        # All questions together should be fast
        self.assertLess(total_question_time, 0.5, 
                       f"All questions took {total_question_time:.3f}s, expected < 0.5s")
    
    def test_concurrent_execution_performance(self):
        """Test performance with concurrent execution"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def worker():
            tracer = get_tracer()
            tracer.clear()
            
            code = '''
def worker_function(n):
    total = 0
    for i in range(n):
        total += i * i
    return total

result = worker_function(100)
'''
            
            start_time = time.time()
            exec_instrumented(code)
            execution_time = time.time() - start_time
            
            results.put((len(tracer.events), execution_time))
        
        # Run multiple workers concurrently
        threads = []
        for _ in range(3):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join(timeout=5.0)
            self.assertFalse(t.is_alive(), "Thread should complete within timeout")
        
        # Check results
        total_events = 0
        total_time = 0
        result_count = 0
        
        while not results.empty():
            events, time_taken = results.get()
            total_events += events
            total_time += time_taken
            result_count += 1
            
            # Each worker should complete quickly
            self.assertLess(time_taken, 2.0, f"Worker took {time_taken:.3f}s, expected < 2.0s")
            self.assertGreater(events, 0, "Worker should record events")
        
        self.assertEqual(result_count, 3, "All workers should complete")
        
        # Average performance should be reasonable
        avg_time = total_time / result_count
        self.assertLess(avg_time, 1.0, f"Average time {avg_time:.3f}s, expected < 1.0s")
    
    def test_scaling_characteristics(self):
        """Test how performance scales with program size"""
        base_code = '''
def process_data(data):
    result = 0
    for item in data:
        if item > 0:
            result += item * 2
        else:
            result -= item
    return result
'''
        
        # Test with different data sizes
        sizes = [10, 50, 100]
        times = []
        event_counts = []
        
        for size in sizes:
            self.tracer.clear()
            
            code = base_code + f'''
data = list(range(-{size//2}, {size//2}))
result = process_data(data)
'''
            
            start_time = time.time()
            exec_instrumented(code)
            execution_time = time.time() - start_time
            
            times.append(execution_time)
            event_counts.append(len(self.tracer.events))
        
        # Performance should scale reasonably (not exponentially)
        for i in range(1, len(times)):
            scaling_factor = times[i] / times[i-1]
            size_factor = sizes[i] / sizes[i-1]
            
            # Time scaling should be roughly linear with size (factor < 10)
            self.assertLess(scaling_factor, size_factor * 2, 
                           f"Performance scaling too poor: {scaling_factor:.1f}x time for {size_factor:.1f}x size")
        
        # Event count should scale with program size
        for i in range(1, len(event_counts)):
            event_scaling = event_counts[i] / event_counts[i-1]
            self.assertGreater(event_scaling, 1.5, "Event count should scale with program size")


if __name__ == '__main__':
    # Skip if psutil not available
    try:
        import psutil
        unittest.main()
    except ImportError:
        print("Skipping performance tests - psutil not available")
        sys.exit(0)