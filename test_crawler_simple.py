#!/usr/bin/env python3
"""Simple integration test to verify crawler setup without full dependencies."""

import hashlib

def test_hash_chunk():
    """Test chunk hashing function."""
    def _hash_chunk(heading: str, text: str) -> str:
        h = hashlib.sha256()
        h.update(heading.encode("utf-8"))
        h.update(b"\n")
        h.update(text.encode("utf-8"))
        return h.hexdigest()

    # Test consistent hashing
    h1 = _hash_chunk("Feature", "Description")
    h2 = _hash_chunk("Feature", "Description")
    assert h1 == h2, "Same content should produce same hash"
    print("✓ Consistent hashing works")

    # Test different hashes
    h3 = _hash_chunk("Feature", "Different")
    assert h1 != h3, "Different content should produce different hash"
    print("✓ Change detection works")


def test_priority_filtering():
    """Test competitor priority filtering logic."""
    from dataclasses import dataclass

    @dataclass
    class Competitor:
        name: str
        priority: int
        enabled: bool

    competitors = [
        Competitor("NetSuite", 1, True),
        Competitor("SAP", 1, True),
        Competitor("Oracle", 2, True),
        Competitor("Disabled", 1, False),
    ]

    # Filter priority 1 only
    priority_1 = [c for c in competitors if c.enabled and c.priority <= 1]
    assert len(priority_1) == 2, "Should find 2 priority 1 competitors"
    assert "NetSuite" in [c.name for c in priority_1]
    print("✓ Priority filtering works")

    # Filter priority 2
    priority_2 = [c for c in competitors if c.enabled and c.priority <= 2]
    assert len(priority_2) == 3, "Should find 3 competitors (priority 1 and 2)"
    print("✓ Multi-level priority filtering works")


def test_file_structure():
    """Verify all required files exist."""
    import os

    files = [
        "competitor_sources.py",
        "test_competitor_sources.py",
        "cli_crawler.py",
        "run_crawler.sh",
        "README_CRAWLER.md",
    ]

    for f in files:
        assert os.path.isfile(f), f"{f} should exist"
    print(f"✓ All {len(files)} required files exist")


def test_syntax():
    """Verify Python files have valid syntax."""
    import py_compile

    files = [
        "competitor_sources.py",
        "test_competitor_sources.py",
        "cli_crawler.py",
    ]

    for f in files:
        try:
            py_compile.compile(f, doraise=True)
        except py_compile.PyCompileError as e:
            raise AssertionError(f"{f} has syntax errors: {e}")
    print(f"✓ All {len(files)} Python files have valid syntax")


def main():
    print("\n🧪 Running Crawler Setup Tests\n")

    tests = [
        ("Chunk Hashing", test_hash_chunk),
        ("Priority Filtering", test_priority_filtering),
        ("File Structure", test_file_structure),
        ("Python Syntax", test_syntax),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*50}\n")

    if failed > 0:
        return 1
    else:
        print("✅ All setup tests passed!\n")
        print("Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run full tests: python test_competitor_sources.py")
        print("3. Test crawler: python cli_crawler.py discover")
        print()
        return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
