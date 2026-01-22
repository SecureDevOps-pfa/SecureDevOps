import { Routes } from '@angular/router';
import { JobSubmissionComponent } from './pages/project-submission/job-submission.component';
import { PipelineMonitorComponent } from './pages/pipeline-monitor/pipeline-monitor.component';

export const routes: Routes = [
  { path: '', component: JobSubmissionComponent },
  { path: 'monitor/:jobId', component: PipelineMonitorComponent },
  { path: '**', redirectTo: '' }
];