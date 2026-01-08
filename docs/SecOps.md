this file goes through decisions made in the secops phase : 
### secrets scanning | gitleaks
- gitleaks is framework independent so it will live in pipelines/global/secrets-*.sh (2 options)
- gitleaks have 2 main options , scanning the working tree or scanning the full history (history might take longer while main tree is very quick )
- in the user form when choosing to use gitleaks both options will be explained and separately selected 
- the runner will have a source compiled executable binary 
    -since there is no official binary for it ive compiled from the source and will copy to the runner 
```bash
COPY gitleaks /usr/local/bin/gitleaks
RUN chmod +x /usr/local/bin/gitleaks
```
- the main 2 commands we will use for gitleaks are : 
```bash
# current directory
gitleaks dir .   --report-format json   --report-path reports/gitleaks-dir.json
# all history
gitleaks git .   --report-format json   --report-path reports/gitleaks-git.json
```
- for pipeline safety 
```bash

```
- the reports must be created in advance 
- if no threat is found the json looks like ```[]```
- output example of the dir case 
```json 
[
 {
  "RuleID": "discord-client-secret",
  "Description": "Discovered a potential Discord client secret, risking compromised Discord bot integrations and data leaks.",
  "StartLine": 16,
  "EndLine": 16,
  "StartColumn": 2,
  "EndColumn": 59,
  "Match": "discord_client_secret = '8dyfuiRyq=vVc3RRr_edRk-fK__JItpZ'",
  "Secret": "8dyfuiRyq=vVc3RRr_edRk-fK__JItpZ",
  "File": "backend/config.py",
  "SymlinkFile": "",
  "Commit": "",
  "Entropy": 4.41391,
  "Author": "",
  "Email": "",
  "Date": "",
  "Message": "",
  "Tags": [],
  "Fingerprint": "backend/config.py:discord-client-secret:16"
 },
  {
  "RuleID": "generic-api-key",
  "Description": "Detected a Generic API Key, potentially exposing access to various services and sensitive operations.",
  "StartLine": 10,
  "EndLine": 10,
  "StartColumn": 5,
  "EndColumn": 47,
  "Match": "Secret\": \"8dyfuiRyq=vVc3RRr_edRk-fK__JItpZ\"",
  "Secret": "8dyfuiRyq=vVc3RRr_edRk-fK__JItpZ",
  "File": "reports/gitleaks-dir.json",
  "SymlinkFile": "",
  "Commit": "",
  "Entropy": 4.41391,
  "Author": "",
  "Email": "",
  "Date": "",
  "Message": "",
  "Tags": [],
  "Fingerprint": "reports/gitleaks-dir.json:generic-api-key:10"
 }
]
```
- output in the case of history 
```json
{
 {
  "RuleID": "generic-api-key",
  "Description": "Detected a Generic API Key, potentially exposing access to various services and sensitive operations.",
  "StartLine": 23,
  "EndLine": 23,
  "StartColumn": 83,
  "EndColumn": 131,
  "Match": "api_key=6eaDLPAKTyulopyXgq9Tww3qu8ZgqMYFeJIfr9oc`",
  "Secret": "6eaDLPAKTyulopyXgq9Tww3qu8ZgqMYFeJIfr9oc",
  "File": "front-end/src/components/Hero.jsx",
  "SymlinkFile": "",
  "Commit": "6460c1c0163993fdc342b7973b500bd904939649",
  "Link": "https://github.com/m-elhamlaoui/development-platform-nova-pioneers/blob/6460c1c0163993fdc342b7973b500bd904939649/front-end/src/components/Hero.jsx#L23",
  "Entropy": 4.803056,
  "Author": "zakaria oumghar",
  "Email": "zakariaoumghar1@gmail.com",
  "Date": "2025-05-26T04:31:11Z",
  "Message": "fixing some parenting",
  "Tags": [],
  "Fingerprint": "6460c1c0163993fdc342b7973b500bd904939649:front-end/src/components/Hero.jsx:generic-api-key:23"
 },
  {
  "RuleID": "generic-api-key",
  "Description": "Detected a Generic API Key, potentially exposing access to various services and sensitive operations.",
  "StartLine": 469,
  "EndLine": 469,
  "StartColumn": 2,
  "EndColumn": 75,
  "Match": "JWT_SECRET=SB4cgMKW7XkP83H5z94FfHd8QXYZVaJ2GtRbnLm5uEvsUwC6DTjeKqNyA7pZkrx",
  "Secret": "SB4cgMKW7XkP83H5z94FfHd8QXYZVaJ2GtRbnLm5uEvsUwC6DTjeKqNyA7pZkrx",
  "File": "backend-services/api-gateway/documentation/documentation.md",
  "SymlinkFile": "",
  "Commit": "a52e1038536ff41973105267d50f4b0c89cc5dd3",
  "Link": "https://github.com/m-elhamlaoui/development-platform-nova-pioneers/blob/a52e1038536ff41973105267d50f4b0c89cc5dd3/backend-services/api-gateway/documentation/documentation.md?plain=1#L469",
  "Entropy": 5.6915655,
  "Author": "Abderrahmane",
  "Email": "essahihabderrahman2020@gmail.com",
  "Date": "2025-05-26T20:45:20Z",
  "Message": "api gateway modifs",
  "Tags": [],
  "Fingerprint": "a52e1038536ff41973105267d50f4b0c89cc5dd3:backend-services/api-gateway/documentation/documentation.md:generic-api-key:469"
 }
}
```
