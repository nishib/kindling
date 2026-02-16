#!/usr/bin/env python3
"""Test the ERP filter with real-world examples from the screenshots."""

from competitor_sources import _is_erp_related

# Test cases from the screenshots
test_cases = [
    {
        "name": "Microplastics article (should REJECT)",
        "title": "New research reveals the everyday item shedding thousands of microplastics",
        "content": "Rillet announced: New research reveals the everyday item shedding thousands of microplastics. Environmental study shows plastic particles...",
        "expected": False
    },
    {
        "name": "DualEntry earnings report (should REJECT)",
        "title": "NIS Management Limited Reports Q3 FY26 Revenue of Rs 103.77 Cr; 9M Revenue Stands at Rs 318.66 Cr",
        "content": "DualEntry announced: NIS Management Limited Reports Q3 FY26 Revenue of Rs 103.77 Cr; 9M Revenue Stands at Rs 318.66 Cr. Financial results quarterly earnings...",
        "expected": False
    },
    {
        "name": "NetSuite ERP feature (should ACCEPT)",
        "title": "NetSuite Launches AI-Powered Revenue Recognition for SaaS Companies",
        "content": "NetSuite today announced a new AI-powered revenue recognition feature that automatically applies ASC 606 rules to subscription contracts. The new module integrates with their general ledger and financial close processes.",
        "expected": True
    },
    {
        "name": "SAP accounting update (should ACCEPT)",
        "title": "SAP S/4HANA Enhances Financial Close Automation",
        "content": "SAP released updates to S/4HANA ERP system including enhanced financial close automation, real-time general ledger updates, and improved accounts payable workflows.",
        "expected": True
    },
    {
        "name": "Rillet product announcement (should ACCEPT)",
        "title": "Rillet Introduces Multi-Entity Consolidation for Accounting Teams",
        "content": "Rillet ERP accounting software now supports multi-entity consolidation, allowing finance teams to manage multiple subsidiaries in a single general ledger system.",
        "expected": True
    },
    {
        "name": "Generic company news (should REJECT)",
        "title": "Oracle Acquires Another Company for $2B",
        "content": "Oracle Corporation announced acquisition of Tech Startup for $2 billion. Stock price rises. Market cap increases.",
        "expected": False
    },
    {
        "name": "Training course (should REJECT)",
        "title": "Learn NetSuite ERP: Complete Course from Zero to Expert",
        "content": "Online course certification tutorial for NetSuite ERP software. Learn accounting software from scratch.",
        "expected": False
    }
]

def run_tests():
    """Run all test cases and report results."""
    print("\n" + "="*80)
    print("TESTING ERP FILTER WITH REAL-WORLD EXAMPLES")
    print("="*80 + "\n")

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        result = _is_erp_related(test["title"], test["content"])
        expected = test["expected"]
        status = "✅ PASS" if result == expected else "❌ FAIL"

        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"{i}. {test['name']}")
        print(f"   Title: {test['title'][:70]}...")
        if i == 5 and result != expected:  # Debug test #5
            print(f"   Content: {test['content'][:100]}...")
        print(f"   Expected: {'ACCEPT' if expected else 'REJECT'}")
        print(f"   Got:      {'ACCEPT' if result else 'REJECT'}")
        print(f"   {status}\n")

    print("="*80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("="*80 + "\n")

    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
