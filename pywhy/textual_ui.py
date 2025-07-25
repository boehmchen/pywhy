"""
Textual-based UI for Python Whyline.
Provides a modern terminal-based interface for debugging with highlighted components.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Button, TextArea, Tree, ListView, ListItem, 
    Label, Input, Tabs, TabPane, DataTable, Static, RichLog
)
from textual.reactive import reactive
from textual.message import Message
from textual.screen import Screen
from textual.binding import Binding
from textual import events
from rich.console import Console
from rich.syntax import Syntax
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.tree import Tree as RichTree
from rich.columns import Columns
from rich.align import Align
from rich.highlighter import ReprHighlighter
from typing import List, Dict, Any, Optional, Tuple
import ast
import inspect
import traceback
from pathlib import Path

from .tracer import WhylineTracer, TraceEvent, get_tracer
from .questions import QuestionAsker, Question, Answer
from .instrumenter import instrument_code, exec_instrumented


class SourceCodeWidget(ScrollableContainer):
    """Widget for displaying source code with syntax highlighting"""
    
    def __init__(self, source: str = "", language: str = "python", **kwargs):
        super().__init__(**kwargs)
        self.source = source
        self.language = language
        self.line_highlights = {}  # line_no -> style
        self.content_widget = None
        
    def on_mount(self) -> None:
        """Called when widget is mounted"""
        self._setup_content()
        
    def _setup_content(self):
        """Setup the scrollable content"""
        if self.content_widget:
            self.content_widget.remove()
        
        self.content_widget = Static(self._render_syntax(), id="source_content")
        if self.is_mounted:
            self.mount(self.content_widget)
    
    def _render_syntax(self) -> Syntax:
        """Render the source code with syntax highlighting"""
        if not self.source:
            return Syntax("# No source code loaded", "python")
        
        syntax = Syntax(
            self.source,
            self.language,
            theme="monokai",
            line_numbers=True,
            word_wrap=False,
            background_color="default"
        )
        
        # Add line highlights if any
        if self.line_highlights:
            for line_no, style in self.line_highlights.items():
                syntax.highlight_lines.add(line_no)
        
        return syntax
    
    def update_source(self, source: str, language: str = "python"):
        """Update the source code"""
        self.source = source
        self.language = language
        self._setup_content()
    
    def highlight_line(self, line_no: int, style: str = "bold red"):
        """Highlight a specific line"""
        self.line_highlights[line_no] = style
        self._setup_content()
    
    def clear_highlights(self):
        """Clear all line highlights"""
        self.line_highlights.clear()
        self._setup_content()
    
    def scroll_to_line(self, line_no: int):
        """Scroll to a specific line number"""
        if not self.source:
            return
        
        lines = self.source.split('\n')
        if 1 <= line_no <= len(lines):
            try:
                # Estimate scroll position based on line number
                # Each line is roughly 1 unit tall
                scroll_y = max(0, line_no - 5)  # Center the line with some context
                self.scroll_to(0, scroll_y, animate=True)
            except Exception:
                # If animated scroll fails, try without animation
                try:
                    self.scroll_to(0, scroll_y, animate=False)
                except Exception:
                    # If that also fails, just refresh the widget
                    self.refresh()


class TraceEventWidget(Static):
    """Widget for displaying trace events in a formatted way"""
    
    def __init__(self, events: List[TraceEvent] = None, **kwargs):
        super().__init__(**kwargs)
        self.events = events or []
    
    def render(self) -> Table:
        """Render trace events as a table"""
        table = Table(
            "ID", "Type", "Line", "File", "Data", "Locals",
            title="Trace Events",
            show_header=True,
            header_style="bold magenta",
            expand=True
        )
        
        for event in self.events[-20:]:  # Show last 20 events
            # Format data
            data_items = list(event.data.items())[:3]
            data_str = ", ".join(f"{k}={v}" for k, v in data_items)
            if len(event.data) > 3:
                data_str += "..."
            
            # Format locals (show just a few key variables)
            locals_items = list(event.locals_snapshot.items())[:2]
            locals_str = ", ".join(f"{k}={v}" for k, v in locals_items)
            if len(event.locals_snapshot) > 2:
                locals_str += "..."
            
            # Color code by event type
            event_type_style = {
                'assign': 'green',
                'function_entry': 'blue',
                'return': 'yellow',
                'branch': 'red',
                'condition': 'cyan'
            }.get(event.event_type, 'white')
            
            table.add_row(
                str(event.event_id),
                f"[{event_type_style}]{event.event_type}[/{event_type_style}]",
                str(event.lineno),
                Path(event.filename).name,
                data_str,
                locals_str
            )
        
        return table
    
    def update_events(self, events: List[TraceEvent]):
        """Update the displayed events"""
        self.events = events
        self.refresh()


class QuestionWidget(ListView):
    """Widget for displaying and managing questions"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.questions: List[Question] = []
    
    def add_question(self, question: Question):
        """Add a new question to the list"""
        self.questions.append(question)
        self.append(ListItem(Label(str(question))))
    
    def clear_questions(self):
        """Clear all questions"""
        self.questions.clear()
        self.clear()
    
    def get_selected_question(self) -> Optional[Question]:
        """Get the currently selected question"""
        if self.index is not None and 0 <= self.index < len(self.questions):
            return self.questions[self.index]
        return None


