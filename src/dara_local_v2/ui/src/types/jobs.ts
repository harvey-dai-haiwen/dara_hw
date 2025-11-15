export type JobStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'

export interface JobSummary {
  job_id: string
  user: string
  pattern_filename: string
  database: string
  status: JobStatus
  num_phases: number
  created_at: string
  started_at?: string | null
  finished_at?: string | null
  error_message?: string | null
}

export interface Diagnostics {
  two_theta_min: number
  two_theta_max: number
  intensity_min: number
  intensity_max: number
  num_points: number
  checks: Record<string, string>
}

export interface PhaseTable {
  columns: string[]
  rows: Array<Record<string, string | number | null>>
}

export interface SolutionResult {
  index: number
  rwp: number
  num_phases: number
  plotly_figure: Record<string, unknown>
  phases_table: PhaseTable
  report_zip_url: string
}

export interface JobDetail {
  job: JobSummary
  diagnostics?: Diagnostics | null
  solutions: SolutionResult[]
}

export interface JobsResponse {
  jobs: JobSummary[]
  total: number
}
