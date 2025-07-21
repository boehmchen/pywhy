#!/usr/bin/env python3
"""
Simple test runner script for Python Whyline tests
"""

import sys
import os
import subprocess

def main():
    """Run all Python Whyline tests"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_runner = os.path.join(script_dir, 'test_runner.py')
    
    print("🧪 Running Python Whyline Test Suite")
    print("=" * 50)
    
    # Run different test categories
    test_categories = [
        ('core', 'Core functionality tests'),
        ('questions', 'Question system tests'),
        ('edge_cases', 'Edge case tests'),
        ('cli', 'CLI integration tests')
    ]
    
    all_passed = True
    
    for category, description in test_categories:
        print(f"\n📋 {description}")
        print("-" * 30)
        
        try:
            result = subprocess.run([
                sys.executable, test_runner, '--category', category
            ], cwd=script_dir, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✅ {category.upper()} TESTS PASSED")
            else:
                print(f"❌ {category.upper()} TESTS FAILED")
                print(result.stdout)
                print(result.stderr)
                all_passed = False
                
        except subprocess.TimeoutExpired:
            print(f"⏱️  {category.upper()} TESTS TIMED OUT")
            all_passed = False
        except Exception as e:
            print(f"❌ {category.upper()} TESTS ERROR: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL TEST CATEGORIES PASSED!")
        print("✅ Python Whyline is working correctly")
    else:
        print("⚠️  Some test categories failed")
        print("❌ Check output above for details")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())