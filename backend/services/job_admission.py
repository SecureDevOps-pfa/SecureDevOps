import json
import time
from pathlib import Path

from validators.structure_validator import validate_structure


def admit_job(
    *,
    job_dir: Path,
    source_dir: Path,
    stack: dict,
    versions: dict,
    pipeline: dict,
):
    contract = Path("contracts/spring-boot-maven.json")

    validation = validate_structure(source_dir, contract)

    if validation.status == "REFUSED":
        raise ValueError(validation.errors)

    metadata = {
        "job_id": job_dir.name,
        "status": validation.status,
        "stack": stack,
        "versions": versions,
        "pipeline": pipeline,
        "warnings": validation.warnings,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    (job_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    return metadata
