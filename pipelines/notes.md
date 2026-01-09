| Tool                  | Usage                                                                            | Expected Output                                                                 |
| --------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **Semgrep (SAST)**    | Scan source folder: `semgrep --config auto --json /app/src/main/java`            | JSON report of insecure coding patterns. Can include CWE, severity, file, line. |
| **Trivy (SCA)**       | Scan Maven dependencies: `trivy fs --scanners vuln --format json /app`           | JSON report listing vulnerable dependencies, version, severity.                 |
| **Trivy (Container)** | After `docker build -t myapp:latest .`: `trivy image --format json myapp:latest` | JSON report listing OS & package vulnerabilities in container image.            |
