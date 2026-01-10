- gitleaks is added as a binary to runners/ and will be copied to all runners (fat runners ) , this approach is used cuz i did not find an official trusted binary and adding another docker stage is heavier than just copying the raw compiled binary from gitleaks source code . maybe ill change that in the future 
- since its in the root all docker builds MUST be done from runners/ 
```bash
docker build -f java17-maven3.9/Dockerfile -t abderrahmane03/pipelinex:java17-mvn3.9.12-latest .
```

docker run --rm -it   -u 10001:10001   -v workdir/app:/home/runner/app:rw   -v workdir/pipelines:/home/runner/pipelines:ro   -v workdir/reports:/home/runner/reports:rw   -w /home/runner   abderrahmane03/pipelinex:java17-mvn3.9.12-latest


just to trigger runner push 



