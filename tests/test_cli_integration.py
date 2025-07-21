"""
Integration tests for CLI functionality
"""

import unittest
import sys
import os
import subprocess
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from python_whyline.cli import WhylineCLI
from python_whyline import get_tracer, QuestionAsker


class TestCLIIntegration(unittest.TestCase):
    """Test CLI integration functionality"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.cli = WhylineCLI()
        self.test_code = '''
def simple_function(x, y):
    result = x + y
    return result

a = 10
b = 20
c = simple_function(a, b)
print(f"Result: {c}")
'''
    
    def test_cli_creation(self):
        """Test CLI creation and initialization"""
        self.assertIsNotNone(self.cli, "CLI should be created")
        self.assertIsNotNone(self.cli.tracer, "CLI should have tracer")
        self.assertIsNotNone(self.cli.asker, "CLI should have question asker")
        self.assertEqual(self.cli.current_code, "", "CLI should start with empty code")
        self.assertEqual(self.cli.current_filename, "<interactive>", "CLI should start with interactive filename")
    
    def test_code_loading(self):
        """Test code loading functionality"""
        self.cli.current_code = self.test_code
        self.cli.current_filename = "<test>"
        
        self.assertEqual(self.cli.current_code, self.test_code, "Code should be loaded")
        self.assertEqual(self.cli.current_filename, "<test>", "Filename should be set")
    
    def test_run_command(self):
        """Test run command functionality"""
        self.cli.current_code = self.test_code
        self.cli.current_filename = "<test>"
        
        # Test run command
        self.cli.do_run("")
        
        # Should have recorded events
        self.assertGreater(len(self.cli.tracer.events), 0, "Run command should record events")
        
        # Should have assignment events
        assign_events = [e for e in self.cli.tracer.events if e.event_type == 'assign']
        self.assertGreater(len(assign_events), 0, "Should record assignment events")
    
    def test_question_creation(self):
        """Test question creation through CLI"""
        self.cli.current_code = self.test_code
        self.cli.current_filename = "<test>"
        self.cli.do_run("")
        
        # Test question creation
        question = self.cli.asker.why_did_variable_have_value('c', 30, "<test>")
        answer = question.get_answer()
        
        self.assertIsNotNone(answer, "Should create and answer questions")
        self.assertIn("line", str(answer).lower(), "Answer should mention line number")
    
    def test_clear_command(self):
        """Test clear command functionality"""
        self.cli.current_code = self.test_code
        self.cli.do_run("")
        
        # Should have events
        self.assertGreater(len(self.cli.tracer.events), 0, "Should have events before clear")
        
        # Clear should remove events
        self.cli.do_clear("")
        self.assertEqual(len(self.cli.tracer.events), 0, "Clear should remove all events")
        self.assertEqual(len(self.cli.questions), 0, "Clear should remove all questions")
    
    def test_trace_command(self):
        """Test trace statistics command"""
        self.cli.current_code = self.test_code
        self.cli.do_run("")
        
        # Should be able to get trace statistics
        stats = self.cli.tracer.get_stats()
        self.assertGreater(stats['total_events'], 0, "Should have trace statistics")
        self.assertIn('event_types', stats, "Should have event types in statistics")
    
    def test_file_loading(self):
        """Test file loading functionality"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(self.test_code)
            temp_filename = f.name
        
        try:
            # Test file loading
            self.cli.do_load(temp_filename)
            
            self.assertEqual(self.cli.current_code, self.test_code, "Should load file content")
            self.assertEqual(self.cli.current_filename, temp_filename, "Should set filename")
            
        finally:
            # Clean up
            os.unlink(temp_filename)
    
    def test_file_loading_error(self):
        """Test file loading error handling"""
        # Test with non-existent file
        self.cli.do_load("nonexistent_file.py")
        
        # Should not crash and should keep existing state
        self.assertEqual(self.cli.current_code, "", "Should not change code on error")
        self.assertEqual(self.cli.current_filename, "<interactive>", "Should not change filename on error")
    
    def test_run_without_code(self):
        """Test run command without code"""
        # Should handle empty code gracefully
        self.cli.do_run("")
        
        # Should not crash
        self.assertEqual(len(self.cli.tracer.events), 0, "Should not record events without code")
    
    def test_main_code_block_handling(self):
        """Test handling of if __name__ == '__main__' blocks"""
        code_with_main = '''
def test_function():
    return 42

if __name__ == "__main__":
    result = test_function()
    print(result)
'''
        
        self.cli.current_code = code_with_main
        self.cli.do_run("")
        
        # Should execute main block and record events
        self.assertGreater(len(self.cli.tracer.events), 0, "Should execute main block")
        
        # Should have assignment events from main block
        assign_events = [e for e in self.cli.tracer.events if e.event_type == 'assign']
        self.assertGreater(len(assign_events), 0, "Should record events from main block")
    
    def test_interactive_mode_simulation(self):
        """Test interactive mode simulation"""
        # Simulate interactive code entry
        test_lines = [
            "x = 10",
            "y = 20", 
            "z = x + y",
            "print(z)"
        ]
        
        self.cli.current_code = '\n'.join(test_lines)
        self.cli.current_filename = "<interactive>"
        
        # Run the code
        self.cli.do_run("")
        
        # Should record events for interactive code
        self.assertGreater(len(self.cli.tracer.events), 0, "Should record events for interactive code")
    
    def test_error_handling_in_cli(self):
        """Test error handling in CLI commands"""
        # Test with invalid code
        self.cli.current_code = "invalid syntax !!!"
        self.cli.do_run("")
        
        # Should not crash CLI
        self.assertEqual(len(self.cli.tracer.events), 0, "Should not record events for invalid code")
        
        # Should still be able to run valid code afterwards
        self.cli.current_code = "x = 1"
        self.cli.do_run("")
        
        assign_events = [e for e in self.cli.tracer.events if e.event_type == 'assign']
        self.assertGreater(len(assign_events), 0, "Should work after error")


