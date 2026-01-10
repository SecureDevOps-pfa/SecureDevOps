| Tool                  | Usage                                                                            | Expected Output                                                                 |
| --------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **Semgrep (SAST)**    | Scan source folder: `semgrep --config auto --json /app/src/main/java`            | JSON report of insecure coding patterns. Can include CWE, severity, file, line. |
| **Trivy (SCA)**       | Scan Maven dependencies: `trivy fs --scanners vuln --format json /app`           | JSON report listing vulnerable dependencies, version, severity.                 |
| **Trivy (Container)** | After `docker build -t myapp:latest .`: `trivy image --format json myapp:latest` | JSON report listing OS & package vulnerabilities in container image.            |




### OWASP ZAP Notes

- zap contains 2 primary modes , baseline , which is what will be implemented intially , and full scan , which has a bit diffrent implementation and takes way way longer (~10min or more in some cases )
- zap wont start the app so i will assume the backend will be inside the runner container and run a bash command : mvn spring-boot:run , either test by using actuator or just give a good guess of when the app is up then run dast.sh 
- 


### scripts generally 
- until nc -z app 8080; do sleep 2; done
potentiallyi could do smoke tests without forcing the user to have actuator health by  tcp tests ... `todo : make port variable in all scripts`

#### structure not to forget 
workspace/
  job-id/
    source/
    reports/
    pipelines/
    metadata.json
    docker-compose.yml
