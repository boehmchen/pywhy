"""
Command-line interface for Python Whyline.
Alternative to the GUI that works without tkinter.
"""

import os
import sys
import cmd
import tempfile
from typing import Optional, List

# Handle both relative and absolute imports
try:
    from .tracer import get_tracer, TraceEvent
    from .instrumenter import instrument_code, exec_instrumented
    from .questions import QuestionAsker, Question, Answer
except ImportError:
    # If relative imports fail, try absolute imports
    try:
        from python_whyline.tracer import get_tracer, TraceEvent
        from python_whyline.instrumenter import instrument_code, exec_instrumented
        from python_whyline.questions import QuestionAsker, Question, Answer
    except ImportError:
        # If that fails too, add the parent directory to the path
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from python_whyline.tracer import get_tracer, TraceEvent
        from python_whyline.instrumenter import instrument_code, exec_instrumented
        from python_whyline.questions import QuestionAsker, Question, Answer


class WhylineCLI(cmd.Cmd):
    """Interactive command-line interface for Python Whyline"""
    
    intro = '''
Python Whyline - Interactive Debugging Tool
==========================================

Commands:
  load <filename>     - Load a Python file
  code                - Enter code interactively
  run                 - Execute the current code with tracing
  ask                 - Ask questions about execution
  trace               - Show trace statistics
  events              - Show recent trace events
  clear               - Clear current trace
  help                - Show this help
  quit                - Exit

Type 'help <command>' for detailed help on a command.
'''
    
    prompt = 'whyline> '
    
    def __init__(self):
        super().__init__()
        self.tracer = get_tracer()
        self.asker = QuestionAsker(self.tracer)
        self.current_code = ""
        self.current_filename = "<interactive>"
        self.questions: List[Question] = []
    
    def do_load(self, filename: str):
        """Load a Python file: load <filename>"""
        if not filename:
            print("Usage: load <filename>")
            return
        
        try:
            with open(filename, 'r') as f:
                self.current_code = f.read()
            self.current_filename = filename
            print(f"Loaded {filename}")
            print("Code:")
            print("-" * 40)
            self._show_code_with_line_numbers()
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found")
        except Exception as e:
            print(f"Error loading file: {e}")
    
    def do_code(self, line: str):
        """Enter code interactively. Type 'END' on a line by itself to finish."""
        print("Enter Python code (type 'END' on a line by itself to finish):")
        
        code_lines = []
        while True:
            try:
                line = input("... ")
                if line.strip() == 'END':
                    break
                code_lines.append(line)
            except KeyboardInterrupt:
                print("\nCode entry cancelled")
                return
            except EOFError:
                break
        
        self.current_code = '\n'.join(code_lines)
        self.current_filename = "<interactive>"
        print("Code entered:")
        print("-" * 40)
        self._show_code_with_line_numbers()
    
    def do_run(self, line: str):
        """Execute the current code with tracing"""
        if not self.current_code:
            print("No code to run. Use 'load <filename>' or 'code' first.")
            return
        
        print("Executing code with tracing...")
        self.tracer.clear()
        
        try:
            # Handle files with __name__ == "__main__" blocks
            code_to_run = self.current_code
            if 'if __name__ == "__main__":' in code_to_run:
                # Replace the condition to make it always true
                code_to_run = code_to_run.replace('if __name__ == "__main__":', 'if True:')
                print("(Modified __name__ check to run main code)")
            
            exec_instrumented(code_to_run)
            stats = self.tracer.get_stats()
            print(f"Execution completed. {stats['total_events']} events recorded.")
            
            if stats['total_events'] == 0:
                print("⚠️  No events recorded. This might happen if:")
                print("   - The code only defines functions without calling them")
                print("   - There are syntax errors in the code")
                print("   - The code runs too quickly to be traced")
        except Exception as e:
            print(f"Execution error: {e}")
            import traceback
            traceback.print_exc()
    
    def do_ask(self, line: str):
        """Ask questions about execution"""
        if not self.tracer.events:
            print("No trace data available. Run code first.")
            return
        
        print("\nAvailable question types:")
        print("1. Why did variable X have value Y?")
        print("2. Why did line N execute?")
        print("3. Why didn't line N execute?")
        print("4. Why did function F return value V?")
        print("5. Show previous questions")
        
        try:
            choice = input("Enter choice (1-5): ").strip()
            
            if choice == '1':
                self._ask_variable_value()
            elif choice == '2':
                self._ask_line_executed()
            elif choice == '3':
                self._ask_line_not_executed()
            elif choice == '4':
                self._ask_function_return()
            elif choice == '5':
                self._show_previous_questions()
            else:
                print("Invalid choice")
        except KeyboardInterrupt:
            print("\nCancelled")
        except EOFError:
            print("\nCancelled")
    
    def _ask_variable_value(self):
        """Ask why a variable had a specific value"""
        var_name = input("Variable name: ").strip()
        if not var_name:
            print("Variable name required")
            return
        
        value_str = input("Value: ").strip()
        if not value_str:
            print("Value required")
            return
        
        # Try to evaluate the value
        try:
            value = eval(value_str)
        except:
            value = value_str
        
        line_no_str = input("Line number (optional): ").strip()
        line_no = int(line_no_str) if line_no_str else None
        
        question = self.asker.why_did_variable_have_value(
            var_name, value, self.current_filename, line_no
        )
        self._process_question(question)
    
    def _ask_line_executed(self):
        """Ask why a line executed"""
        line_no_str = input("Line number: ").strip()
        if not line_no_str:
            print("Line number required")
            return
        
        try:
            line_no = int(line_no_str)
        except ValueError:
            print("Invalid line number")
            return
        
        question = self.asker.why_did_line_execute(self.current_filename, line_no)
        self._process_question(question)
    
    def _ask_line_not_executed(self):
        """Ask why a line didn't execute"""
        line_no_str = input("Line number: ").strip()
        if not line_no_str:
            print("Line number required")
            return
        
        try:
            line_no = int(line_no_str)
        except ValueError:
            print("Invalid line number")
            return
        
        question = self.asker.why_didnt_line_execute(self.current_filename, line_no)
        self._process_question(question)
    
    def _ask_function_return(self):
        """Ask why a function returned a specific value"""
        func_name = input("Function name: ").strip()
        if not func_name:
            print("Function name required")
            return
        
        value_str = input("Return value: ").strip()
        if not value_str:
            print("Return value required")
            return
        
        # Try to evaluate the value
        try:
            value = eval(value_str)
        except:
            value = value_str
        
        question = self.asker.why_did_function_return(func_name, value)
        self._process_question(question)
    
    def _process_question(self, question: Question):
        """Process a question and show the answer"""
        self.questions.append(question)
        
        print(f"\nQuestion: {question}")
        print("Computing answer...")
        
        try:
            answer = question.get_answer()
            print(f"\nAnswer: {answer}")
            
            if answer.evidence:
                print(f"\nEvidence ({len(answer.evidence)} events):")
                for i, event in enumerate(answer.evidence[:5]):  # Show first 5
                    print(f"  {i+1}. Line {event.lineno}: {event.event_type}")
                    if event.data:
                        print(f"      Data: {event.data}")
                
                if len(answer.evidence) > 5:
                    print(f"  ... and {len(answer.evidence) - 5} more events")
        except Exception as e:
            print(f"Error computing answer: {e}")
    
    def _show_previous_questions(self):
        """Show previously asked questions"""
        if not self.questions:
            print("No previous questions")
            return
        
        print("\nPrevious questions:")
        for i, question in enumerate(self.questions, 1):
            print(f"{i}. {question}")
        
        try:
            choice = input("Enter question number to see answer (or press Enter): ").strip()
            if choice:
                idx = int(choice) - 1
                if 0 <= idx < len(self.questions):
                    question = self.questions[idx]
                    answer = question.get_answer()
                    print(f"\nAnswer: {answer}")
                else:
                    print("Invalid question number")
        except ValueError:
            print("Invalid input")
        except (KeyboardInterrupt, EOFError):
            pass
    
    def do_trace(self, line: str):
        """Show trace statistics"""
        stats = self.tracer.get_stats()
        print(f"Trace Statistics:")
        print(f"  Total events: {stats['total_events']}")
        print(f"  Files traced: {stats['files_traced']}")
        print(f"  Time span: {stats['time_span']:.3f} seconds")
        print(f"  Event types: {stats['event_types']}")
    
    def do_events(self, line: str):
        """Show recent trace events"""
        if not self.tracer.events:
            print("No trace events")
            return
        
        # Parse optional count argument
        count = 10
        if line.strip():
            try:
                count = int(line.strip())
            except ValueError:
                print("Invalid count, using default (10)")
        
        print(f"Recent {count} trace events:")
        events = self.tracer.events[-count:]
        
        for event in events:
            print(f"  {event.event_id}: Line {event.lineno} - {event.event_type}")
            if event.data:
                print(f"    Data: {event.data}")
    
    def do_clear(self, line: str):
        """Clear current trace"""
        self.tracer.clear()
        self.questions.clear()
        print("Trace cleared")
    
    def do_quit(self, line: str):
        """Exit the program"""
        print("Goodbye!")
        return True
    
    def do_exit(self, line: str):
        """Exit the program"""
        return self.do_quit(line)
    
    def do_EOF(self, line: str):
        """Handle Ctrl+D"""
        print("\nGoodbye!")
        return True
    
    def _show_code_with_line_numbers(self):
        """Display code with line numbers"""
        if not self.current_code:
            print("No code loaded")
            return
        
        lines = self.current_code.split('\n')
        for i, line in enumerate(lines, 1):
            print(f"{i:3d}: {line}")
    
    def emptyline(self):
        """Do nothing on empty line"""
        pass


