"""
Python Whyline - A debugging tool for asking "why" questions about Python program execution.

This package provides:
- Tracer: Records execution events
- Instrumenter: Transforms code to add tracing
- Questions: Ask why/why not questions about execution
- UI: Simple interface for interactive debugging
"""

from .tracer import WhylineTracer, get_tracer, start_tracing, stop_tracing
from .instrumenter import instrument_code, instrument_file, exec_instrumented
from .questions import QuestionAsker, Question, Answer

# Import UI components conditionally
try:
    from .ui import WhylineUI
    UI_AVAILABLE = True
except ImportError:
    UI_AVAILABLE = False
    WhylineUI = None

from .cli import WhylineCLI

__version__ = "0.1.0"
__all__ = [
    "WhylineTracer",
    "get_tracer", 
    "start_tracing",
    "stop_tracing",
    "instrument_code",
    "instrument_file",
    "exec_instrumented",
    "QuestionAsker",
    "Question",
    "Answer",
    "WhylineCLI",
    "UI_AVAILABLE"
]

# Only export WhylineUI if available
if UI_AVAILABLE:
    __all__.append("WhylineUI")