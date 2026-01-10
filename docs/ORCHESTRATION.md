### orchestrators

for now we have 2 orchestrators : 
- docker-compose.dast.yml : orchestrating app with zap assuming no db is needed for the app
- docker-compose.java17mvn3.9.yml : orchestrates for app with db , works for test and smoke if db is required but  does not have zap service

what should be implemented is either one global compose with a way to disable services using preexisting images as disablers that just exit with 0 and add condition to only depend on db if its a non dummy service . or to have the backend use the service blocks to generate a docker compose each time , sort of proceduraly based on user input and core engine logic .  

same logic may be applied later to add frontend support as well . 


### pro mode 

allowing users to run anything with 0 restrictions is dangerous on the host , the approach well go for is allowing change  of the core command of each stage with a exit status management , like this :
```bash
: "${TOOL_CMD:=gitleaks dir \"$APP_DIR\" --report-format json --report-path \"$LOG_FILE\"}"

START_TS=$(date +%s%3N)

eval "$TOOL_CMD"
EXIT_CODE=$?

# -------------------------------
# Standardized exit code handling
# -------------------------------
case $EXIT_CODE in
  0) STATUS="SUCCESS"; MESSAGE="no leaks found" ;;
  1) STATUS="FAILURE"; MESSAGE="leaks found, see $LOG_FILE for details" ;;
  2) STATUS="ERROR"; MESSAGE="tool error" ;;
  *) STATUS="UNKNOWN"; MESSAGE="unknown exit code $EXIT_CODE" ;;
esac
```
another thing needed is dependencies in the runner , the template potentiallywould be shown to the user and they input jistwhat to be added to it not full modification (to avoid users not using a non root user ...) then they would wait for the image to be built , wont be pushed to dockerhub , since its custum its also going to be deleted by the end , then if its built their custum script is ran and reports are generated and given , this keeps the host safr while allowing a fair amount of custumization . 