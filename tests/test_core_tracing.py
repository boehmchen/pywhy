"""
Unit tests for core tracing functionality
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from python_whyline import get_tracer, exec_instrumented


class TestCoreTracing(unittest.TestCase):
    """Test core tracing functionality"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tracer = get_tracer()
        self.tracer.clear()
    
    def test_basic_event_recording(self):
        """Test that basic events are recorded"""
        code = '''
x = 10
y = 20
z = x + y
'''
        exec_instrumented(code)
        
        # Check if events were recorded
        self.assertGreater(len(self.tracer.events), 0, "No events recorded")
        
        # Check for assignment events
        assign_events = [e for e in self.tracer.events if e.event_type == 'assign']
        self.assertGreaterEqual(len(assign_events), 3, f"Expected 3+ assignments, got {len(assign_events)}")
    
    def test_event_structure(self):
        """Test that events have the correct structure"""
        code = 'x = 42'
        exec_instrumented(code)
        
        self.assertGreater(len(self.tracer.events), 0, "No events recorded")
        
        event = self.tracer.events[0]
        
        # Check required fields
        required_fields = ['event_id', 'filename', 'lineno', 'event_type', 'timestamp', 'args']
        for field in required_fields:
            self.assertTrue(hasattr(event, field), f"Event missing field: {field}")
    
    def test_event_types(self):
        """Test that different event types are recorded"""
        code = '''
def test_func():
    x = 1
    return x

result = test_func()
'''
        exec_instrumented(code)
        
        event_types = set(e.event_type for e in self.tracer.events)
        expected_types = {'assign', 'function_entry', 'return'}
        
        for expected_type in expected_types:
            self.assertIn(expected_type, event_types, f"Missing event type: {expected_type}")
    
    def test_tracer_clear(self):
        """Test that tracer.clear() works correctly"""
        code = 'x = 1'
        exec_instrumented(code)
        
        self.assertGreater(len(self.tracer.events), 0, "No events recorded initially")
        
        self.tracer.clear()
        self.assertEqual(len(self.tracer.events), 0, "Events not cleared")
    
    def test_tracer_stats(self):
        """Test tracer statistics"""
        code = '''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(3)
'''
        exec_instrumented(code)
        
        stats = self.tracer.get_stats()
        
        # Check stats structure
        required_keys = ['total_events', 'event_types', 'files_traced', 'time_span']
        for key in required_keys:
            self.assertIn(key, stats, f"Missing stats key: {key}")
        
        # Check stats values
        self.assertGreater(stats['total_events'], 0, "No events in stats")
        self.assertGreater(stats['files_traced'], 0, "No files traced")
        self.assertGreaterEqual(stats['time_span'], 0, "Negative time span")
    
    def test_variable_history(self):
        """Test variable history tracking"""
        code = '''
x = 1
x = 2
x = 3
'''
        exec_instrumented(code)
        
        history = self.tracer.get_variable_history('x')
        self.assertGreaterEqual(len(history), 3, "Not all variable assignments tracked")
    
    def test_line_executions(self):
        """Test line execution tracking"""
        code = '''
x = 1  # line 2
y = 2  # line 3
'''
        exec_instrumented(code)
        
        line_events = self.tracer.get_line_executions('<string>', 2)
        self.assertGreater(len(line_events), 0, "No events found for line 2")


if __name__ == '__main__':
    unittest.main()