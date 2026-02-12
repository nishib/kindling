"""Scenario engine package for simulated ERP scenarios.

This package intentionally keeps the core scenario logic (templates,
state machine, rules, synthetic data) pure and framework-agnostic so
it can be exercised from tests and the FastAPI router.
"""

from . import templates, state_machine, rules_engine, synthetic_data, coach  # noqa: F401

