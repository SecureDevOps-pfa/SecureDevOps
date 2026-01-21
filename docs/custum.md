custom scripts are limited only to sast tools , its basically a script that replaces sast.sh or secrets-scope.sh based on the user wish , thats it .
### frontend wise : 
the user should be informed of all restrictions and limitations . 
- when selecting pipelines stages on the sast tools (secrets scanning and sast) the user can select either the default ones we have or pick custom mode for one of them . 
- the user will be prompted by the context of this customization 
    - he will enter the command to be ran 
    - he will give the command to install the tool 
    - the user is informed to use the variables `"${LOG_FILE}"` and `"$APP_DIR"` when needed in his command 
    - the user is prompted the extention of his log file (.json .log ... ) 
    - if the command he runs to install a tool requires adding it to the bin/ so its executable , he should instead put it in `home/runner/bin/`
    - the command to install a tool shoud not include `sudo` , subsequently it wont include package managers `apt yum ...` as they require a sudo most of the time 


### backend : 
- the custum script is in `pipelines/global/sample-custumizable.sh`
- the user custum scripts falls into `sast` or `secrets` stage , it is selected in the frontend and should be given to the script as a variable named `STAGE`
- `INSTALL_CMD` is the variable holding the command to install the tool needed 
- `TOOL_CMD` is the variable holding the command to be ran 
- the user enters the extention of the output of his tool (we assume 1 output , default is json) , store it as a variable named `LOG_EXT`
nothing else is to be done , the custum script is treated as a normal sast or dast script , the workflow is the same 
- user picks custum sast 
- when the backend copies the scripts instead of copying `pipelines/sast.sh` or secrets.sh it copies instead  `pipelines/global/custom.sh`
- when its the time to run custom.sh the backend gives it the necessary variables : `STAGE,INSTALL_CMD, and TOOL_CMD` 
the rest is the same , it has a normal stage name it appears normally in the state.json