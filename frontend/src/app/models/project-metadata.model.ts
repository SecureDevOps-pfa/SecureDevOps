export interface Stack {
  language: string;
  framework: string;
  build_tool: string;
  requires_db: boolean;
}

export interface Versions {
  java?: string;
  build_tool?: string;
}

export interface CustomToolConfig {
  install_cmd: string;
  tool_cmd: string;
  log_ext: string;
}

export interface Pipeline {
  run_secret_scan: boolean;
  secret_scan_mode: 'dir' | 'git' | 'custom';
  secret_custom?: CustomToolConfig;
  run_build: boolean;
  run_unit_tests: boolean;
  run_sast: boolean;
  sast_mode: 'default' | 'custom';
  sast_custom?: CustomToolConfig;
  run_sca: boolean;
  run_package: boolean;
  run_smoke: boolean;
  run_dast: boolean;
}

export interface ProjectMetadata {
  stack: Stack;
  versions: Versions;
  pipeline: Pipeline;
}

export interface JobCreationResponse {
  job_id: string;
  status: string;
  execution_state: string;
  stack: Stack;
  versions: Versions;
  pipeline: Pipeline;
  database?: any;
  warnings?: string[];
  created_at: string;
}