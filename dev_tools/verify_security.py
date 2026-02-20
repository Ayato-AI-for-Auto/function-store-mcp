import os
import sys

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from mcp_core.engine.quality_gate import QualityGate


def verify_security_gate():
    gate = QualityGate()

    print("--- Test 1: Secure Code ---")
    secure_code = """
def hello_world():
    print('Hello, safe world!')
    return True
"""
    report = gate.check_score_only(
        "safe_func", secure_code, "A safe function", ["requests>=2.31.0"]
    )
    print(f"Score: {report['final_score']}")
    print(f"Reliability: {report['reliability']}")
    # print(json.dumps(report, indent=2))

    print("\n--- Test 2: Insecure Code (Bandit High Severity) ---")
    insecure_code = """
import os
def dangerous(cmd):
    os.system(cmd) # High severity finding in Bandit
    eval('1+1')    # Medium/High severity
"""
    report = gate.check_score_only(
        "dangerous_func", insecure_code, "A dangerous function"
    )
    print(f"Score: {report['final_score']}")
    print(f"Reliability: {report['reliability']}")
    print(f"Bandit Findings: {report['security']['bandit']['findings']}")

    print("\n--- Test 3: Vulnerable Dependencies (Safety) ---")
    # Note: This might skip if safety is not installed or data is missing
    code = "def test(): pass"
    report = gate.check_score_only(
        "vuln_dep_func", code, "Vulnerable dep", ["requests<2.20.0"]
    )
    print(f"Score: {report['final_score']}")
    print(f"Safety Findings: {report['security']['safety']['findings']}")


if __name__ == "__main__":
    verify_security_gate()
