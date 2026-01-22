import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { PipelineService } from '../../services/pipeline.service';
import { JobStatus, StageStatus } from '../../models/job-status.model';
import { interval, Subscription } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { RouterModule } from '@angular/router';
import { ChangeDetectorRef } from '@angular/core';
import { LucideAngularModule, icons } from 'lucide-angular';

interface StageInfo {
  name: string;
  displayName: string;
  icon: string;
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'SKIPPED';
}

@Component({
  selector: 'app-pipeline-monitor',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, LucideAngularModule],
  templateUrl: './pipeline-monitor.component.html',
  styleUrls: ['./pipeline-monitor.component.scss']
})
export class PipelineMonitorComponent implements OnInit, OnDestroy {
  jobId: string = '';
  jobStatus: JobStatus | null = null;
  stages: StageInfo[] = [];
  isLoading: boolean = true;
  errorMessage: string = '';
  
  // Logs
  selectedStage: string = '';
  stageLogs: string = '';
  logsLoading: boolean = false;
  logsError: string = '';
  autoRefreshLogs: boolean = false;
  
  private pollingSubscription?: Subscription;
  private logsPollingSubscription?: Subscription;

  // Lucide icons
  readonly icons: { [key: string]: any } = {
    Shield: icons.Shield,
    Hammer: icons.Hammer,
    TestTube: icons.TestTube,
    Search: icons.Search,
    Package: icons.Package,
    Box: icons.Box,
    Flame: icons.Flame,
    ShieldCheck: icons.ShieldCheck,
    Check: icons.Check,
    X: icons.X,
    Clock: icons.Clock,
    Loader: icons.Loader,
    Download: icons.Download,
    ArrowLeft: icons.ArrowLeft,
    TriangleAlert: icons.TriangleAlert,
    Code: icons.Code,
    Wrench: icons.Wrench,
    Info: icons.Info,
    ChevronRight: icons.ChevronRight,
    Terminal: icons.Terminal
  };

  stageMapping: { [key: string]: { displayName: string; icon: string } } = {
    'SECRETS': { displayName: 'Secret Scan', icon: 'Shield' },
    'BUILD': { displayName: 'Build', icon: 'Hammer' },
    'TEST': { displayName: 'Unit Tests', icon: 'TestTube' },
    'SAST': { displayName: 'Static Analysis', icon: 'Search' },
    'SCA': { displayName: 'Dependencies', icon: 'Package' },
    'PACKAGE': { displayName: 'Package', icon: 'Box' },
    'SMOKE-TEST': { displayName: 'Smoke Tests', icon: 'Flame' },
    'DAST': { displayName: 'Dynamic Analysis', icon: 'ShieldCheck' }
  };

  constructor(
    private route: ActivatedRoute,
    private pipelineService: PipelineService,
    private cdr: ChangeDetectorRef
  ) {}

  getStageIcon(iconName: string): any {
    return this.icons[iconName] || this.icons['Box'];
  }

  ngOnInit(): void {
    this.jobId = this.route.snapshot.paramMap.get('jobId') || '';
    
    if (this.jobId) {
      this.startPolling();
    } else {
      this.errorMessage = 'Invalid job ID';
    }
  }

  ngOnDestroy(): void {
    this.stopPolling();
    this.stopLogsPolling();
  }

  startPolling(): void {
    // Initial fetch
    this.fetchJobStatus();

    // Poll every 2 seconds
    this.pollingSubscription = interval(2000)
      .pipe(
        switchMap(() => {
          console.log('[MONITOR] polling tick');
          return this.pipelineService.getJobStatus(this.jobId);
        })
      )
      .subscribe({
        next: (status) => {
          this.updateJobStatus(status);
          this.isLoading = false;
          this.cdr.detectChanges();
          
          // Stop polling if job is finished
          if (status.execution.state === 'SUCCEEDED' || status.execution.state === 'FAILED') {
            this.stopPolling();
          }
        },
        error: (error) => {
          this.errorMessage = 'Failed to fetch job status';
          console.error(error);
        }
      });
  }

  stopPolling(): void {
    if (this.pollingSubscription) {
      this.pollingSubscription.unsubscribe();
    }
  }

  fetchJobStatus(): void {
    this.pipelineService.getJobStatus(this.jobId).subscribe({
      next: (status) => {
        this.updateJobStatus(status);
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        this.errorMessage = error.error?.detail || 'Failed to load job status';
        this.isLoading = false;
      }
    });
  }

  updateJobStatus(status: JobStatus): void {
    const previousCurrentStage = this.jobStatus?.execution.current_stage;
    const previousState = this.jobStatus?.execution.state;
    this.jobStatus = status;
    this.stages = this.buildStagesList(status);

    // Auto-select current running stage if no stage is selected or stage changed
    const currentStage = status.execution.current_stage;
    if (currentStage) {
      if (!this.selectedStage || currentStage !== previousCurrentStage) {
        this.loadStageLogs(currentStage);
      }
    } else if (!this.selectedStage && (status.execution.state === 'SUCCEEDED' || status.execution.state === 'FAILED')) {
      // Pipeline finished but no stage selected - select the last completed stage
      const lastStage = this.stages.filter(s => s.status === 'SUCCESS' || s.status === 'FAILED').pop();
      if (lastStage) {
        this.loadStageLogs(lastStage.name);
      }
    }
  }

