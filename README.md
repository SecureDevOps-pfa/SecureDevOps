# 1. Project Overview & Objectives

The objective of this project is to design a secure and extensible DevSecOps pipeline engine capable of analyzing software projects built with different frameworks and technologies.

The system accepts a project as a compressed archive or a GitHub/Dockerhub repository link, performs structural and security validation, and then selects the appropriate predefined pipeline based on the detected project characteristics .

Each pipeline executes build, testing, and security analysis stages within an **isolated environment.** All generated results are normalized and aggregated into a structured report intended to help development teams evaluate code quality and release readiness.

# 2. Global Workflow (End-to-End View)

- The user submits a project (compressed archive or repository link).
- The platform validates the input and performs an initial security assessment (e.g. archive bombs, invalid structures).
- Based on the detected technologies and user-selected options, an appropriate predefined pipeline is selected.
- The pipeline is executed within a dedicated and isolated execution environment.
- The pipeline execution is delegated to an isolated job runner, allowing the main API to remain responsive.
- Execution results and artifacts are collected and normalized.
- Once the job completes, all associated resources and environments are destroyed.

---

# 3. Phase 1 — User Input & Safety Validation

**Supported input types:** compressed archives, GitHub repositories, and DockerHub images (public repositories only).

### Threat Model for Untrusted Inputs

Submitted projects are considered untrusted by default. The platform focuses on mitigating a limited but critical set of risks, including:

- Archive-based attacks (e.g. decompression bombs, path traversal)
- Presence of executable or binary files
- Excessive resource usage (file count, size, depth)

This threat model is intentionally limited and aims to protect the execution environment rather than provide exhaustive security guarantees.

### Validation Strategy

Before any pipeline execution, the input is validated through a series of structural and security checks. Validation outcomes are classified as:

- **Hard failures**, which result in immediate rejection (e.g. security violations, unsupported structure/framework …)
- **Soft failures**, which indicate non-critical issues and may affect pipeline completeness (e.g. missing test files)

Based on this validation, each submission is assigned one of the following states:

- **ACCEPTED**
- **ACCEPTED_WITH_ISSUES** (e.g. no unit tests found, testing phase skipped)
- **REFUSED**

---

# 4. Phase 2 — Job Creation & Project Analysis

### Project Structure Detection & Input Handling

- The user submits project info through a form, specifying:
    - Input type: ZIP / GitHub / DockerHub
        - **DockerHub**: only DAST (prebuilt image) is supported for now
        - **ZIP / GitHub**: select framework/structure from a menu of suuported frameworks/structures
- Input is validated before queueing:
    - Basic security checks (archive bombs, disallowed binaries, etc.)
    - Structural validation vs canonical project structure
        - Example: Spring Boot + Maven → `pom.xml` at root, main class in `src/main/java/...`
- Validation outcomes:
    - **ACCEPTED** → proceed
    - **ACCEPTED_WITH_ISSUES** → non-critical missing elements (e.g., empty test folder)
    - **REFUSED** → hard failures, not queued

### Project Metadata Extraction

- Metadata JSON is generated for accepted projects
- Captures:
    - Project info (name, framework, language)
    - Tool versions (Java, Maven…)
    - Selected operations (unit tests, build, integration tests, DAST)
    - Resource constraints, exposed ports, etc.

**Example JSON (Spring Boot, Maven 3.9, Java 21, full CI, no DAST/integration tests)**

```json
{
  "project": {
    "name": "order-service",
    "framework": "spring-boot",
    "language": "java",
    "java_version": "21",
    "build_tool": "maven",
    "packaging": "jar",
    "maven_version": "3.9"
  },
  "pipeline_config": {
    "run_unit_tests": true,
    "run_build": true,
    "run_sast": true,
    "run_dast": false,
    "run_integration_tests": false,
    "run_smoke_tests": true
  },
  "execution_environment": {
    "containerized": true,
    "isolated_network": true,
    "resource_limits": {
      "cpu": "2",
      "memory": "2g"
    }
  },
  "job_id": "job-2025-00127"
}
```

### Job Concept & Queueing

Each job is allocated default CPU and memory resources to ensure isolation and fairness. In future iterations, resource allocation could be made configurable per project up to a system-defined maximum.

- Accepted projects enter a **job queue**, executed asynchronously in isolated pipelines
- Maximum concurrent pipelines: 3
    - Additional accepted projects wait in the queue
    - This ensures server resources are not exhausted
- Rejected projects never enter the job queue

### Ephemeral Workspace

- Each job runs in a temporary folder containing:
    - Project source code (read-only)
    - Pipeline scripts
    - Output folders for reports/logs
- Workspace is **cleaned up after job completion**, freeing resources

---

# 5. Phase 3 — Pipeline Selection & Definition

### Framework-Specific Pipelines

