# SecureDevOps Backend — Quick Architecture + Endpoints

This document summarizes the **backend** code: endpoints, what they accept/produce, and how the main Python modules work together.
(Does not analyze workspaces execution environment beyond what backend actually creates.)

---

## 1) Backend entrypoint

### `backend/app.py`
Runs the web API (Flask). Defines the REST endpoints under `/api/...` and delegates almost all work to `services/job_orchestrator.py`.

---

## 2) API Endpoints (what they take / what they produce)

> Source: `backend/app.py` (calls into `JobOrchestrator`)

### `POST /api/jobs/upload`
**Purpose:** Create a job workspace from a **ZIP upload**.

**Request**
- `Content-Type: multipart/form-data`
- Form field: `file` (the uploaded zip archive)

**Backend behavior**
- Validates “is it a real zip signature” and applies safety limits (counts/sizes/depth, no symlinks, no traversal, blocked extensions).
- Creates a job workspace on disk.
- Extracts ZIP into `workspaces/<job-id>/source/`.
- Runs structure validation against a contract (Spring Boot Maven contract).
- Writes `workspaces/<job-id>/metadata.json`.

**Response (typical)**
- JSON metadata including:
  - `job_id`
  - `status` (`ACCEPTED`, `ACCEPTED_WITH_ISSUES`, or refused triggers error)
  - `execution_state: "QUEUED"`
  - `stack`, `versions`, `pipeline`
  - `warnings`
  - `created_at`

**Errors**
- Validation refused → raises `ValueError(errors)` and the endpoint returns an error response.
- Zip safety violations (too large, too many files, traversal attempt, etc.) → error response.

---

### `POST /api/jobs/github`
**Purpose:** Create a job workspace by **cloning a public GitHub repository**.

**Request**
- `Content-Type: application/json`
- Body fields (as used by orchestrator flow):
  - `repo_url` (must match `https://github.com/<owner>/<repo>`)
  - `stack` (dict)
  - `versions` (dict)
  - `pipeline` (dict)

**Backend behavior**
- Validates the GitHub URL format.
- Creates a job workspace on disk.
- `git clone` into `workspaces/<job-id>/source/`.
- Deletes `.git/`.
- Runs repository safety scan (limits on files/bytes/depth + dangerous extensions).
- Runs structure validation (contract check).
- Writes `workspaces/<job-id>/metadata.json`.

**Response**
- Same “metadata.json-like” structure as upload.

**Errors**
- Invalid URL, clone failure, safety scan fail, structure refused → error response and the workspace is cleaned up.

---

## 3) What the backend *creates on disk*

### Actual implemented output (current backend)
For each job:
- `workspaces/<job-id>/`
- `workspaces/<job-id>/source/`  ← extracted/cloned project is placed here
- `workspaces/<job-id>/metadata.json` ← written by admission step

### What docs/pipelines describe (not created by backend currently)
Docs and pipeline scripts often assume a layout like:
- `app/` (project)
- `reports/`
- `pipelines/`
- `metadata/project.json`

That layout is **not assembled by backend code** today. Backend produces `source/` and a root `metadata.json`.

---

## 4) Main Python modules and how they work together

### A) Orchestration layer

#### `backend/services/job_orchestrator.py`
**Role:** The main coordinator for both endpoints. It implements “create job from input → admit job”.

High-level flow:
1. Create workspace (`workspace_service.create_workspace`)
2. Put user input into `workspace.source_dir`:
   - ZIP path → `zip_input_service.handle_zip_input`
   - GitHub path → `repo_input_service.clone_github_repository`
3. Admission:
   - `job_admission.admit_job(...)` validates structure and writes `metadata.json`
4. On any failure: cleanup via `workspace_service.cleanup_workspace(workspace)`

---

### B) Workspace management

#### `backend/services/workspace_service.py`
**Role:** Owns the filesystem job directory lifecycle.

- `create_workspace(workspaces_root="workspaces")`:
  - generates a job id
  - creates:
    - `workspaces/<job-id>/`
    - `workspaces/<job-id>/source/`
  - returns a `Workspace` object:
    - `job_id`
    - `job_dir`
    - `source_dir`

