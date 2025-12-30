import json
from pathlib import Path
import glob

class ValidationResult:
    def __init__(self):
        self.errors = []
        self.warnings = []

    @property
    def status(self):
        if self.errors:
            return "REFUSED"
        if self.warnings:
            return "ACCEPTED_WITH_ISSUES"
        return "ACCEPTED"


def validate_structure(source_dir: Path, contract_path: Path) -> ValidationResult:
    result = ValidationResult()
    contract = json.loads(contract_path.read_text())

    # --- Required paths ---
    for rel_path in contract.get("required_paths", []):
        if not (source_dir / rel_path).exists():
            result.errors.append(f"Missing required path: {rel_path}")

    # --- Required files ---
    for rule in contract.get("required_files", []):
        matches = glob.glob(str(source_dir / rule["pattern"]), recursive=True)
        if len(matches) < rule.get("min_count", 1):
            result.errors.append(
                f"Expected at least {rule['min_count']} file(s) matching {rule['pattern']}"
            )

    # --- Semantic checks ---
    for check in contract.get("semantic_checks", []):
        if check["type"] == "contains_text":
            count = 0
            for file in source_dir.rglob("*.java"):
                if check["value"] in file.read_text(errors="ignore"):
                    count += 1

            if check.get("exactly_one") and count != 1:
                result.errors.append(
                    f"Expected exactly one occurrence of {check['value']}, found {count}"
                )

    # --- Optional paths ---
    for rel_path in contract.get("optional_paths", []):
        if not (source_dir / rel_path).exists():
            result.warnings.append(f"Optional path not found: {rel_path}")

    return result
