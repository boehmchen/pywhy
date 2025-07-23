# Pywhy Test Suite

This directory contains comprehensive tests for the Pywhy implementation using pytest.

## Test Structure

### Core Test Modules

- **`test_instrumentation.py`** - Tests AST instrumentation functionality
  - Basic assignments, functions, control flow, loops
  - Advanced constructs: classes, nested functions, recursion
  - Data structure operations and exception handling
  - Complex algorithms and performance testing

- **`test_trace_dsl.py`** - Tests the tracing DSL functionality
  - TraceEventBuilder fluent API testing
  - TraceSequence high-level pattern testing
  - EventMatcher utility testing
  - JSON serialization and event validation

### Test Infrastructure

- **`conftest.py`** - Pytest configuration and fixtures
  - Shared test fixtures (tracer, builders, temp files)
  - Helper assertion functions
  - Sample code snippets for testing
  - Parametrized fixtures for comprehensive testing

- **`__init__.py`** - Test package initialization

## Running Tests

### Prerequisites
```bash
pip install pytest
```

### Run All Tests
```bash
cd pywhy/tests
pytest
```

### Run Specific Test Categories
```bash
# DSL functionality tests
pytest -m dsl

# Unit tests
pytest -m unit

# Integration tests  
pytest -m integration

# Performance tests
pytest -m performance

# CLI tests (if available)
pytest -m cli
```

### Run Specific Test Files
```bash
# Run instrumentation tests
pytest test_instrumentation.py

# Run DSL tests
pytest test_trace_dsl.py

# Run specific test class
pytest test_instrumentation.py::TestBasicInstrumentation

# Run specific test method
pytest test_instrumentation.py::TestBasicInstrumentation::test_simple_assignment_instrumentation
```

### Useful Pytest Options
```bash
# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Show local variables in traceback
pytest -l

# Run in parallel (requires pytest-xdist)
pytest -n auto

# Generate coverage report (requires pytest-cov)
pytest --cov=pywhy
```

## Test Categories (Pytest Markers)

### 🧪 **Unit Tests** (`@pytest.mark.unit`)
- Individual component testing
- Basic functionality validation
- Isolated feature testing

### 🔗 **Integration Tests** (`@pytest.mark.integration`)
- Component interaction testing
- End-to-end workflow validation
- Cross-module functionality

### 📝 **DSL Tests** (`@pytest.mark.dsl`)
- Domain Specific Language testing
- TraceEventBuilder and TraceSequence
- Event matching and validation

### ⚡ **Performance Tests** (`@pytest.mark.performance`)
- Execution speed validation
- Memory usage testing
- Scalability assessment

### 🐌 **Slow Tests** (`@pytest.mark.slow`)
- Tests that take significant time
- Can be skipped for quick runs: `pytest -m "not slow"`

## Test Features

### 🎯 **Parametrized Testing**
Tests use `@pytest.mark.parametrize` for comprehensive coverage:
```python
@pytest.mark.parametrize("condition,result", [
    ("x > 0", True),
    ("y < 10", False),
    ("z == 0", True)
])
def test_condition_events_parametrized(self, trace_builder, condition, result):
    # Test with multiple parameter combinations
```

### 🏗️ **Fixture-Based Architecture**
All tests use pytest fixtures for clean setup/teardown:
- `tracer`: Clean tracer instance
- `trace_builder`: Fresh TraceEventBuilder
- `trace_sequence`: Fresh TraceSequence
- `instrumented_execution`: Execute code with instrumentation
- `temp_file`/`temp_dir`: Temporary files with automatic cleanup

### 🔍 **DSL-Powered Assertions**
Custom assertion helpers using the DSL:
```python
assert_has_event_type(events, EventType.ASSIGN, min_count=3)
assert_variable_value_event(events, "x", 10)
assert_function_called(events, "my_func", [1, 2, 3])
assert_performance_bounds(execution_time, 2.0, "Operation")
```

