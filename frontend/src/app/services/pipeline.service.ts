import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { JobCreationResponse, ProjectMetadata } from '../models/project-metadata.model';
import { JobStatus } from '../models/job-status.model';

@Injectable({
  providedIn: 'root'
})
export class PipelineService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  submitZipJob(file: File, metadata: ProjectMetadata): Observable<JobCreationResponse> {
    const formData = new FormData();
    formData.append('project_zip', file);
    formData.append('metadata', JSON.stringify(metadata));

    return this.http.post<JobCreationResponse>(
      `${this.apiUrl}/jobs/upload`,
      formData
    );
  }

  submitGitHubJob(githubUrl: string, metadata: ProjectMetadata): Observable<JobCreationResponse> {
    return this.http.post<JobCreationResponse>(
      `${this.apiUrl}/jobs/github`,
      {
        github_url: githubUrl,
        ...metadata
      }
    );
  }

  getJobStatus(jobId: string): Observable<JobStatus> {
    return this.http.get<JobStatus>(`${this.apiUrl}/jobs/${jobId}/status`);
  }

  downloadReports(jobId: string): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/jobs/${jobId}/reports`, {
      responseType: 'blob'
    });
  }
}