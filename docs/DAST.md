basically the way owasp zap works is : 
- app is running on a known port (in our case app runnning inside the runner container)
- owasp zap runs from its official docker image with that port as its target , it attacks the target and produces a json and an html (could be displayed in the frontend)
- in our case we  will have both app and zap run  inside the same internal docker network `(per job network : pipelinex-net-<job_id>)` so the app is reachable while we remain isolated 
- to simplify things , i created a docker compose to have them both on the same network with the correct volumes and  using docker dns to have zap correctly attack the app's path . 
```yaml
services:
  app:
    image: abderrahmane03/pipelinex:java17-mvn3.9-latest
    working_dir: /workspaces/source
    volumes:
      - ./workspaces/${JOB_ID:-.}:/workspaces
    command: mvn spring-boot:run
    expose:
      - "${PORT:-8080}"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:${PORT:-8080}"]
      interval: 5s
      timeout: 3s
      retries: 12

  zap:
    image: ghcr.io/zaproxy/zaproxy:stable
    depends_on:
      app:
        condition: service_healthy
    working_dir: /workspaces
    volumes:
      - ./workspaces/${JOB_ID:-.}:/workspaces
    environment:
      APP_PORT: "${PORT:-8080}"
      REPORTS_DIR: /workspaces/reports
    command: ["/bin/bash", "/workspaces/pipelines/dast.sh"]

networks:
  default:
    name: "${DOCKER_NETWORK:-pipelinex-network}"
```

- the backend should copy this docker compose from runners/dast/docker-compose.dast.yml and add it in the root of workspace/job-id
- then run docker compose -f docker-compose.dast.yml up after giving it the variables it expects
    - JOB_ID
    - PORT (will be defaulted to 8080 but the would be also taken in input from the user)
    - DOCKER_NETWORK : defaul is pipelinex-network , the value given should be pipelinex-network-JOB_ID
> [!WARNING]
> The provided `docker-compose.yml` assumes a strict and consistent filesystem layout that matches the runner image contract.

- inside the runner container
```bash
/home/runner
├── app/        # Spring Boot project (pom.xml, src/, target/)
├── pipelines/  # Security scripts (sast.sh, sca.sh, dast.sh, etc.)
└── reports/    # Output directory for all security stages
```
- dast.sh is  mounted  from /home/runner/pipelines/dast.sh and outputs are also on
```bash
/home/runner/reports/dast/
├── dast.json    # Raw ZAP JSON output
├── dast.html    # Human-readable HTML report
└── result.json  # Pipeline summary (SUCCESS / WARN / ERROR)
```

hopefully that should be it . 

#### explaination of what happens : 
- docker compose creates a docker internal network and registers both inside of it 
- docker dns names the user inputed application app , so it is reachable inside the network from http://app:port 
- the app service uses the runner then goes to source/ , runs `mvn spring-boot:run` , then does a health check 
- zap container waits until app service is healthy then attacks it using dast.sh which is mounted , writing outputs to reports/dast 
- zap outputs are result.json dast.json and dast.html , could be displayed in the future
- in this iteration we are using zap baseline mode which takes less time and requires less config , full scan mode can be added in the future.