- Pipelines are tailored to each supported framework and toolchain.
- Commands and procedures differ across frameworks (e.g., Spring Boot + Maven vs FastAPI).

### Metadata-Driven Selection

- The project metadata JSON determines which pipeline scripts to run.
- Ensures the backend orchestrator remains framework-agnostic.

### Script-Based Pipeline Philosophy

- Each stage is implemented as a standalone `.sh` script.
- Backend simply calls `build.sh`, `test.sh`, etc., without custom logic per framework.
- good for modularity, reusability, and future extensibility.
- we would have a project structure similar to :

```   
├── 📁 pipelines/
│   ├── 📁spring/
│   │   ├── build.sh
│   │   ├── test.sh
│   │   ├── package.sh
│   │   ├── run-smoke.sh
│   │   └── dast.sh
│   └── 📁angular/
│       ├── build.sh
│       ├── test.sh
│       ├── package.sh
│       ├── run-smoke.sh
│       └── dast.sh

```

### Canonical CI/CD Stages (for full CI) after project validation

| Stage | Purpose | Tool(s) e.g | Example / Notes |
| --- | --- | --- | --- |
| **Build** | Compile/package the project | Maven, Gradle, npm | `mvn package` for Spring Boot |
| **Unit Testing** | Verify individual components | JUnit, pytest, Jest | `mvn test` |
| **Static Analysis (SAST)** | Detect insecure coding patterns | Semgrep | Reads code only, no network |
| **Software Composition Analysis (SCA)** | Detect vulnerable dependencies | Trivy | `pom.xml`, `package-lock.json`, `requirements.txt` |
| **Secret Scan** | Detect hardcoded secrets | Gitleaks | API keys, passwords, tokens |
| **Container Scan** | Detect container-related vulnerabilities | Trivy | Base image, OS packages, runtime deps |
| **Smoke / Integration Tests** | Verify app starts & endpoints respond | curl, HTTP tests | Can simulate real module interactions |
| **Dynamic Analysis (DAST)** | Test running app for vulnerabilities | OWASP ZAP | Runs in isolated network, optional per user |
| **Report Aggregation** | Collect & normalize results | Custom scripts | JSON report, severity levels, findings summary |

---

# 6. Phase 4 — Pipeline Execution & Isolation

### Containerized Execution Model

- Each job runs in an **isolated Docker container**, ensuring security and reproducibility.
- Prebuilt images with all necessary dependencies are used:
    - Project code is mounted read-only
    - Pipeline scripts are executed inside this environment
- Isolation protects the host machine from untrusted inputs and runtime vulnerabilities.

### Runner-Based Approach

- **Fat runners**: prebuilt Docker images containing all required runtimes and tools.
    - Example: Java 17 + Maven 3.9 runner
    - Fast for execution, no rebuild per job
    - Trade-off: larger storage footprint
- Alternative: dynamic runner templates per user request (different tool versions)
    - Slower due to per-job image builds
    - More flexible, less storage , more time to wait for the end user .
- **Current project**: we willuse fat runners to limit the amount of supported project types and to have faster requests so we can better test and debug the processes .

### Temporary Workspace (per job)

- A unique workspace is created for each job, containing:

```
├── 📁 workdir/<job-id>/
│   ├── 📁 project/        # user source code (read-only)
│   ├── 📁 pipelines/      # framework pipeline scripts
│   │   └── 📁 spring/
│   │       ├── build.sh
│   │       ├── test.sh
│   │       ├── package.sh
│   │       ├── run-smoke.sh
│   │       └── dast.sh
│   ├── 📁 reports/        # normalized outputs (writable)
│   │   ├── 📁 build/
│   │   ├── 📁 sast/
│   │   ├── 📁 dast/
│   │   └── 📝 meta.json
│   └── 📁 metadata/
│       └── 📝 project.json # generated after validation
```

- **Mounts inside the runner**:
    - `project/` → read-only source code for builds tests …
    - `reports/` → writable outputs for normalization and reporting
    - `metadata/` → guides script selection and execution

### Network & DAST Isolation

- Each job uses a **private Docker network** to prevent exposure to host or other jobs
- DAST workflow:
    - Runner container runs the project
    - OWASP ZAP container connects inside the same network to perform dynamic scanning
- Future option: run the entire workspace on a **Raspberry Pi** for extra security isolation

### Example Workflow (Java 17 + Maven 3.9)



```bash
docker run --rm \
  -v /workdir/job-001/project:/app:ro \
  -v /workdir/job-001/reports:/reports \
  -v /workdir/job-001/pipelines:/pipelines \
  --network job-001-net \
  runner-java17-maven39 \
  bash -c "/pipelines/spring/build.sh && /pipelines/spring/test.sh"
```
- Outputs are collected, normalized, and saved in `/reports/`
- Workspace is deleted after job completion, freeing resources
---