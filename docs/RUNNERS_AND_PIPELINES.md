# Isolated Runner & Pipeline Execution – Local Workflow

This document explains **what was implemented so far** and how to **manually run and test pipelines using isolated runners**, using a **Spring Boot (Java 17 / Maven 3.9)** project as a concrete example. It also outlines **what will be automated next in Python**.

---

## 🎯 Goals of this document

* High‑level view of how pipelines work
* How the isolated runner environment operates
* Security measures implemented so far (and planned)
* How to set up and manually use a runner
* How this process will later be automated via Python

---

## 🏃 Runners

A **runner** is a Docker image that contains **all dependencies required to execute a user project**.

For a Maven‑built Spring Boot project, this means:

* Java (same or higher version than the project)
* Maven
* Additional tools needed by pipelines (e.g. `curl` for smoke tests)

The runner is started as a **container**, and the following are mounted into it:

* the user project (`app/`)
* the pipeline scripts (`pipelines/`)
* the reports directory (`reports/`)

All pipeline execution happens **inside the container**, with **very restricted privileges** and no direct control over the host system.

The runner uses a **non‑root user** with limited permissions.

### Example runner (Java 17 / Maven 3.9)

> Full runner definition: `runners/java17maven3.9`

```Dockerfile
FROM eclipse-temurin:17-jdk-jammy

# ---------- system deps ----------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        unzip \
        ca-certificates \
        bash && \
    rm -rf /var/lib/apt/lists/*

# ---------- maven install ----------
ENV MAVEN_VERSION=3.9.12
ENV MAVEN_HOME=/opt/maven
ENV PATH=$MAVEN_HOME/bin:$PATH

RUN curl -fsSL https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.9.12/apache-maven-3.9.12-bin.zip \
    -o /tmp/maven.zip && \
    unzip /tmp/maven.zip -d /opt && \
    mv /opt/apache-maven-3.9.12 ${MAVEN_HOME} && \
    rm /tmp/maven.zip

# ---------- non-root user ----------
RUN useradd -m -u 10001 runner
USER runner
WORKDIR /home/runner

CMD ["bash"]
```

### Fat runners (design choice)

We use **fat runners**: dependencies and versions are baked directly into the image.

Examples:

* `java17 + maven3.9`
* `java21 + maven3.9`

Trade‑off:

* ❌ More storage usage
* ✅ No runtime downloads → faster and more predictable execution

### Runner user & UID

* All runners use the **same non‑root UID: `10001`**
* This simplifies permissions when mounting workspaces
* The runner only has access to workspace‑related files

### Publishing runners

Runners are built and pushed to Docker Hub (for now):

```bash
#ran from runners/java-maven
docker build -t abderrahmane03/pipelinex:java17-mvn3.9.12-latest .
docker push abderrahmane03/pipelinex:java17-mvn3.9.12-latest
```

Later, this can move to a **private or cloud‑managed registry**.

---

## 📁 Workspaces

Once a project is accepted by validation, an **ephemeral workspace** is created. All pipelines run **inside this workspace**, mounted into the runner.

### Workspace structure
> all the naming conventions (app/ pipelines/ reports/ must be respected as they are expected by the pipelines and future logic)

```
📁 workdir/<job-id>/
├── 📁 app/                # user project (renamed to app)
├── 📁 pipelines/          # framework-specific pipeline scripts
│   ├── build.sh
│   ├── test.sh
│   ├── package.sh
│   ├── smoke.sh
│   ├── sast.sh
│   ├── secrets.sh
│   ├── sca.sh
│   └── dast.sh
├── 📁 reports/            # pipeline outputs
│   ├── build/
│   │   ├── build.log
│   │   └── result.json
│   ├── package/
│   │   ├── package.log
│   │   └── result.json
│   ├── smoke-test/
│   │   ├── smoke-test.log
│   │   └── result.json
│   └── test/
│       ├── test.log
│       └── result.json
└── 📁 metadata/
    └── 📝 project.json     # tech stack + stages to execute
```

The entire workspace is **owned by the runner user** and mounted into the container at runtime.

### Ownership & permissions
> the workspaces are owned by the runner user/group and required permissions are granted 
```bash
sudo chown -R 10001:10001 workdir/<job-id>
sudo chmod -R u+rwx workdir/<job-id>
sudo chmod +x workdir/<job-id>/pipelines/*.sh
```

---

## ▶️ Running the runner manually

Command to start the runner container and mount the workspace:

```bash
docker run --rm -it \
  -u 10001:10001 \
  -v workdir/<job-id>/app:/home/runner/app:rw \
  -v workdir/<job-id>/pipelines:/home/runner/pipelines:ro \
  -v workdir/<job-id>/reports:/home/runner/reports:rw \
  -w /home/runner \
  abderrahmane03/pipelinex:java17-mvn3.9.12-latest
```

Notes:

* `app` is **read‑write** (Maven writes to `target/`)
* `pipelines` is **read‑only** (predefined, executable scripts)
* `reports` is **read‑write** (logs + JSON results)

Once inside the container, each stage can be executed manually:

```bash
$pipelines/build.sh
$pipelines/test.sh
$pipelines/package.sh
$pipelines/smoke.sh
```

All outputs are written to the `reports/` directory , all results have the same structure :
```json
{
  "stage": "${STAGE}",
  "status": "${STATUS}", //SUCCESS OR FAILED
  "duration_ms": ${DURATION},
  "message": "${MESSAGE}"
}
```

---

## 🔁 Pipelines

Pipeline scripts are organized by framework at the project root:

```bash
📁 pipelines/
└── 📁 spring-boot-maven/
    ├── build.sh
    ├── test.sh
    ├── package.sh
    ├── smoke.sh
    ├── sast.sh
    ├── sca.sh
    ├── secrets.sh
    └── dast.sh
```

Each stage:

* lives in its own `.sh` file
* assumes execution relative to the workspace structure
* writes logs and a `result.json` file to `reports/<stage>/`

once a workspace is created the adequat pipelines are copied there as well inside workspaces/job-id/pipelines/

---

## 🔒 Security measures (current & planned)

**Implemented so far:**

* Isolated execution inside Docker containers
* Non‑root runner user (`uid 10001`)
* Read‑only mounts where possible
* Ephemeral workspaces

**Planned:**

* Network restrictions per runner
* Resource limits (CPU / memory)
* Private image registry

---

## 🔜 Next steps

* Automate workspace creation and runner execution using Python
* Orchestrate pipelines programmatically based on metadata
* Aggregate and normalize outputs for frontend consumption
* Run jobs asynchronously using a task queue (Celery)
