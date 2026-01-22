import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
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

  getJobLogs(jobId: string, stage: string): Observable<string> {
    // Backend returns FileResponse with application/octet-stream
    // We need to get it as arraybuffer and decode it manually
    return this.http.get(`${this.apiUrl}/jobs/${jobId}/${stage}/logs`, {
      responseType: 'arraybuffer'
    }).pipe(
      map(buffer => {
        // Decode the arraybuffer to text
        const decoder = new TextDecoder('utf-8');
        return decoder.decode(buffer);
      })
    );
  }
}