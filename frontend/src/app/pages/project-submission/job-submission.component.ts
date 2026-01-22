import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { PipelineService } from '../../services/pipeline.service';
import { ProjectMetadata, Stack, Versions, Pipeline } from '../../models/project-metadata.model';
import { LucideAngularModule, icons } from 'lucide-angular';

@Component({
  selector: 'app-job-submission',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideAngularModule],
  templateUrl: './job-submission.component.html',
  styleUrls: ['./job-submission.component.scss']
})
export class JobSubmissionComponent {
  inputType: 'zip' | 'github' = 'zip';
  selectedFile: File | null = null;
  githubUrl: string = '';
  isDragging: boolean = false;
  
  // Lucide icons
  readonly icons: { [key: string]: any } = {
    Package: icons.Package,
    Github: icons.Github,
    Upload: icons.Upload,
    Shield: icons.Shield,
    Hammer: icons.Hammer,
    TestTube: icons.TestTube,
    Search: icons.Search,
    Layers: icons.Layers,
    Box: icons.Box,
    Flame: icons.Flame,
    ShieldCheck: icons.ShieldCheck,
    Database: icons.Database,
    Code: icons.Code,
    Settings: icons.Settings,
    Play: icons.Play,
    TriangleAlert: icons.TriangleAlert,
    FileArchive: icons.FileArchive,
    GitBranch: icons.GitBranch,
    Check: icons.Check,
    Info: icons.Info
  };
  
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
    secret_scan_mode: 'dir' as 'dir' | 'git' | 'custom',
    secret_custom: {
      install_cmd: '',
      tool_cmd: '',
      log_ext: 'json'
    },
    run_build: true,
    run_unit_tests: true,
    run_sast: true,
    sast_mode: 'default' as 'default' | 'custom',
    sast_custom: {
      install_cmd: '',
      tool_cmd: '',
      log_ext: 'json'
    },
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

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.name.toLowerCase().endsWith('.zip')) {
        this.selectedFile = file;
        this.errorMessage = '';
      } else {
        this.errorMessage = 'Please drop a valid ZIP file';
        this.selectedFile = null;
      }
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

    // Validate custom tool configurations
    if (this.pipelineOptions.secret_scan_mode === 'custom') {
      if (!this.pipelineOptions.secret_custom.install_cmd || !this.pipelineOptions.secret_custom.tool_cmd) {
        this.errorMessage = 'Please provide install and tool commands for custom secret scanning';
        return;
      }
    }

    if (this.pipelineOptions.sast_mode === 'custom') {
      if (!this.pipelineOptions.sast_custom.install_cmd || !this.pipelineOptions.sast_custom.tool_cmd) {
        this.errorMessage = 'Please provide install and tool commands for custom SAST';
        return;
      }
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
      pipeline: {
        run_secret_scan: this.pipelineOptions.run_secret_scan,
        secret_scan_mode: this.pipelineOptions.secret_scan_mode,
        ...(this.pipelineOptions.secret_scan_mode === 'custom' && {
          secret_custom: this.pipelineOptions.secret_custom
        }),
        run_build: this.pipelineOptions.run_build,
        run_unit_tests: this.pipelineOptions.run_unit_tests,
        run_sast: this.pipelineOptions.run_sast,
        sast_mode: this.pipelineOptions.sast_mode,
        ...(this.pipelineOptions.sast_mode === 'custom' && {
          sast_custom: this.pipelineOptions.sast_custom
        }),
        run_sca: this.pipelineOptions.run_sca,
        run_package: this.pipelineOptions.run_package,
        run_smoke: this.pipelineOptions.run_smoke,
        run_dast: this.pipelineOptions.run_dast
      }
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