### BACKEND 
what needs to be done is mainly improve logging , sending logs to the frontend , and enhance the logic of picking pipelines and generalise pipeline selections . 
- when running the pipelines inside the backend contaner and the outpuse are written like : 
```bash 
[PIPELINE] START ...
[PIPELINE] END ...
```
these outputs should be redirected to the frontend to be displayed 
- once a job finished execuiton , each stage with its result.json and stage.log must be outside the container so they can be displayed by the frontend (if a stage is failed we would be able to see the logs just like in github actions or jenkins)
- instead of hardcoding maven pipelines when chosing the pipelines hsould be picked from the metadata , assuming the namine convention framework or framework-rest-of-name if it has more than one word like spring-boot . 
- for pipelines execution , the order should not be arbitrary : 
    - pipelines are selected (build package test smoke sast sca secrets)
    - sast sca and secrets are always ran since they only require the code itself
    - build first , if it fails package test and smoke would fail so need to run them
    - if package fails no need to run smoke 
    - if smoke fail no need to run  dast (in the future once dast is established) 



### app's devops 
enhancing the cd pipeline to only push the changing parts of the projects rather than everything
-  separate pushing backend form being the main action
- add pushing runners workflow/job
- use a github action to check changes in a folder
- apply it to only push the changing part of the code reducing pipeline execution by avoiding useless reexecutions


### pipelines and runners 
- add sast required tools to the runners (maven and gradle)
- finish pipelines (sast sca and secrets)
- improve logging (change result.json to stage.json)
- checks which one should come first , dast or orchestration and start with it 

### frontend & other frameworks support 
- start frontend inspired by jenkins and github actions with a foccus on ux (clear form explaining app's constrainsts , logging on each stage ... )
- add another framework runner and pipelines 
    - same runner format (almost the same code change of the core language and the build tool)
    - same runner config : sast and other usefule tools (curl) installed , same user id , same workdir and cmd 
    -  same scripts logging naming convention and place , diffrent commands 