import json
import time
from pathlib import Path

from validators.structure_validator import validate_structure
from services.workspace_service import Workspace


def admit_job(
    *,
    workspace: Workspace,
    stack: dict,
    versions: dict,
    pipeline: dict,
):
    contract = Path("contracts/spring-boot-maven.json")

    validation = validate_structure(workspace.source_dir, contract)

    if validation.status == "REFUSED":
        raise ValueError(validation.errors)

    metadata = {
        "job_id": workspace.job_id,
        "status": validation.status,
        "execution_state": "QUEUED",
        "stack": stack,
        "versions": versions,
        "pipeline": pipeline,
        "warnings": validation.warnings,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    (workspace.job_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    return metadata