  buildStagesList(status: JobStatus): StageInfo[] {
    const stageOrder = ['SECRETS', 'BUILD', 'TEST', 'SAST', 'SCA', 'PACKAGE', 'SMOKE-TEST', 'DAST'];
    
    console.log('[DEBUG] Job status from backend:', status);
    console.log('[DEBUG] Execution stages:', status.execution.stages);
    
    return stageOrder
      .filter(stageName => status.execution.stages[stageName])
      .map(stageName => {
        const stageStatus = status.execution.stages[stageName].status;
        console.log(`[DEBUG] Stage: ${stageName}, Status: ${stageStatus}`);
        return {
          name: stageName,
          displayName: this.stageMapping[stageName].displayName,
          icon: this.stageMapping[stageName].icon,
          status: stageStatus
        };
      });
  }

  getStageClass(status: string): string {
    const baseClass = 'stage-circle';
    switch (status) {
      case 'PENDING': return `${baseClass} pending`;
      case 'RUNNING': return `${baseClass} running`;
      case 'SUCCESS': return `${baseClass} success`;
      case 'FAILED': return `${baseClass} failed`;
      case 'SKIPPED': return `${baseClass} skipped`;
      default: return baseClass;
    }
  }

  getOverallStatusClass(): string {
    if (!this.jobStatus) return '';
    
    const state = this.jobStatus.execution.state;
    switch (state) {
      case 'QUEUED': return 'status-queued';
      case 'RUNNING': return 'status-running';
      case 'SUCCEEDED': return 'status-success';
      case 'FAILED': return 'status-failed';
      default: return '';
    }
  }

  downloadReports(): void {
    if (!this.jobStatus || 
        (this.jobStatus.execution.state !== 'SUCCEEDED' && 
         this.jobStatus.execution.state !== 'FAILED')) {
      return;
    }

    this.pipelineService.downloadReports(this.jobId).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${this.jobId}-reports.zip`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      },
      error: (error) => {
        console.error('Failed to download reports', error);
      }
    });
  }

  getWarnings(): [string, any][] {
    return this.jobStatus?.execution?.warnings ? Object.entries(this.jobStatus.execution.warnings) : [];
  }

  loadStageLogs(stageName: string): void {
    const stage = this.jobStatus?.execution.stages[stageName];
    if (!stage || stage.status === 'SKIPPED' || stage.status === 'PENDING') {
      this.logsError = `Stage ${stageName} has not started yet or was skipped`;
      this.stageLogs = '';
      this.selectedStage = '';
      return;
    }

    this.selectedStage = stageName;
    this.logsError = '';
    this.stageLogs = '';

    // Stop any existing logs polling
    this.stopLogsPolling();

    // If stage is RUNNING, show waiting message and start polling
    if (stage.status === 'RUNNING') {
      this.logsLoading = false;
      this.stageLogs = `# Stage ${stageName} is currently running...\n# Logs will appear when the stage completes\n# Waiting for stage to finish...`;
      this.autoRefreshLogs = true;
      // Poll every 2 seconds to check if stage completed
      this.startLogsPolling(stageName);
    } else {
      // Stage is completed (SUCCESS or FAILED) - fetch logs immediately
      this.logsLoading = true;
      this.autoRefreshLogs = false;
      this.fetchStageLogs(stageName);
    }
  }

  fetchStageLogs(stageName: string): void {
    this.pipelineService.getJobLogs(this.jobId, stageName).subscribe({
      next: (logs) => {
        this.stageLogs = logs;
        this.logsLoading = false;
        this.logsError = '';
      },
      error: (error) => {
        const errorDetail = error.error?.detail || error.message || 'Failed to load logs';
        const status = error.status;
        
        // Stage is completed but logs not available
        if (status === 404) {
          console.log(`[Logs] No logs available for ${stageName}: ${errorDetail}`);
          this.logsError = '';
          this.stageLogs = `# No logs available for ${stageName}\n# The stage completed but did not generate any log output`;
        } else {
          console.error(`[Logs] Error loading logs for ${stageName}:`, error);
          this.logsError = errorDetail;
          this.stageLogs = '';
        }
        this.logsLoading = false;
      }
    });
  }

  startLogsPolling(stageName: string): void {
    // Poll every 2 seconds to check if stage is completed
    this.logsPollingSubscription = interval(2000)
      .subscribe(() => {
        const stage = this.jobStatus?.execution.stages[stageName];
        
        // Check if stage has completed
        if (stage && (stage.status === 'SUCCESS' || stage.status === 'FAILED')) {
          // Stage completed - fetch logs and stop polling
          this.stopLogsPolling();
          this.autoRefreshLogs = false;
          this.logsLoading = true;
          this.fetchStageLogs(stageName);
        } else if (stage?.status === 'RUNNING') {
          // Still running - update waiting message
          this.stageLogs = `# Stage ${stageName} is currently running...\n# Logs will appear when the stage completes\n# Waiting for stage to finish...`;
        } else {
          // Stage status changed unexpectedly - stop polling
          this.stopLogsPolling();
          this.autoRefreshLogs = false;
        }
      });
  }

  stopLogsPolling(): void {
    if (this.logsPollingSubscription) {
      this.logsPollingSubscription.unsubscribe();
      this.logsPollingSubscription = undefined;
    }
  }

  clearLogs(): void {
    this.selectedStage = '';
    this.stageLogs = '';
    this.logsError = '';
    this.autoRefreshLogs = false;
    this.stopLogsPolling();
  }
}
