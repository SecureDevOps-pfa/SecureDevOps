import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { PipelineService } from '../../services/pipeline.service';
import { ProjectMetadata, Stack, Versions, Pipeline } from '../../models/project-metadata.model';

@Component({
  selector: 'app-job-submission',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './job-submission.component.html',
  styleUrls: ['./job-submission.component.scss']
})
export class JobSubmissionComponent {
  inputType: 'zip' | 'github' = 'zip';
  selectedFile: File | null = null;
  githubUrl: string = '';
  
  // Supported frameworks
  frameworks = [
    { 
      label: 'Spring Boot + Maven',
      value: 'spring-boot',
      language: 'java',
      buildTool: 'maven',
      requiresDb: false
    }
  ];

  selectedFramework = this.frameworks[0];

  // Versions
  javaVersion: string = '17';
  mavenVersion: string = '3.9';

  // Pipeline options
  pipelineOptions = {
    run_secret_scan: false,
    secret_scan_mode: 'dir' as 'dir' | 'git',
    run_build: true,
    run_unit_tests: true,
    run_sast: true,
    run_sca: true,
    run_package: true,
    run_smoke: true,
    run_dast: false
  };

  requiresDatabase: boolean = false;
  isSubmitting: boolean = false;
  errorMessage: string = '';

  constructor(
    private pipelineService: PipelineService,
    private router: Router
  ) {}

  onFileSelected(event: any): void {
    const file = event.target.files[0];
    if (file && file.name.toLowerCase().endsWith('.zip')) {
      this.selectedFile = file;
      this.errorMessage = '';
    } else {
      this.errorMessage = 'Please select a valid ZIP file';
      this.selectedFile = null;
    }
  }

  onFrameworkChange(): void {
    // Update database requirement based on framework
    this.requiresDatabase = this.selectedFramework.requiresDb;
  }

  submitJob(): void {
    if (this.isSubmitting) return;

    // Validation
    if (this.inputType === 'zip' && !this.selectedFile) {
      this.errorMessage = 'Please select a ZIP file';
      return;
    }

    if (this.inputType === 'github' && !this.githubUrl.trim()) {
      this.errorMessage = 'Please enter a GitHub repository URL';
      return;
    }

    // Build metadata
    const metadata: ProjectMetadata = {
      stack: {
        language: this.selectedFramework.language,
        framework: this.selectedFramework.value,
        build_tool: this.selectedFramework.buildTool,
        requires_db: this.requiresDatabase
      },
      versions: {
        java: this.javaVersion,
        build_tool: this.mavenVersion
      },
      pipeline: { ...this.pipelineOptions }
    };

    this.isSubmitting = true;
    this.errorMessage = '';

    const submission$ = this.inputType === 'zip'
      ? this.pipelineService.submitZipJob(this.selectedFile!, metadata)
      : this.pipelineService.submitGitHubJob(this.githubUrl, metadata);

    submission$.subscribe({
      next: (response) => {
        this.isSubmitting = false;
        this.router.navigate(['/monitor', response.job_id]);
      },
      error: (error) => {
        this.isSubmitting = false;
        this.errorMessage = error.error?.detail || 'Failed to submit job. Please try again.';
      }
    });
  }
}