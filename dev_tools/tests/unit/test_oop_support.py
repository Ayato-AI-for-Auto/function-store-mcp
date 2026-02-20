import pytest
from mcp_core.core.database import init_db
from mcp_core.engine.logic import do_get_impl, do_save_impl


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_save_and_retrieve_class():
    """Verify that a Python Class can be saved and retrieved as-is."""
    class_code = """
class DataCarrier:
    def __init__(self, value: int):
        self.value = value
    
    def double(self) -> int:
        return self.value * 2
"""
    name = "DataCarrier"
    # Save Class
    save_res = do_save_impl(
        asset_name=name,
        code=class_code,
        description="A simple data carrier class",
        skip_test=True,
    )
    assert "SUCCESS" in save_res

    # Retrieve and compare
    retrieved_code = do_get_impl(name)
    assert class_code.strip() == retrieved_code.strip()


def test_class_linting():
    """Verify that Ruff correctly detects errors within class methods."""
    from mcp_core.engine.quality_gate import QualityGate

    qgate = QualityGate()

    # Bad Class (unused import inside, bad spacing)
    bad_class_code = """
import os  # Unused
class BadClass:
    def method(self):
        unused_var = 10
        return "hello"
"""
    # Force check
    report = qgate.check_score_only("BadClass", bad_class_code, "desc")

    assert report["final_score"] < 100
    # Check if linter caught the unused import/variable
    errors = " ".join(report["linter"]["errors"])
    assert "os" in errors or "unused_var" in errors


def test_class_with_inheritance():
    """Verify that classes with inheritance are supported."""
    oop_code = """
class Base:
    def greet(self):
        return "hello"

class Derived(Base):
    def greet(self):
        return super().greet() + " world"
"""
    name = "DerivedClass"
    save_res = do_save_impl(
        asset_name=name, code=oop_code, description="Inheritance test", skip_test=True
    )
    assert "SUCCESS" in save_res

    retrieved = do_get_impl(name)
    assert "Derived(Base)" in retrieved
