"""
Unit tests for question and answer system
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from python_whyline import get_tracer, exec_instrumented, QuestionAsker


class TestQuestionSystem(unittest.TestCase):
    """Test question and answer system functionality"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tracer = get_tracer()
        self.tracer.clear()
        
        # Execute test code with known behavior
        self.test_code = '''
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        if num > 0:
            total += num
    return total

def main():
    data = [1, -2, 3, 4, -5]
    result = calculate_sum(data)
    doubled = result * 2
    return doubled

final_result = main()
'''
        exec_instrumented(self.test_code)
        self.asker = QuestionAsker(self.tracer)
    
    def test_question_asker_creation(self):
        """Test QuestionAsker creation"""
        self.assertIsNotNone(self.asker, "QuestionAsker not created")
        self.assertEqual(self.asker.tracer, self.tracer, "Wrong tracer assigned")
    
    def test_why_did_variable_have_value(self):
        """Test 'why did variable have value' questions"""
        # Test known variable assignment
        question = self.asker.why_did_variable_have_value('final_result', 16)
        answer = question.get_answer()
        
        self.assertIsNotNone(answer, "No answer generated")
        self.assertIn("line", str(answer).lower(), "Answer should mention line number")
        self.assertTrue(len(answer.evidence) > 0, "No evidence provided")
    
    def test_why_did_line_execute(self):
        """Test 'why did line execute' questions"""
        question = self.asker.why_did_line_execute('<string>', 3)  # total = 0 line
        answer = question.get_answer()
        
        self.assertIsNotNone(answer, "No answer generated")
        self.assertIn("executed", str(answer).lower(), "Answer should mention execution")
    
    def test_why_didnt_line_execute(self):
        """Test 'why didn't line execute' questions"""
        question = self.asker.why_didnt_line_execute('<string>', 999)  # non-existent line
        answer = question.get_answer()
        
        self.assertIsNotNone(answer, "No answer generated")
        answer_text = str(answer).lower()
        self.assertTrue("never" in answer_text or "didn't" in answer_text, 
                       "Answer should mention non-execution")
    
    def test_why_did_function_return(self):
        """Test 'why did function return' questions"""
        question = self.asker.why_did_function_return('calculate_sum', 8)
        answer = question.get_answer()
        
        self.assertIsNotNone(answer, "No answer generated")
        # Should find the return event
        answer_text = str(answer).lower()
        self.assertTrue("line" in answer_text or "return" in answer_text, 
                       "Answer should mention return location")
    
    def test_question_with_filename_constraint(self):
        """Test questions with filename constraints"""
        question = self.asker.why_did_variable_have_value('data', [1, -2, 3, 4, -5], '<string>')
        answer = question.get_answer()
        
        self.assertIsNotNone(answer, "No answer generated with filename constraint")
    
    def test_question_with_line_constraint(self):
        """Test questions with line number constraints"""
        question = self.asker.why_did_variable_have_value('total', 0, '<string>', 3)
        answer = question.get_answer()
        
        self.assertIsNotNone(answer, "No answer generated with line constraint")
    
    def test_question_formatting(self):
        """Test that questions are formatted correctly"""
        q1 = self.asker.why_did_variable_have_value('x', 42)
        q2 = self.asker.why_did_line_execute('<string>', 5)
        q3 = self.asker.why_didnt_line_execute('<string>', 10)
        q4 = self.asker.why_did_function_return('func', 'value')
        
        # Check that questions don't have duplicate text
        self.assertNotIn("x x", str(q1), "Variable question has duplicate text")
        self.assertNotIn("line 5 line 5", str(q2), "Line execute question has duplicate text")
        self.assertNotIn("line 10 line 10", str(q3), "Line non-execute question has duplicate text")
        self.assertNotIn("func func", str(q4), "Function return question has duplicate text")
        
        # Check question marks
        self.assertTrue(str(q1).endswith("?"), "Variable question should end with ?")
        self.assertTrue(str(q2).endswith("?"), "Line execute question should end with ?")
        self.assertTrue(str(q3).endswith("?"), "Line non-execute question should end with ?")
        self.assertTrue(str(q4).endswith("?"), "Function return question should end with ?")
    
    def test_answer_evidence(self):
        """Test that answers provide evidence"""
        question = self.asker.why_did_variable_have_value('final_result', 16)
        answer = question.get_answer()
        
        self.assertIsNotNone(answer.evidence, "Answer should have evidence")
        self.assertGreater(len(answer.evidence), 0, "Evidence list should not be empty")
        
        # Check evidence structure
        for event in answer.evidence:
            self.assertTrue(hasattr(event, 'event_type'), "Evidence should have event_type")
            self.assertTrue(hasattr(event, 'lineno'), "Evidence should have lineno")
    
    def test_nonexistent_variable_question(self):
        """Test questions about non-existent variables"""
        question = self.asker.why_did_variable_have_value('nonexistent_var', 999)
        answer = question.get_answer()
        
        self.assertIsNotNone(answer, "Should get answer for non-existent variable")
        answer_text = str(answer).lower()
        self.assertTrue("no" in answer_text or "not found" in answer_text, 
                       "Answer should indicate variable not found")
    
    def test_question_caching(self):
        """Test that question answers are cached"""
        question = self.asker.why_did_variable_have_value('final_result', 16)
        
        # First call should compute answer
        answer1 = question.get_answer()
        
        # Second call should return cached answer
        answer2 = question.get_answer()
        
        self.assertIs(answer1, answer2, "Answer should be cached")


if __name__ == '__main__':
    unittest.main()