- `cleanup_workspace(workspace)`:
  - removes `workspace.job_dir` recursively

This is the module that **controls workspace creation**.

---

### C) Admission + Metadata

#### `backend/services/job_admission.py`
**Role:** Validate the extracted/cloned project and persist job metadata.

What it does (from the file you shared):
1. Selects a contract file:
   - `contracts/spring-boot-maven.json`
2. Validates structure:
   - `validators.structure_validator.validate_structure(workspace.source_dir, contract)`
3. If refused:
   - raises `ValueError(validation.errors)`
4. Otherwise writes:
   - `workspaces/<job-id>/metadata.json`

Metadata includes:
- `job_id`
- `status` (from validation)
- `execution_state: "QUEUED"`
- user-provided `stack`, `versions`, `pipeline`
- any `warnings`
- timestamp `created_at`

---

### D) Input services (how code gets into `source/`)

#### `backend/services/zip_input_service.py`
**Role:** Safely handle zip uploads.

Key responsibilities:
- zip signature verification
- safe extraction path handling (prevents `../` traversal)
- reject symlinks
- enforce limits: max files, max total bytes, max depth
- block dangerous extensions
- optional “single top-level folder normalization” so the project lands directly under `source/`

Output: fully populated `workspace.source_dir`.

#### `backend/services/repo_input_service.py`
**Role:** Safely clone GitHub repositories.

Key responsibilities:
- validate URL shape
- `git clone` with conservative flags (depth/branch/no-tags)
- remove `.git`
- scan repo content for limits + dangerous extensions

Output: fully populated `workspace.source_dir`.

---

### E) Structure validation

#### `backend/validators/structure_validator.py`
**Role:** Enforce “project contract” requirements.

It reads a contract JSON (e.g. Spring Boot Maven) and checks:
- required paths exist
- required file patterns exist (glob checks)
- simple semantic checks (example: expects a `@SpringBootApplication` in exactly one `.java` file)
- non-fatal issues become warnings

Returns a `ValidationResult` with:
- `status`: `ACCEPTED` / `ACCEPTED_WITH_ISSUES` / `REFUSED`
- `errors`
- `warnings`

---

### F) Safety utilities

#### `backend/utils/zip_safety.py`
ZIP hardening utilities (signature check, safe paths, reject symlinks, etc.).

#### `backend/utils/content_safety.py`
Blocks dangerous extensions (executables, bytecode, archives, etc.).

#### `backend/utils/repo_safety.py`
Scans cloned repos for:
- file count limits
- byte limits
- depth limits
- blocked extensions

---

## 5) How the pieces fit (one diagram)

```
Client
  ├─ POST /api/jobs/upload (zip)
  │    app.py
  │      → JobOrchestrator.create_job_from_zip_input
  │          → workspace_service.create_workspace
  │          → zip_input_service.handle_zip_input  (extract → source/)
  │          → job_admission.admit_job            (validate + metadata.json)
  │          → return metadata response
  │
  └─ POST /api/jobs/github (repo_url)
       app.py
         → JobOrchestrator.create_job_from_repo_input
             → workspace_service.create_workspace
             → repo_input_service.clone_github_repository (clone → source/)
             → job_admission.admit_job                    (validate + metadata.json)
             → return metadata response
```

---

## 6) Notes / suspected redundant file

### `backend/services/github_service.py`
Looks like an older implementation that also clones GitHub repos + writes metadata, but current endpoint flow appears to use:
- `repo_input_service.py` + `workspace_service.py` + `job_admission.py`.

So `github_service.py` is likely unused unless imported elsewhere.

---

## 7) Where “app/ reports/ metadata.js” would be controlled
- Backend currently controls only:
  - `workspaces/<job-id>/source/`
  - `workspaces/<job-id>/metadata.json`
- If you want a runtime layout like `app/`, `reports/`, `metadata/`, that code does **not exist yet** in backend services.
  - It would likely belong in `workspace_service` (workspace layout creation) and/or a new “workspace layout builder” step inside