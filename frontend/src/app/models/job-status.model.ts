export interface StageStatus {
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'SKIPPED';
}

export interface ExecutionStatus {
  state: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED';
  current_stage: string | null;
  updated_at: string;
  stages: {
    [key: string]: StageStatus;
  };
  warnings: {
    [key: string]: string;
  };
}

export interface JobInfo {
  id: string;
  admission_status: string;
  created_at: string;
  stack: {
    language: string;
    framework: string;
    build_tool: string;
    requires_db: boolean;
  };
  versions: {
    java?: string;
    build_tool?: string;
  };
}

export interface JobStatus {
  job: JobInfo;
  execution: ExecutionStatus;
}