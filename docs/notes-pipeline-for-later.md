for the current iteration ill do many things manually to test the pipelines and the runner , some config steps that i would automate later will be kept here . 


### Iteration I : known spring boot project with everything respected 
- since the runner has a non root user i should grant it permission for the files to be mounted to its container 
- i should not assume /actuator/health is available for all projects
- i should make the port to test in smoke test/future dast a variable since its not always the default 8080
- i should add logging in all pipelines , instead of a simple message project did not compile ... it should be a displayed logs for what went wrong 
- the runners wont live inside the server rather in dockerhub 
- for this iteration i will be running the container either from the local build image or from the dockerhub pulled one either way from the terminal , later on docker cli would be used . 
- chown -R 10001:10001 workspaces/job-123 where the 10001 is the uid of the user running the docker image as non root , requires permission from the host file system before mounting them to the image 
- all dockerfiles/runners would use non root users with the same id 


commands to automate : 
- moving the workspace permission to the runner user 
```bash
sudo chown -R 10001:10001 workspaces-test/job-test
sudo chmod -R u+rwx workspaces-test/job-test (or chmod 700 job-test for better isolation , for the future)
sudo chmod +x workspaces-test/job-test/pipelines/*.sh
```
running the runner (using the docker image ) , will be slightly changed when adding tags to the docker image 
```bash 
docker run --rm -it \
  -u 10001:10001 \
  -v $PWD/workspaces-test/job-test/app:/home/runner/app:rw \
  -v $PWD/workspaces-test/job-test/pipelines:/home/runner/pipelines:ro \
  -v $PWD/workspaces-test/job-test/reports:/home/runner/reports:rw \
  -w /home/runner \
  abderrahmane03/pipelinex:java17-mvn3.9.12-latest
#one liner
docker run --rm -it   -u 10001:10001   -v $PWD/workspace-runner/app:/home/runner/app:rw   -v $PWD/workspace-runner/pipelines:/home/runner/pipelines:ro   -v $PWD/workspace-runner/reports:/home/runner/reports:rw   -w /home/runner   abderrahmane03/pipelinex:java17-mvn3.9.12-latest
```

```bash
docker build -t abderrahmane03/pipelinex:java17-mvn3.9.12-latest . 
docker push abderrahmane03/pipelinex:java17-mvn3.9.12-latest
```

### General app 
- opnce the project is tested and approved rename its folder to app/ and remove unecessary files (optiona , such as readme mvnw ... )



### useful for later documentation 
- to display logs clearly for maven use : 
```bash
if mvn -f ../app/pom.xml -DskipTests clean compile \
     -B -ntp \
     >"$LOG_FILE" 2>&1; then
```
| Flag      | Why                                |
| --------- | ---------------------------------- |
| `-B`      | Batch mode → no colors, no prompts |
| `-ntp`    | No transfer progress spam          |
| `>`       | All stdout to file                 |
| `2>&1`    | stderr included                    |
| exit code | Maven returns correct status       |



- for debugging permissions : 
```bash
ls -ld $PWD
ls -ld workspace-runner
ls -ld workspace-runner/reports
```