class AnswerWidget(Static):
    """Widget for displaying answers to questions"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_answer = None
    
    def render(self) -> Panel:
        """Render the current answer"""
        if not self.current_answer:
            return Panel(
                "No answer selected. Click on a question to see its answer.",
                title="Answer",
                border_style="dim"
            )
        
        answer = self.current_answer
        
        # Create answer content
        content = []
        
        # Main explanation
        content.append(f"[bold green]Answer:[/bold green] {answer.explanation}")
        content.append(f"[dim]Confidence: {answer.confidence:.2f}[/dim]")
        content.append("")
        
        # Evidence
        if answer.evidence:
            content.append(f"[bold yellow]Evidence ({len(answer.evidence)} events):[/bold yellow]")
            for i, event in enumerate(answer.evidence[:5]):  # Show first 5
                content.append(f"  {i+1}. Line {event.lineno}: {event.event_type}")
            if len(answer.evidence) > 5:
                content.append(f"  ... and {len(answer.evidence) - 5} more events")
        
        answer_text = "\n".join(content)
        
        return Panel(
            answer_text,
            title=f"Answer: {answer.question.subject}",
            border_style="green"
        )
    
    def update_answer(self, answer: Answer):
        """Update the displayed answer"""
        self.current_answer = answer
        self.refresh()
    
    def clear_answer(self):
        """Clear the current answer"""
        self.current_answer = None
        self.refresh()


class StatsWidget(Static):
    """Widget for displaying trace statistics"""
    
    def __init__(self, tracer: WhylineTracer, **kwargs):
        super().__init__(**kwargs)
        self.tracer = tracer
    
    def render(self) -> Panel:
        """Render trace statistics"""
        stats = self.tracer.get_stats()
        
        # Create statistics table
        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Total Events", str(stats['total_events']))
        table.add_row("Files Traced", str(stats['files_traced']))
        table.add_row("Time Span", f"{stats['time_span']:.2f}s")
        
        # Event type breakdown
        table.add_row("", "")
        table.add_row("Event Types:", "")
        for event_type, count in stats['event_types'].items():
            table.add_row(f"  {event_type}", str(count))
        
        return Panel(
            table,
            title="Trace Statistics",
            border_style="cyan"
        )


class FileDialog(Screen):
    """Simple file dialog for opening Python files"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_file = None
    
    def compose(self) -> ComposeResult:
        """Compose the file dialog"""
        yield Container(
            Label("Select a Python file to open:"),
            Input(placeholder="Enter file path...", id="file_input"),
            Horizontal(
                Button("Open", variant="primary", id="open_btn"),
                Button("Cancel", id="cancel_btn"),
            ),
            id="file_dialog"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "open_btn":
            file_input = self.query_one("#file_input", Input)
            filepath = file_input.value.strip()
            if filepath:
                self.selected_file = filepath
                self.dismiss(filepath)
        elif event.button.id == "cancel_btn":
            self.dismiss(None)


class QuestionDialog(Screen):
    """Dialog for asking questions about the code"""
    
    def __init__(self, question_type: str = "general", **kwargs):
        super().__init__(**kwargs)
        self.question_type = question_type
        self.result = None
    
    def compose(self) -> ComposeResult:
        """Compose the question dialog"""
        title = {
            "general": "Ask a Question",
            "variable": "Ask about Variable Value",
            "line": "Ask about Line Execution",
            "function": "Ask about Function Return"
        }.get(self.question_type, "Ask a Question")
        
        with Container(id="question_dialog"):
            yield Label(title, id="dialog_title")
            
            if self.question_type == "variable":
                yield Label("Variable name:")
                yield Input(placeholder="e.g., result", id="var_name")
                yield Label("Value:")
                yield Input(placeholder="e.g., 42", id="var_value")
                yield Label("Line number (optional):")
                yield Input(placeholder="e.g., 10", id="line_num")
            
            elif self.question_type == "line":
                yield Label("Line number:")
                yield Input(placeholder="e.g., 15", id="line_num")
                yield Label("Question type:")
                yield Horizontal(
                    Button("Why did it execute?", id="why_did", variant="primary"),
                    Button("Why didn't it execute?", id="why_didnt"),
                )
            
            elif self.question_type == "function":
                yield Label("Function name:")
                yield Input(placeholder="e.g., calculate", id="func_name")
                yield Label("Return value:")
                yield Input(placeholder="e.g., 100", id="return_value")
            
            else:  # general
                yield Label("Choose question type:")
                yield Vertical(
                    Button("Why did variable have value?", id="var_question"),
                    Button("Why did line execute?", id="line_execute"),
                    Button("Why didn't line execute?", id="line_no_execute"),
                    Button("Why did function return value?", id="func_return"),
                )
            
            yield Horizontal(
                Button("Ask", variant="primary", id="ask_btn"),
                Button("Cancel", id="cancel_btn"),
            )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "ask_btn":
            self._handle_ask()
        elif event.button.id == "cancel_btn":
            self.dismiss(None)
        elif event.button.id in ["var_question", "line_execute", "line_no_execute", "func_return"]:
            # Switch to specific question type
            question_types = {
                "var_question": "variable",
                "line_execute": "line",
                "line_no_execute": "line",
                "func_return": "function"
            }
            new_type = question_types[event.button.id]
            self.app.push_screen(QuestionDialog(new_type), self.app.handle_question_result)
            self.dismiss(None)
        elif event.button.id in ["why_did", "why_didnt"]:
            # Handle line execution questions
            line_input = self.query_one("#line_num", Input)
            try:
                line_num = int(line_input.value.strip())
                question_type = "line_execute" if event.button.id == "why_did" else "line_no_execute"
                self.result = {"type": question_type, "line_num": line_num}
                self.dismiss(self.result)
            except ValueError:
                self.notify("Please enter a valid line number", severity="error")
    
    def _handle_ask(self):
        """Handle the ask button press"""
        try:
            if self.question_type == "variable":
                var_name = self.query_one("#var_name", Input).value.strip()
                var_value = self.query_one("#var_value", Input).value.strip()
                line_num_str = self.query_one("#line_num", Input).value.strip()
                
                if not var_name or not var_value:
                    self.notify("Please fill in variable name and value", severity="error")
                    return
                
                # Try to evaluate the value
                try:
                    value = eval(var_value)
                except:
                    value = var_value
                
                line_num = int(line_num_str) if line_num_str else None
                
                self.result = {
                    "type": "variable",
                    "var_name": var_name,
                    "value": value,
                    "line_num": line_num
                }
                self.dismiss(self.result)
            
            elif self.question_type == "function":
                func_name = self.query_one("#func_name", Input).value.strip()
                return_value = self.query_one("#return_value", Input).value.strip()
                
                if not func_name or not return_value:
                    self.notify("Please fill in function name and return value", severity="error")
                    return
                
                # Try to evaluate the return value
                try:
                    value = eval(return_value)
                except:
                    value = return_value
                
                self.result = {
                    "type": "function",
                    "func_name": func_name,
                    "return_value": value
                }
                self.dismiss(self.result)
                
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")


class GotoLineDialog(Screen):
    """Dialog for jumping to a specific line in the source code"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.result = None
    
    def compose(self) -> ComposeResult:
        """Compose the goto line dialog"""
        with Container(id="goto_dialog"):
            yield Label("Go to Line", id="dialog_title")
            yield Label("Line number:")
            yield Input(placeholder="Enter line number...", id="line_input")
            yield Horizontal(
                Button("Go", variant="primary", id="go_btn"),
                Button("Cancel", id="cancel_btn"),
            )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "go_btn":
            line_input = self.query_one("#line_input", Input)
            try:
                line_no = int(line_input.value.strip())
                if line_no > 0:
                    self.result = line_no
                    self.dismiss(line_no)
                else:
                    self.notify("Please enter a positive line number", severity="error")
            except ValueError:
                self.notify("Please enter a valid line number", severity="error")
        elif event.button.id == "cancel_btn":
            self.dismiss(None)
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input field"""
        if event.input.id == "line_input":
            # Simulate clicking the Go button
            self.on_button_pressed(type('MockEvent', (), {'button': type('MockButton', (), {'id': 'go_btn'})()})())


class WhylineApp(App):
    """Main Whyline application using Textual"""
    
    CSS = """
    #main_container {
        layout: grid;
        grid-size: 3 2;
        grid-gutter: 1;
        height: 100%;
    }
    
    #source_panel {
        column-span: 2;
        row-span: 1;
        border: solid $primary;
        background: $surface;
    }
    
    #trace_panel {
        column-span: 1;
        row-span: 1;
        border: solid $secondary;
        background: $surface;
    }
    
    #questions_panel {
        column-span: 1;
        row-span: 1;
        border: solid $accent;
        background: $surface;
    }
    
    #answer_panel {
        column-span: 1;
        row-span: 1;
        border: solid $warning;
        background: $surface;
    }
    
    #stats_panel {
        column-span: 1;
        row-span: 1;
        border: solid $success;
        background: $surface;
    }
    
    .panel_title {
        text-style: bold;
        color: $text;
        background: $primary;
        padding: 0 1;
    }
    
    .highlighted_line {
        background: $warning 50%;
    }
    
    #question_dialog {
        background: $surface;
        border: solid $primary;
        padding: 1;
        width: 60%;
        height: auto;
        margin: 2;
    }
    
    #dialog_title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    #file_dialog {
        background: $surface;
        border: solid $secondary;
        padding: 1;
        width: 50%;
        height: auto;
        margin: 2;
    }
    
    #source_code {
        height: 100%;
        overflow-y: auto;
        overflow-x: auto;
        scrollbar-background: $surface;
        scrollbar-color: $primary;
        scrollbar-corner-color: $surface;
    }
    
    #source_content {
        height: auto;
        width: auto;
        min-height: 100%;
    }
    
    #goto_dialog {
        background: $surface;
        border: solid $accent;
        padding: 1;
        width: 40%;
        height: auto;
        margin: 3;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+o", "open_file", "Open File"),
        Binding("ctrl+r", "run_code", "Run Code"),
        Binding("ctrl+c", "clear_trace", "Clear Trace"),
        Binding("ctrl+s", "save_trace", "Save Trace"),
        Binding("ctrl+l", "load_trace", "Load Trace"),
        Binding("f1", "help", "Help"),
        Binding("ctrl+shift+q", "ask_question", "Ask Question"),
        Binding("ctrl+shift+v", "ask_variable", "Ask Variable"),
        Binding("ctrl+shift+l", "ask_line", "Ask Line"),
        Binding("ctrl+shift+f", "ask_function", "Ask Function"),
        Binding("ctrl+shift+g", "goto_line", "Go to Line"),
        Binding("ctrl+shift+t", "scroll_to_top", "Scroll to Top"),
        Binding("ctrl+shift+b", "scroll_to_bottom", "Scroll to Bottom"),
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tracer = get_tracer()
        self.asker = QuestionAsker(self.tracer)
        self.current_source = ""
        self.current_file = None
        
    def compose(self) -> ComposeResult:
        """Compose the main application layout"""
        yield Header()
        
        with Container(id="main_container"):
            # Source code panel (top left, spans 2 columns)
            with Vertical(id="source_panel"):
                yield Label("Source Code", classes="panel_title")
                yield SourceCodeWidget(id="source_code")
            
            # Trace events panel (top right)
            with Vertical(id="trace_panel"):
                yield Label("Trace Events", classes="panel_title")
                yield TraceEventWidget(id="trace_events")
            
            # Questions panel (bottom left)
            with Vertical(id="questions_panel"):
                yield Label("Questions", classes="panel_title")
                yield QuestionWidget(id="questions")
            
            # Answer panel (bottom center)
            with Vertical(id="answer_panel"):
                yield Label("Answer", classes="panel_title")
                yield AnswerWidget(id="answer")
            
            # Statistics panel (bottom right)
            with Vertical(id="stats_panel"):
                yield Label("Statistics", classes="panel_title")
                yield StatsWidget(self.tracer, id="stats")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when the app is mounted"""
        self.title = "Python Whyline - Advanced Debugging Interface"
        self.sub_title = "Ask 'why' and 'why not' questions about your code"
        
        # Load a sample file if available
        sample_files = [
            "working_example.py",
            "example.py", 
            "demo.py"
        ]
        
        for filename in sample_files:
            if Path(filename).exists():
                self.load_file(filename)
                break
    
    def action_open_file(self) -> None:
        """Open a file dialog"""
        self.push_screen(FileDialog(), self.handle_file_selected)
    
    def handle_file_selected(self, filepath: str) -> None:
        """Handle file selection from dialog"""
        if filepath:
            self.load_file(filepath)
    
    def load_file(self, filepath: str) -> None:
        """Load a Python file"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            self.current_source = content
            self.current_file = filepath
            
            # Update source code widget
            source_widget = self.query_one("#source_code", SourceCodeWidget)
            source_widget.update_source(content)
            
            # Update title
            self.sub_title = f"Loaded: {Path(filepath).name}"
            
        except Exception as e:
            self.notify(f"Error loading file: {e}", severity="error")
    
    def action_run_code(self) -> None:
        """Run the current code with instrumentation"""
        if not self.current_source:
            self.notify("No code to run", severity="warning")
            return
        
        try:
            # Clear previous trace
            self.tracer.clear()
            
            # Show running status
            self.sub_title = "Running code..."
            
            # Check if code has __name__ guard and notify user
            if 'if __name__ == "__main__":' in self.current_source:
                self.notify("Detected __name__ == '__main__' guard - will be modified to execute main code", severity="information")
            
            # Execute instrumented code
            exec_instrumented(self.current_source)
            
            # Update trace events
            trace_widget = self.query_one("#trace_events", TraceEventWidget)
            trace_widget.update_events(self.tracer.events)
            
            # Update statistics
            stats_widget = self.query_one("#stats", StatsWidget)
            stats_widget.refresh()
            
            # Update status
            stats = self.tracer.get_stats()
            self.sub_title = f"Executed: {stats['total_events']} events recorded"
            
            if stats['total_events'] == 0:
                self.notify("⚠️ No events recorded. This might happen if the code only defines functions without calling them.", severity="warning")
            else:
                self.notify(f"Code executed successfully. {stats['total_events']} events recorded.", severity="information")
            
        except Exception as e:
            self.notify(f"Error running code: {e}", severity="error")
            self.sub_title = "Execution failed"
    
    def action_clear_trace(self) -> None:
        """Clear the current trace"""
        self.tracer.clear()
        
        # Clear all widgets
        trace_widget = self.query_one("#trace_events", TraceEventWidget)
        trace_widget.update_events([])
        
        questions_widget = self.query_one("#questions", QuestionWidget)
        questions_widget.clear_questions()
        
        answer_widget = self.query_one("#answer", AnswerWidget)
        answer_widget.clear_answer()
        
        stats_widget = self.query_one("#stats", StatsWidget)
        stats_widget.refresh()
        
        self.sub_title = "Trace cleared"
        self.notify("Trace cleared", severity="information")
    
    def action_save_trace(self) -> None:
        """Save the current trace"""
        if not self.tracer.events:
            self.notify("No trace to save", severity="warning")
            return
        
        try:
            filename = f"trace_{len(self.tracer.events)}_events.pkl"
            self.tracer.save_trace(filename)
            self.notify(f"Trace saved to {filename}", severity="information")
        except Exception as e:
            self.notify(f"Error saving trace: {e}", severity="error")
    
    def action_load_trace(self) -> None:
        """Load a trace file"""
        # For now, just show a notification
        self.notify("Load trace feature coming soon", severity="information")
    
    def action_help(self) -> None:
        """Show help information"""
        help_text = """
        # Python Whyline Help
        
        ## Key Bindings:
        - **Ctrl+Q**: Quit application
        - **Ctrl+O**: Open Python file
        - **Ctrl+R**: Run code with instrumentation
        - **Ctrl+C**: Clear trace
        - **Ctrl+S**: Save trace
        - **Ctrl+L**: Load trace
        - **F1**: Show this help
        - **Ctrl+Shift+Q**: Ask general question
        - **Ctrl+Shift+V**: Ask about variable value
        - **Ctrl+Shift+L**: Ask about line execution
        - **Ctrl+Shift+F**: Ask about function return
        
        ## Navigation:
        - **Ctrl+Shift+G**: Go to line
        - **Ctrl+Shift+T**: Scroll to top
        - **Ctrl+Shift+B**: Scroll to bottom
        - **Mouse wheel**: Scroll source code
        
        ## Usage:
        1. Open a Python file (Ctrl+O)
        2. Run the code (Ctrl+R) to collect trace
        3. Use Ctrl+Shift+Q to ask questions
        4. Click questions to see answers
        5. Use navigation shortcuts to explore code
        
        ## Question Types:
        - Why did line X execute?
        - Why didn't line X execute?
        - Why did variable X have value Y?
        - Why did function return value Z?
        """
        
        self.notify(help_text, severity="information")
    
    def action_ask_question(self) -> None:
        """Open general question dialog"""
        if not self.tracer.events:
            self.notify("No trace data available. Run code first.", severity="warning")
            return
        
        self.push_screen(QuestionDialog("general"), self.handle_question_result)
    
    def action_ask_variable(self) -> None:
        """Open variable question dialog"""
        if not self.tracer.events:
            self.notify("No trace data available. Run code first.", severity="warning")
            return
        
        self.push_screen(QuestionDialog("variable"), self.handle_question_result)
    
    def action_ask_line(self) -> None:
        """Open line execution question dialog"""
        if not self.tracer.events:
            self.notify("No trace data available. Run code first.", severity="warning")
            return
        
        self.push_screen(QuestionDialog("line"), self.handle_question_result)
    
    def action_ask_function(self) -> None:
        """Open function return question dialog"""
        if not self.tracer.events:
            self.notify("No trace data available. Run code first.", severity="warning")
            return
        
        self.push_screen(QuestionDialog("function"), self.handle_question_result)
    
    def handle_question_result(self, result: dict) -> None:
        """Handle the result from a question dialog"""
        if not result:
            return
        
        try:
            question = None
            filename = self.current_file or "<string>"
            
            if result["type"] == "variable":
                question = self.asker.why_did_variable_have_value(
                    result["var_name"], 
                    result["value"], 
                    filename, 
                    result.get("line_num")
                )
            elif result["type"] == "line_execute":
                question = self.asker.why_did_line_execute(filename, result["line_num"])
            elif result["type"] == "line_no_execute":
                question = self.asker.why_didnt_line_execute(filename, result["line_num"])
            elif result["type"] == "function":
                question = self.asker.why_did_function_return(
                    result["func_name"], 
                    result["return_value"]
                )
            
            if question:
                questions_widget = self.query_one("#questions", QuestionWidget)
                questions_widget.add_question(question)
                self.notify(f"Added question: {question}", severity="information")
            
        except Exception as e:
            self.notify(f"Error creating question: {e}", severity="error")
    
    def get_suggested_questions(self) -> List[str]:
        """Get suggested questions based on trace data"""
        suggestions = []
        
        if not self.tracer.events:
            return ["No trace data available. Run code first."]
        
        # Find interesting variables
        variables = {}
        for event in self.tracer.events:
            if event.event_type in ['assign', 'aug_assign'] and event.data.get('var_name'):
                var_name = event.data.get('var_name')
                value = event.data.get('value')
                variables[var_name] = value
        
        # Suggest variable questions
        for var_name, value in list(variables.items())[:3]:  # Top 3 variables
            suggestions.append(f"Why did variable '{var_name}' have value '{value}'?")
        
        # Find interesting lines
        lines = set()
        for event in self.tracer.events:
            lines.add(event.lineno)
        
        # Suggest line questions
        for line_no in sorted(lines)[:3]:  # First 3 lines
            suggestions.append(f"Why did line {line_no} execute?")
        
        # Find function calls
        functions = set()
        for event in self.tracer.events:
            if event.event_type == 'function_entry' and event.data.get('func_name'):
                func_name = event.data.get('func_name')
                functions.add(func_name)
        
        # Suggest function questions
        for func_name in list(functions)[:2]:  # Top 2 functions
            suggestions.append(f"Why did function '{func_name}' get called?")
        
        return suggestions[:8]  # Max 8 suggestions
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle question selection"""
        if event.list_view.id == "questions":
            questions_widget = self.query_one("#questions", QuestionWidget)
            question = questions_widget.get_selected_question()
            
            if question:
                try:
                    # Show computing status
                    self.sub_title = "Computing answer..."
                    
                    # Compute answer
                    answer = question.get_answer()
                    
                    # Display answer
                    answer_widget = self.query_one("#answer", AnswerWidget)
                    answer_widget.update_answer(answer)
                    
                    # Highlight relevant lines in source
                    try:
                        source_widget = self.query_one("#source_code", SourceCodeWidget)
                        source_widget.clear_highlights()
                        
                        evidence_lines = []
                        for event in answer.evidence[:5]:  # Highlight first 5 evidence lines
                            source_widget.highlight_line(event.lineno)
                            evidence_lines.append(event.lineno)
                        
                        # Scroll to the first evidence line
                        if evidence_lines:
                            source_widget.scroll_to_line(evidence_lines[0])
                    except Exception as scroll_error:
                        # Don't fail the whole operation if scrolling fails
                        self.notify(f"Scrolling error: {scroll_error}", severity="warning")
                    
                    self.sub_title = "Answer computed"
                    
                except Exception as e:
                    self.notify(f"Error computing answer: {e}", severity="error")
    
    def action_goto_line(self) -> None:
        """Open go to line dialog"""
        self.push_screen(GotoLineDialog(), self.handle_goto_line)
    
    def action_scroll_to_top(self) -> None:
        """Scroll source code to top"""
        source_widget = self.query_one("#source_code", SourceCodeWidget)
        source_widget.scroll_to(0, 0)
        self.notify("Scrolled to top", severity="information")
    
    def action_scroll_to_bottom(self) -> None:
        """Scroll source code to bottom"""
        source_widget = self.query_one("#source_code", SourceCodeWidget)
        # Scroll to a very large Y coordinate to reach the bottom
        source_widget.scroll_to(0, 10000)
        self.notify("Scrolled to bottom", severity="information")
    
    def handle_goto_line(self, line_no: int) -> None:
        """Handle go to line result"""
        if line_no:
            source_widget = self.query_one("#source_code", SourceCodeWidget)
            source_widget.scroll_to_line(line_no)
            self.notify(f"Jumped to line {line_no}", severity="information")
    
    def on_key(self, event: events.Key) -> None:
        """Handle key presses for question shortcuts"""
        if event.key == "q":
            # Quick question dialog
            self.action_ask_question()


def main():
    """Main entry point for the Textual UI"""
    app = WhylineApp()
    app.run()


if __name__ == "__main__":
    main()