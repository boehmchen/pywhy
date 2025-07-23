"""
Test configuration and fixtures for Python Whyline tests
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Global test configuration
TEST_TIMEOUT = 30  # seconds
MAX_EVENTS_FOR_SMALL_TEST = 100
MAX_EVENTS_FOR_LARGE_TEST = 10000
MAX_EXECUTION_TIME = 5.0  # seconds

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / 'data'

# Create test data directory if it doesn't exist
TEST_DATA_DIR.mkdir(exist_ok=True)

# Common test code snippets
COMMON_TEST_CODES = {
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

def create_temp_file(content, suffix='.py'):
    """Create a temporary file with given content"""
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        return path
    except:
        os.close(fd)
        raise

def cleanup_temp_file(path):
    """Clean up temporary file"""
    try:
        os.unlink(path)
    except (OSError, FileNotFoundError):
        pass

class TestEnvironment:
    """Test environment manager"""
    
    def __init__(self):
        self.temp_files = []
        self.temp_dirs = []
    
    def create_temp_file(self, content, suffix='.py'):
        """Create temporary file and track for cleanup"""
        path = create_temp_file(content, suffix)
        self.temp_files.append(path)
        return path
    
    def create_temp_dir(self):
        """Create temporary directory and track for cleanup"""
        path = tempfile.mkdtemp()
        self.temp_dirs.append(path)
        return path
    
    def cleanup(self):
        """Clean up all temporary files and directories"""
        for path in self.temp_files:
            cleanup_temp_file(path)
        
        for path in self.temp_dirs:
            try:
                shutil.rmtree(path)
            except (OSError, FileNotFoundError):
                pass
        
        self.temp_files.clear()
        self.temp_dirs.clear()

# Global test environment
test_env = TestEnvironment()

@pytest.fixture
def test_environment():
    """Pytest fixture for test environment"""
    env = TestEnvironment()
    yield env
    env.cleanup()

@pytest.fixture
def test_codes():
    """Pytest fixture for common test codes"""
    return COMMON_TEST_CODES

def get_test_code(name):
    """Get common test code by name"""
    return COMMON_TEST_CODES.get(name, '')

def create_test_file(name, content=None):
    """Create a test file with given content"""
    if content is None:
        content = get_test_code(name)
    
    return test_env.create_temp_file(content)

def skip_if_no_module(module_name):
    """Skip test if module is not available"""
    import unittest
    
    try:
        __import__(module_name)
        return lambda func: func
    except ImportError:
        return unittest.skip(f"Module {module_name} not available")

# Test utilities
def measure_execution_time(func):
    """Decorator to measure execution time"""
    import time
    
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        return result, end - start
    
    return wrapper

def get_memory_usage():
    """Get current memory usage in MB"""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        return 0

def assert_performance(execution_time, max_time, operation_name):
    """Assert performance is within acceptable limits"""
    if execution_time > max_time:
        raise AssertionError(f"{operation_name} took {execution_time:.3f}s, expected < {max_time:.3f}s")

def assert_event_count(events, min_count, max_count, operation_name):
    """Assert event count is within expected range"""
    actual_count = len(events)
    if actual_count < min_count:
        raise AssertionError(f"{operation_name} recorded {actual_count} events, expected >= {min_count}")
    if actual_count > max_count:
        raise AssertionError(f"{operation_name} recorded {actual_count} events, expected <= {max_count}")

def cleanup_test_environment():
    """Clean up test environment"""
    test_env.cleanup()

# Register cleanup function
import atexit
atexit.register(cleanup_test_environment)