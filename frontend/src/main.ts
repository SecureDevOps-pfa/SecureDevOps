// filepath: c:\Users\eloue\Downloads\pipelineX\SecureDevOps\frontend\src\main.ts
import { bootstrapApplication } from '@angular/platform-browser';
import { App } from './app/app';
import { appConfig } from './app/app.config';  // Ensure this exists and configures routing

bootstrapApplication(App, appConfig)
  .catch(err => console.error(err));