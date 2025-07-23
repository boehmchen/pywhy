"""
Basic UI for Python Whyline.
Provides a simple interface for asking questions about program execution.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from typing import List
import threading
from dataclasses import dataclass

from .tracer import get_tracer
from .questions import QuestionAsker, Question, Answer
from .instrumenter import exec_instrumented


@dataclass
class SourceLocation:
    """Represents a location in source code"""
    filename: str
    line_no: int
    column: int = 0


class WhylineUI:
    """Main UI class for Python Whyline"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Python Whyline")
        self.root.geometry("1200x800")
        
        self.tracer = get_tracer()
        self.asker = QuestionAsker(self.tracer)
        self.current_file = None
        self.current_source = ""
        
        self.setup_ui()
        self.setup_menus()
        
    def setup_ui(self):
        """Setup the main UI components"""
        
        # Create main paned window
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel: Source code
        self.source_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.source_frame, weight=2)
        
        # Source code label
        ttk.Label(self.source_frame, text="Source Code:").pack(anchor=tk.W)
        
        # Source code text area
        self.source_text = scrolledtext.ScrolledText(
            self.source_frame, 
            wrap=tk.NONE,
            font=('Courier', 10)
        )
        self.source_text.pack(fill=tk.BOTH, expand=True)
        
        # Bind right-click for context menu
        self.source_text.bind("<Button-3>", self.show_context_menu)
        self.source_text.bind("<Button-2>", self.show_context_menu)  # Mac
        
        # Right panel: Questions and answers
        self.right_paned = ttk.PanedWindow(self.main_paned, orient=tk.VERTICAL)
        self.main_paned.add(self.right_paned, weight=1)
        
        # Questions panel
        self.questions_frame = ttk.Frame(self.right_paned)
        self.right_paned.add(self.questions_frame, weight=1)
        
        ttk.Label(self.questions_frame, text="Questions:").pack(anchor=tk.W)
        
        self.questions_listbox = tk.Listbox(self.questions_frame, height=10)
        self.questions_listbox.pack(fill=tk.BOTH, expand=True)
        self.questions_listbox.bind('<Double-1>', self.on_question_selected)
        
        # Answers panel
        self.answers_frame = ttk.Frame(self.right_paned)
        self.right_paned.add(self.answers_frame, weight=1)
        
        ttk.Label(self.answers_frame, text="Answer:").pack(anchor=tk.W)
        
        self.answer_text = scrolledtext.ScrolledText(
            self.answers_frame, 
            height=10,
            wrap=tk.WORD
        )
        self.answer_text.pack(fill=tk.BOTH, expand=True)
        
        # Bottom panel: Controls
        self.controls_frame = ttk.Frame(self.root)
        self.controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Execution controls
        ttk.Button(self.controls_frame, text="Run Code", 
                  command=self.run_code).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.controls_frame, text="Clear Trace", 
                  command=self.clear_trace).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = ttk.Label(self.controls_frame, text="Ready")
        self.status_label.pack(side=tk.RIGHT, padx=5)
        
        # Store questions and answers
        self.questions: List[Question] = []
        self.answers: List[Answer] = []
        
    def setup_menus(self):
        """Setup the menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open...", command=self.open_file)
        file_menu.add_command(label="Save Trace...", command=self.save_trace)
        file_menu.add_command(label="Load Trace...", command=self.load_trace)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Show Trace Statistics", command=self.show_trace_stats)
        
    def open_file(self):
        """Open a Python file"""
        filename = filedialog.askopenfilename(
            title="Open Python File",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    content = f.read()
                
                self.current_file = filename
                self.current_source = content
                self.source_text.delete(1.0, tk.END)
                self.source_text.insert(1.0, content)
                self.status_label.config(text=f"Loaded: {filename}")
                
                # Add line numbers
                self.add_line_numbers()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {e}")
    
    def add_line_numbers(self):
        """Add line numbers to the source code display"""
        # This is a simplified version - a full implementation would be more sophisticated
        lines = self.source_text.get(1.0, tk.END).split('\n')
        numbered_lines = []
        for i, line in enumerate(lines, 1):
            if line.strip():  # Don't number empty lines
                numbered_lines.append(f"{i:3d}: {line}")
            else:
                numbered_lines.append(line)
        
        self.source_text.delete(1.0, tk.END)
        self.source_text.insert(1.0, '\n'.join(numbered_lines))
    
    def get_cursor_line(self) -> int:
        """Get the line number at the cursor position"""
        cursor_pos = self.source_text.index(tk.INSERT)
        line_no = int(cursor_pos.split('.')[0])
        return line_no
    
    def show_context_menu(self, event):
        """Show context menu for asking questions"""
        context_menu = tk.Menu(self.root, tearoff=0)
        
        line_no = self.get_cursor_line()
        
        context_menu.add_command(
            label=f"Why did line {line_no} execute?",
            command=lambda: self.ask_why_line_executed(line_no)
        )
        context_menu.add_command(
            label=f"Why didn't line {line_no} execute?",
            command=lambda: self.ask_why_line_not_executed(line_no)
        )
        context_menu.add_separator()
        context_menu.add_command(
            label="Why did variable have value...",
            command=lambda: self.ask_variable_value_dialog(line_no)
        )
        
        try:
            context_menu.post(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def ask_why_line_executed(self, line_no: int):
        """Ask why a specific line executed"""
        if not self.current_file:
            messagebox.showwarning("Warning", "Please open a file first")
            return
        
        question = self.asker.why_did_line_execute(self.current_file, line_no)
        self.add_question(question)
    
    def ask_why_line_not_executed(self, line_no: int):
        """Ask why a specific line didn't execute"""
        if not self.current_file:
            messagebox.showwarning("Warning", "Please open a file first")
            return
        
        question = self.asker.why_didnt_line_execute(self.current_file, line_no)
        self.add_question(question)
    
    def ask_variable_value_dialog(self, line_no: int):
        """Show dialog to ask about variable value"""
        dialog = VariableValueDialog(self.root, self.asker, self.current_file, line_no)
        if dialog.result:
            self.add_question(dialog.result)
    
    def add_question(self, question: Question):
        """Add a question to the UI"""
        self.questions.append(question)
        self.questions_listbox.insert(tk.END, str(question))
        self.status_label.config(text=f"Added question: {question}")
    
    def on_question_selected(self, event):
        """Handle question selection"""
        selection = self.questions_listbox.curselection()
        if not selection:
            return
        
        question_index = selection[0]
        question = self.questions[question_index]
        
        # Show "Computing..." message
        self.answer_text.delete(1.0, tk.END)
        self.answer_text.insert(1.0, "Computing answer...")
        self.root.update()
        
        # Compute answer in background
        def compute_answer():
            try:
                answer = question.get_answer()
                self.root.after(0, lambda: self.display_answer(answer))
            except Exception as e:
                self.root.after(0, lambda: self.display_error(str(e)))
        
        threading.Thread(target=compute_answer, daemon=True).start()
    
    def display_answer(self, answer: Answer):
        """Display an answer in the UI"""
        self.answer_text.delete(1.0, tk.END)
        
        text = f"Answer: {answer.explanation}\n\n"
        text += f"Confidence: {answer.confidence:.2f}\n\n"
        
        if answer.evidence:
            text += f"Evidence ({len(answer.evidence)} events):\n"
            for i, event in enumerate(answer.evidence[:10]):  # Show first 10
                text += f"  {i+1}. Line {event.lineno}: {event.event_type}\n"
            
            if len(answer.evidence) > 10:
                text += f"  ... and {len(answer.evidence) - 10} more events\n"
        
        self.answer_text.insert(1.0, text)
        self.status_label.config(text="Answer computed")
    
    def display_error(self, error: str):
        """Display an error message"""
        self.answer_text.delete(1.0, tk.END)
        self.answer_text.insert(1.0, f"Error computing answer: {error}")
        self.status_label.config(text="Error")
    
    def run_code(self):
        """Run the current code with instrumentation"""
        if not self.current_source:
            messagebox.showwarning("Warning", "No code to run")
            return
        
        self.status_label.config(text="Running code...")
        self.root.update()
        
        try:
            # Clear previous trace
            self.tracer.clear()
            
            # Execute instrumented code
            exec_instrumented(self.current_source)
            
            stats = self.tracer.get_stats()
            self.status_label.config(
                text=f"Code executed. {stats['total_events']} events recorded."
            )
            
        except Exception as e:
            messagebox.showerror("Execution Error", f"Error running code: {e}")
            self.status_label.config(text="Execution failed")
    
    def clear_trace(self):
        """Clear the current trace"""
        self.tracer.clear()
        self.questions.clear()
        self.answers.clear()
        self.questions_listbox.delete(0, tk.END)
        self.answer_text.delete(1.0, tk.END)
        self.status_label.config(text="Trace cleared")
    
    def save_trace(self):
        """Save the current trace to a file"""
        filename = filedialog.asksaveasfilename(
            title="Save Trace",
            defaultextension=".pkl",
            filetypes=[("Pickle files", "*.pkl"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                self.tracer.save_trace(filename)
                self.status_label.config(text=f"Trace saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save trace: {e}")
    
    def load_trace(self):
        """Load a trace from a file"""
        filename = filedialog.askopenfilename(
            title="Load Trace",
            filetypes=[("Pickle files", "*.pkl"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                self.tracer.load_trace(filename)
                stats = self.tracer.get_stats()
                self.status_label.config(
                    text=f"Trace loaded. {stats['total_events']} events."
                )
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load trace: {e}")
    
    def show_trace_stats(self):
        """Show trace statistics"""
        stats = self.tracer.get_stats()
        
        stats_text = f"""
Trace Statistics:
- Total events: {stats['total_events']}
- Files traced: {stats['files_traced']}
- Time span: {stats['time_span']:.2f} seconds

Event types:
"""
        
        for event_type, count in stats['event_types'].items():
            stats_text += f"- {event_type}: {count}\n"
        
        messagebox.showinfo("Trace Statistics", stats_text)
    
    def run(self):
        """Start the UI"""
        self.root.mainloop()


class VariableValueDialog:
    """Dialog for asking about variable values"""
    
    def __init__(self, parent, asker: QuestionAsker, filename: str, line_no: int):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Ask about Variable Value")
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # Variable name
        ttk.Label(self.dialog, text="Variable name:").pack(pady=5)
        self.var_name_entry = ttk.Entry(self.dialog, width=40)
        self.var_name_entry.pack(pady=5)
        
        # Value
        ttk.Label(self.dialog, text="Value:").pack(pady=5)
        self.value_entry = ttk.Entry(self.dialog, width=40)
        self.value_entry.pack(pady=5)
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.LEFT, padx=5)
        
        self.asker = asker
        self.filename = filename
        self.line_no = line_no
        
        # Focus on first entry
        self.var_name_entry.focus_set()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def ok_clicked(self):
        """Handle OK button click"""
        var_name = self.var_name_entry.get().strip()
        value_str = self.value_entry.get().strip()
        
        if not var_name:
            messagebox.showwarning("Warning", "Please enter a variable name")
            return
        
        if not value_str:
            messagebox.showwarning("Warning", "Please enter a value")
            return
        
        # Try to evaluate the value
        try:
            value = eval(value_str)
        except:
            # If evaluation fails, treat as string
            value = value_str
        
        self.result = self.asker.why_did_variable_have_value(
            var_name, value, self.filename, self.line_no
        )
        self.dialog.destroy()
    
    def cancel_clicked(self):
        """Handle Cancel button click"""
        self.dialog.destroy()


def main():
    """Main entry point"""
    app = WhylineUI()
    app.run()


if __name__ == "__main__":
    main()