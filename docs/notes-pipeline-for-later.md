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


### General app 
- opnce the project is tested and approved rename its folder to app/ and remove unecessary files (optiona , such as readme mvnw ... )
