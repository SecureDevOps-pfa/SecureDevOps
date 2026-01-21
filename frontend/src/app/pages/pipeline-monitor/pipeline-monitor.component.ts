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

interface StageInfo {
  name: string;
  displayName: string;
  icon: string;
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILURE' | 'SKIPPED';
}

@Component({
  selector: 'app-pipeline-monitor',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './pipeline-monitor.component.html',
  styleUrls: ['./pipeline-monitor.component.scss']
})
export class PipelineMonitorComponent implements OnInit, OnDestroy {
  jobId: string = '';
  jobStatus: JobStatus | null = null;
  stages: StageInfo[] = [];
  isLoading: boolean = true;
  errorMessage: string = '';
  
  private pollingSubscription?: Subscription;

  stageMapping: { [key: string]: { displayName: string; icon: string } } = {
    'SECRETS': { displayName: 'Secret Scan', icon: '🔐' },
    'BUILD': { displayName: 'Build', icon: '🔨' },
    'TEST': { displayName: 'Unit Tests', icon: '🧪' },
    'SAST': { displayName: 'SAST', icon: '🔍' },
    'SCA': { displayName: 'SCA', icon: '📦' },
    'PACKAGE': { displayName: 'Package', icon: '📦' },
    'SMOKE-TEST': { displayName: 'Smoke Tests', icon: '💨' },
    'DAST': { displayName: 'DAST', icon: '🛡️' }
  };

  constructor(
    private route: ActivatedRoute,
    private pipelineService: PipelineService,
    private cdr: ChangeDetectorRef
  ) {}

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
    this.jobStatus = status;
    this.stages = this.buildStagesList(status);
  }

  buildStagesList(status: JobStatus): StageInfo[] {
    const stageOrder = ['SECRETS', 'BUILD', 'TEST', 'SAST', 'SCA', 'PACKAGE', 'SMOKE-TEST', 'DAST'];
    
    return stageOrder
      .filter(stageName => status.execution.stages[stageName])
      .map(stageName => ({
        name: stageName,
        displayName: this.stageMapping[stageName].displayName,
        icon: this.stageMapping[stageName].icon,
        status: status.execution.stages[stageName].status
      }));
  }

  getStageClass(status: string): string {
    const baseClass = 'stage-circle';
    switch (status) {
      case 'PENDING': return `${baseClass} pending`;
      case 'RUNNING': return `${baseClass} running`;
      case 'SUCCESS': return `${baseClass} success`;
      case 'FAILURE': return `${baseClass} failed`;
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
}