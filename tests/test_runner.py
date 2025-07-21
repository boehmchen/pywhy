"""
Test runner for Python Whyline test suite
"""

import unittest
import sys
import os
import time
from io import StringIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import all test modules
from test_core_tracing import TestCoreTracing
from test_ast_instrumentation import TestASTInstrumentation
from test_question_system import TestQuestionSystem
from test_edge_cases import TestEdgeCases
from test_cli_integration import TestCLIIntegration, TestCLICommandLine
from test_performance import TestPerformance


class ColoredTextTestResult(unittest.TextTestResult):
    """Custom test result class with colored output"""
    
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.success_count = 0
        self.verbosity = verbosity
    
    def addSuccess(self, test):
        super().addSuccess(test)
        self.success_count += 1
        if self.verbosity > 1:
            self.stream.write("✅ ")
            self.stream.write(str(test))
            self.stream.writeln(" ... ok")
    
    def addError(self, test, err):
        super().addError(test, err)
        if self.verbosity > 1:
            self.stream.write("❌ ")
            self.stream.write(str(test))
            self.stream.writeln(" ... ERROR")
    
    def addFailure(self, test, err):
        super().addFailure(test, err)
        if self.verbosity > 1:
            self.stream.write("❌ ")
            self.stream.write(str(test))
            self.stream.writeln(" ... FAIL")
    
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        if self.verbosity > 1:
            self.stream.write("⚠️  ")
            self.stream.write(str(test))
            self.stream.writeln(f" ... skipped ({reason})")


class TestSuite:
    """Main test suite runner"""
    
    def __init__(self, verbosity=2):
        self.verbosity = verbosity
        self.test_classes = [
            TestCoreTracing,
            TestASTInstrumentation,
            TestQuestionSystem,
            TestEdgeCases,
            TestCLIIntegration,
            TestCLICommandLine,
            TestPerformance
        ]
    
    def create_test_suite(self, test_categories=None):
        """Create test suite with specified categories"""
        suite = unittest.TestSuite()
        
        # Define test categories
        categories = {
            'core': [TestCoreTracing, TestASTInstrumentation],
            'questions': [TestQuestionSystem],
            'edge_cases': [TestEdgeCases],
            'cli': [TestCLIIntegration, TestCLICommandLine],
            'performance': [TestPerformance],
            'all': self.test_classes
        }
        
        # Default to all tests if no categories specified
        if test_categories is None:
            test_categories = ['all']
        
        # Add tests from specified categories
        classes_to_test = set()
        for category in test_categories:
            if category in categories:
                classes_to_test.update(categories[category])
            else:
                print(f"⚠️  Unknown test category: {category}")
        
        # Create test suite
        for test_class in classes_to_test:
            tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
            suite.addTests(tests)
        
        return suite
    
    def run_tests(self, test_categories=None, failfast=False):
        """Run the test suite"""
        print("🧪 PYTHON WHYLINE TEST SUITE")
        print("=" * 50)
        
        # Create test suite
        suite = self.create_test_suite(test_categories)
        
        # Count total tests
        total_tests = suite.countTestCases()
        print(f"Running {total_tests} tests...")
        print()
        
        # Run tests
        runner = unittest.TextTestRunner(
            verbosity=self.verbosity,
            failfast=failfast,
            resultclass=ColoredTextTestResult
        )
        
        start_time = time.time()
        result = runner.run(suite)
        end_time = time.time()
        
        # Print summary
        self.print_summary(result, end_time - start_time)
        
        return result
    
    def print_summary(self, result, execution_time):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        total_tests = result.testsRun
        successes = result.success_count if hasattr(result, 'success_count') else (
            total_tests - len(result.failures) - len(result.errors) - len(result.skipped)
        )
        failures = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped)
        
        print(f"Total tests run: {total_tests}")
        print(f"✅ Successes: {successes}")
        print(f"❌ Failures: {failures}")
        print(f"❌ Errors: {errors}")
        print(f"⚠️  Skipped: {skipped}")
        print(f"⏱️  Execution time: {execution_time:.2f}s")
        
        # Calculate success rate
        if total_tests > 0:
            success_rate = (successes / total_tests) * 100
            print(f"📈 Success rate: {success_rate:.1f}%")
        
        # Print detailed failure/error information
        if failures:
            print("\n❌ FAILURES:")
            for test, traceback in result.failures:
                print(f"  • {test}: {traceback.split('AssertionError: ')[-1].strip()}")
        
        if errors:
            print("\n❌ ERRORS:")
            for test, traceback in result.errors:
                print(f"  • {test}: {traceback.split('\\n')[-2].strip()}")
        
        # Overall result
        print("\n" + "=" * 50)
        if failures == 0 and errors == 0:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Python Whyline implementation is working correctly")
        else:
            print(f"⚠️  {failures + errors} tests failed")
            print("❌ Implementation needs attention")
        
        print("=" * 50)


def run_specific_test(test_class_name, test_method_name=None):
    """Run a specific test class or method"""
    # Map test names to classes
    test_classes = {
        'core': TestCoreTracing,
        'ast': TestASTInstrumentation,
        'questions': TestQuestionSystem,
        'edge': TestEdgeCases,
        'cli': TestCLIIntegration,
        'cli_cmd': TestCLICommandLine,
        'performance': TestPerformance
    }
    
    if test_class_name not in test_classes:
        print(f"❌ Unknown test class: {test_class_name}")
        print(f"Available classes: {list(test_classes.keys())}")
        return False
    
    test_class = test_classes[test_class_name]
    
    if test_method_name:
        # Run specific test method
        suite = unittest.TestSuite()
        suite.addTest(test_class(test_method_name))
    else:
        # Run all tests in class
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
    
    runner = unittest.TextTestRunner(verbosity=2, resultclass=ColoredTextTestResult)
    result = runner.run(suite)
    
    return len(result.failures) == 0 and len(result.errors) == 0


def main():
    """Main entry point for test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Python Whyline Test Runner')
    parser.add_argument('--category', '-c', action='append', 
                       help='Test category to run (core, questions, edge_cases, cli, performance, all)')
    parser.add_argument('--failfast', '-f', action='store_true',
                       help='Stop on first failure')
    parser.add_argument('--verbose', '-v', action='count', default=1,
                       help='Increase verbosity')
    parser.add_argument('--specific', '-s', nargs='+',
                       help='Run specific test: class_name [method_name]')
    
    args = parser.parse_args()
    
    if args.specific:
        # Run specific test
        if len(args.specific) == 1:
            success = run_specific_test(args.specific[0])
        elif len(args.specific) == 2:
            success = run_specific_test(args.specific[0], args.specific[1])
        else:
            print("❌ Invalid specific test format. Use: class_name [method_name]")
            return 1
        
        return 0 if success else 1
    
    # Run test suite
    suite = TestSuite(verbosity=args.verbose)
    result = suite.run_tests(args.category, args.failfast)
    
    # Return appropriate exit code
    return 0 if (len(result.failures) == 0 and len(result.errors) == 0) else 1


if __name__ == '__main__':
    sys.exit(main())