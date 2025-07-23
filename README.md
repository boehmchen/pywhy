# PyWhy - Whyline for Python

A Python implementation of the Whyline debugging tool that helps developers understand program execution by answering "why" questions about their code.

## Installation

```bash
poetry install
```

## Usage

```python
from pywhy import instrument_code, exec_instrumented

# Your Python code
code = """
def add(a, b):
    return a + b

result = add(5, 3)
"""

# Instrument and execute
globals_dict = exec_instrumented(code)
tracer = globals_dict["_whyline_tracer"]

# Analyze execution
for event in tracer.events:
    print(event)
```

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=pywhy

# Run specific test category
poetry run pytest -m unit
```