### 📊 **Sample Code Testing**
Parametrized fixture tests all sample codes automatically:
```python
def test_all_sample_codes_instrument_successfully(self, sample_code_execution):
    execution = sample_code_execution
    assert len(execution['events']) > 0
    # Automatically tests: simple_assignment, function_call, control_flow, 
    # loop, recursion, class_usage, exception_handling, complex_program
```

## Expected Results

### ✅ **Success Criteria**
- All unit tests pass (basic functionality)
- DSL tests validate event creation and matching
- Integration tests confirm end-to-end workflows
- Performance tests meet timing requirements

### 📊 **Performance Benchmarks**
- Simple instrumentation: < 1 second
- Complex algorithms: < 5 seconds  
- Deep recursion (50 levels): < 3 seconds
- Event processing: > 1000 events/second

### 🎯 **Coverage Goals**
- All core instrumentation functionality
- Complete DSL API coverage
- Error handling and edge cases
- Performance characteristics validation

## Sample Test Output

```bash
$ pytest -v
========================= test session starts =========================
platform darwin -- Python 3.11.0
collected 45 items

test_instrumentation.py::TestBasicInstrumentation::test_simple_assignment_instrumentation PASSED [4%]
test_instrumentation.py::TestBasicInstrumentation::test_function_definition_and_call PASSED [8%]
test_trace_dsl.py::TestTraceEventBuilder::test_basic_assignment_creation PASSED [12%]
test_trace_dsl.py::TestTraceEventBuilder::test_function_events_creation PASSED [16%]
...
test_instrumentation.py::TestInstrumentationPerformance::test_deep_recursion_performance PASSED [100%]

========================= 45 passed in 12.34s =========================
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure you're in the right directory
   cd pywhy/tests
   # Or add to PYTHONPATH
   export PYTHONPATH=$PYTHONPATH:$(pwd)/../..
   ```

2. **Missing Modules**
   ```bash
   # Install missing dependencies
   pip install pytest pytest-cov pytest-xdist
   ```

3. **Slow Tests**
   ```bash
   # Skip slow tests for quick runs
   pytest -m "not slow"
   # Or run only fast tests
   pytest -m "unit and not slow"
   ```

### Debug Mode
```bash
# Maximum verbosity with locals
pytest -vvv -l

# Drop into debugger on failure
pytest --pdb

# Run specific failing test
pytest test_instrumentation.py::TestBasicInstrumentation::test_simple_assignment_instrumentation -vvv
```

## Contributing

### Adding New Tests

1. **Follow pytest conventions**:
   - File names: `test_*.py`
   - Function names: `test_*`
   - Class names: `Test*`

2. **Use appropriate markers**:
   ```python
   @pytest.mark.unit
   @pytest.mark.dsl
   @pytest.mark.performance
   ```

3. **Leverage fixtures**:
   ```python
   def test_my_feature(self, tracer, instrumented_execution):
       # Use provided fixtures
   ```

4. **Use DSL assertions**:
   ```python
   from conftest import assert_has_event_type
   assert_has_event_type(events, EventType.ASSIGN, min_count=1)
   ```

5. **Add parametrized tests** for multiple scenarios:
   ```python
   @pytest.mark.parametrize("input,expected", [
       (1, 1), (2, 4), (3, 9)
   ])
   def test_square(self, input, expected):
       assert square(input) == expected
   ```

### Test Organization

- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test component interactions
- **Performance tests**: Validate timing and resource usage
- **DSL tests**: Validate the tracing domain-specific language

## Test Coverage

The test suite provides comprehensive coverage of:

- ✅ **Core Instrumentation**: All AST transformation functionality
- ✅ **DSL API**: Complete TraceEventBuilder and TraceSequence APIs
- ✅ **Event System**: Event creation, matching, and validation
- ✅ **Performance**: Timing bounds and resource usage
- ✅ **Error Handling**: Graceful failure and recovery
- ✅ **Complex Scenarios**: Real-world Python code patterns
- ✅ **Integration**: End-to-end workflow validation

This ensures the Pywhy implementation is thoroughly tested and production-ready.