class TestCLICommandLine(unittest.TestCase):
    """Test CLI command line interface"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.example_file = os.path.join(self.project_root, 'example.py')
        
        # Create example file if it doesn't exist
        if not os.path.exists(self.example_file):
            with open(self.example_file, 'w') as f:
                f.write('''
def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)

if __name__ == "__main__":
    result = fibonacci(5)
    print(f"Fibonacci(5) = {result}")
''')
    
    def test_cli_basic_execution(self):
        """Test basic CLI execution"""
        # Test CLI with simple commands
        commands = ["run", "quit"]
        input_data = "\n".join(commands)
        
        try:
            result = subprocess.run(
                [sys.executable, os.path.join(self.project_root, "run_cli.py"), self.example_file],
                input=input_data,
                text=True,
                capture_output=True,
                timeout=10,
                cwd=self.project_root
            )
            
            # Should not crash
            self.assertEqual(result.returncode, 0, f"CLI should not crash: {result.stderr}")
            
            # Should show execution completed
            self.assertIn("Execution completed", result.stdout, "Should show execution completed")
            
        except subprocess.TimeoutExpired:
            self.fail("CLI took too long to execute")
        except FileNotFoundError:
            self.skipTest("CLI script not found")
    
    def test_cli_question_interaction(self):
        """Test CLI question interaction"""
        # Test CLI with question commands
        commands = [
            "run",
            "ask",
            "2",      # Why did line N execute?
            "2",      # Line number
            "quit"
        ]
        input_data = "\n".join(commands)
        
        try:
            result = subprocess.run(
                [sys.executable, os.path.join(self.project_root, "run_cli.py"), self.example_file],
                input=input_data,
                text=True,
                capture_output=True,
                timeout=10,
                cwd=self.project_root
            )
            
            # Should not crash
            self.assertEqual(result.returncode, 0, f"CLI should not crash: {result.stderr}")
            
            # Should show question and answer
            self.assertIn("Question:", result.stdout, "Should show question")
            self.assertIn("Answer:", result.stdout, "Should show answer")
            
        except subprocess.TimeoutExpired:
            self.fail("CLI took too long to execute")
        except FileNotFoundError:
            self.skipTest("CLI script not found")


if __name__ == '__main__':
    unittest.main()