def main():
    """Main entry point for CLI"""
    # Check for UI mode arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--textual" or sys.argv[1] == "-t":
            # Launch Textual UI
            try:
                from .textual_ui import WhylineApp
                print("🚀 Launching Textual UI...")
                app = WhylineApp()
                app.run()
                return
            except ImportError:
                print("❌ Textual UI not available. Install with: pip install textual rich")
                return
        elif sys.argv[1] == "--tkinter" or sys.argv[1] == "-k":
            # Launch Tkinter UI
            try:
                from .ui import WhylineUI
                print("🚀 Launching Tkinter UI...")
                app = WhylineUI()
                app.run()
                return
            except ImportError:
                print("❌ Tkinter UI not available. Install tkinter.")
                return
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("""
Python Whyline - Interactive Debugging Tool

Usage:
    python -m python_whyline.cli [options] [filename]

Options:
    --textual, -t    Launch modern Textual-based UI
    --tkinter, -k    Launch traditional Tkinter-based UI
    --help, -h       Show this help message
    
    (no options)     Launch command-line interface

Examples:
    python -m python_whyline.cli                    # Command-line interface
    python -m python_whyline.cli sample.py          # CLI with file loaded
    python -m python_whyline.cli --textual          # Modern UI
    python -m python_whyline.cli --tkinter          # Traditional GUI
""")
            return
    
    # Default: command-line interface
    cli = WhylineCLI()
    
    # If filename provided, load it
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        filename = sys.argv[1]
        cli.do_load(filename)
    
    try:
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    main()