# Python Whyline Test Suite

This directory contains comprehensive unit tests for the Python Whyline implementation using Python's unittest framework.

## Test Structure

### Core Test Modules

- **`test_core_tracing.py`** - Tests core tracing functionality
  - Event recording and retrieval
  - Event structure validation
  - Tracer statistics and operations
  - Variable history tracking

- **`test_ast_instrumentation.py`** - Tests AST instrumentation
  - Function instrumentation
  - Control flow (if/else, loops)
  - Class and method instrumentation
  - Recursive functions
  - Error handling

- **`test_question_system.py`** - Tests question/answer system
  - All question types (variable values, line execution, function returns)
  - Question formatting and caching
  - Answer accuracy and evidence
  - Edge cases with non-existent variables

- **`test_edge_cases.py`** - Tests edge cases and complex scenarios
  - Complex Python constructs (lambdas, generators, decorators)
  - Deep recursion handling
  - Variable scoping scenarios
  - Exception handling
  - Data structure operations
  - Import scenarios
  - Thread safety
  - Memory management

- **`test_cli_integration.py`** - Tests CLI functionality
  - CLI creation and initialization
  - Code loading and execution
  - Question creation through CLI
  - File loading and error handling
  - Command line interface testing

- **`test_performance.py`** - Tests performance characteristics
  - Execution performance
  - Memory usage
  - Question answering performance
  - Concurrent execution
  - Scaling characteristics

### Test Infrastructure

- **`test_runner.py`** - Main test runner with colored output
- **`conftest.py`** - Test configuration and utilities
- **`__init__.py`** - Test package initialization

## Running Tests

### Run All Tests
```bash
cd python_whyline/tests
python test_runner.py
```

### Run Specific Test Categories
```bash
# Core functionality only
python test_runner.py --category core

# Question system only
python test_runner.py --category questions

# CLI tests only
python test_runner.py --category cli

# Performance tests only
python test_runner.py --category performance

# Edge cases only
python test_runner.py --category edge_cases
```

### Run Specific Test Classes
```bash
# Run core tracing tests
python test_runner.py --specific core

# Run AST instrumentation tests
python test_runner.py --specific ast

# Run specific test method
python test_runner.py --specific core test_basic_event_recording
```

### Other Options
```bash
# Stop on first failure
python test_runner.py --failfast

# Increase verbosity
python test_runner.py --verbose

# Multiple categories
python test_runner.py --category core --category questions
```

### Run Individual Test Files
```bash
# Run specific test file
python test_core_tracing.py
python test_question_system.py
python -m unittest test_edge_cases.TestEdgeCases.test_deep_recursion
```

## Test Categories

### 📊 **Core Tests** (`core`)
- Basic tracing functionality
- AST instrumentation
- Event recording and structure

### ❓ **Question Tests** (`questions`)
- Question/answer system
- All question types
- Answer accuracy

### 🔀 **Edge Case Tests** (`edge_cases`)
- Complex Python constructs
- Error handling
- Memory management
- Thread safety

### 💻 **CLI Tests** (`cli`)
- Command line interface
- Interactive functionality
- File loading

### ⚡ **Performance Tests** (`performance`)
- Execution speed
- Memory usage
- Scalability

## Expected Results

### ✅ **Passing Tests**
All test categories should pass with 100% success rate:
- Core functionality: All basic operations work
- Question system: All question types answered correctly
- Edge cases: Complex scenarios handled properly
- CLI: Interactive interface functional
- Performance: Meets speed and memory requirements

### 📊 **Performance Benchmarks**
- Basic execution: < 2 seconds
- Large programs: < 5 seconds
- Deep recursion: < 3 seconds
- Question answering: < 0.1 seconds per question
- Memory usage: < 100MB increase for typical programs

### 🎯 **Success Criteria**
- All core tests pass (essential functionality)
- Question system accuracy 100% (main feature)
- Edge cases handled gracefully (robustness)
- CLI fully functional (usability)
- Performance within acceptable limits (efficiency)

## Test Output

The test runner provides colored output:
- ✅ Green for passing tests
- ❌ Red for failing tests
- ⚠️ Yellow for skipped tests

Example output:
```
🧪 PYTHON WHYLINE TEST SUITE
==================================================
Running 45 tests...

✅ test_core_tracing.TestCoreTracing.test_basic_event_recording ... ok
✅ test_core_tracing.TestCoreTracing.test_event_structure ... ok
...

==================================================
📊 TEST SUMMARY
==================================================
Total tests run: 45
✅ Successes: 45
❌ Failures: 0
❌ Errors: 0
⚠️ Skipped: 0
⏱️ Execution time: 12.34s
📈 Success rate: 100.0%

==================================================
🎉 ALL TESTS PASSED!
✅ Python Whyline implementation is working correctly
==================================================
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure you're running from the correct directory
   - Check that parent directories are in Python path

2. **Missing Dependencies**
   - Performance tests require `psutil`: `pip install psutil`
   - Some tests may be skipped if dependencies unavailable

3. **Timeout Issues**
   - Performance tests have timeouts for slow systems
   - Adjust timeout values in `conftest.py` if needed

4. **CLI Tests Failing**
   - Ensure CLI scripts are in correct location
   - Check file permissions for CLI execution

### Debug Mode
```bash
# Run with maximum verbosity
python test_runner.py --verbose --verbose

# Run single test for debugging
python test_runner.py --specific core test_basic_event_recording

# Stop on first failure for quick debugging
python test_runner.py --failfast
```

## Contributing

When adding new tests:

1. **Follow naming conventions**: `test_*.py` for files, `test_*` for methods
2. **Use appropriate test categories**: Add to existing modules or create new ones
3. **Include performance considerations**: Add timing assertions for new features
4. **Add to test runner**: Update categories in `test_runner.py` if needed
5. **Document expected behavior**: Clear assertions with meaningful messages

## Test Coverage

The test suite covers:
- ✅ All core functionality (tracing, instrumentation, questions)
- ✅ All question types and edge cases
- ✅ CLI interface and user interactions
- ✅ Performance and scalability
- ✅ Error handling and robustness
- ✅ Complex Python language features
- ✅ Memory management and threading

This ensures the Python Whyline implementation is thoroughly validated and ready for production use.