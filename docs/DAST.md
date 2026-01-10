basically the way owasp zap works is : 
- app is running on a known port (in our case app runnning inside the runner container)
- owasp zap runs from its official docker image with that port as its target , it attacks the target and produces a json and an html (could be displayed in the frontend)
- in our case we  will have both app and zap run  inside the same internal docker network `(per job network : pipelinex-net-<job_id>)` so the app is reachable while we remain isolated 


### backend todos 

#### important change : runners must use internal docker network from now on 
- to have zap and app in  the same network the runner should be there too , creating a network is abackend task , using docker sdk this time , a function to create the network : 
```python
import docker
from docker.errors import NotFound

client = docker.from_env()

def create_job_network(job_id: str) -> str:
    network_name = f"pipelinex-net-{job_id}"
    try:
        client.networks.get(network_name) # Already exists (unlikely but safe)
        return network_name
    except NotFound:
        client.networks.create(
            name=network_name,
            driver="bridge",
            internal=True  # internal for more security
        )
        return network_name
```
and  to remove it when the job finishes : 
```python
def remove_job_network(network_name: str):
    try:
        network = client.networks.get(network_name)
        network.remove()
    except NotFound:
        pass
```

- running the container with the docker network using docker sdk : 
```python
import docker
client = docker.from_env()
def run_runner_container(
    job_id: str,
    network_name: str,
    workdir_base: str,
    image: str = "abderrahmane03/pipelinex:java17-mvn3.9.12-latest",
):
    container = client.containers.run(
        image=image,
        name=f"runner-{job_id}",
        user="10001:10001",
        tty=True,
        detach=True,
        remove=True,  # equivalent to --rm
        working_dir="/home/runner",
        network=network_name,
        volumes={
            f"{workdir_base}/{job_id}/app": {
                "bind": "/home/runner/app",
                "mode": "rw",
            },
            f"{workdir_base}/{job_id}/pipelines": {
                "bind": "/home/runner/pipelines",
                "mode": "ro",
            },
            f"{workdir_base}/{job_id}/reports": {
                "bind": "/home/runner/reports",
                "mode": "rw",
            },
        },
        environment={
            "DOCKER_NETWORK": network_name,
            # APP_PORT injected later if needed
        },
    )
    return container
```

- the backend  will start the app ,wait until its up then runs dast.sh (start the app inside a docker network)
- the backend will run mvn spring-boot:run , waits a certain amount of time  while checking if the app is up then after a certain  amount if not responsive assumes it corrupt and wont start dast , if not dast is started . 
- if the pipeline already has smoke test enabled it would be ran before dast , if it succeed backend does not have to manually check app health before running dast , if smoke test fails dast will be skipped 
- the port is defaulted to 8080 in spring boot's case , but is taken as a user input as well . 

- 2 pruposed function to check the apps health 
1. by me hhhh uses basic lsof -i :port ,  after a certain amount of time if port is taken then tomcat is up , seems good enough for me (99% wont work in windows)
```python
import subprocess
import time
def wait_for_port_lsof(port: int, timeout: int = 60) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            result = subprocess.run(
                ["lsof", f"-i:{port}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode == 0:
                return True
        except FileNotFoundError:
            raise RuntimeError("lsof not available on system")
        time.sleep(1)
    return False
```

2. GPT hhh 
```python
import socket
import time

def wait_for_port_tcp(
    host: str,
    port: int,
    timeout: int = 60,
    interval: float = 1.0
) -> bool:
    """
    Wait until a TCP connection to host:port succeeds.
    Returns True if reachable, False on timeout.
    """

    end_time = time.time() + timeout

    while time.time() < end_time:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            try:
                sock.connect((host, port))
                return True
            except (ConnectionRefusedError, socket.timeout, OSError):
                pass

        time.sleep(interval)

    return False
```
- either way once the app is up just run the dast.sh and expect to get result.json dast.json and dast.html



### dast notes (abderrahmane)
- docker pull ghcr.io/zaproxy/zaproxy:sha256-563cb2a45bd7aa04ad972af0ab893fcf4cd657ed5fb3e4638fb504d19ee2af7c.att latest zap version available