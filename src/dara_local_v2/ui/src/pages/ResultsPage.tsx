import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import StatusBadge from '../components/StatusBadge'
import type { JobStatus, JobSummary } from '../types/jobs'
import { fetchJSON } from '../utils/api'

interface JobsResponse {
  jobs: JobSummary[]
  total: number
}

type StatusFilter = JobStatus | 'ALL'

const STATUS_OPTIONS: StatusFilter[] = ['ALL', 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED']

function formatDate(value?: string | null) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

export function ResultsPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')
  const [jobs, setJobs] = useState<JobSummary[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const query = useMemo(() => {
    if (statusFilter === 'ALL') return ''
    return `?status=${statusFilter}`
  }, [statusFilter])

  const fetchJobs = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchJSON<JobsResponse>(`/api/jobs${query}`)
      setJobs(data.jobs)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load jobs')
    } finally {
      setLoading(false)
    }
  }, [query])

  useEffect(() => {
    fetchJobs()
  }, [fetchJobs])

  return (
    <div className="page-stack">
      <div className="section-card">
        <div className="filter-bar">
          <label htmlFor="status-filter">Status</label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
          >
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {status === 'ALL' ? 'All jobs' : status}
              </option>
            ))}
          </select>
          <button type="button" onClick={fetchJobs} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>

        {error && <div className="error-panel">{error}</div>}
        {!error && loading && <div className="loading-panel">Loading jobs…</div>}

        {!loading && !error && (
          <div className="table-card">
            {jobs.length === 0 ? (
              <p className="muted-text">No jobs yet. Submit a search to populate this list.</p>
            ) : (
              <table className="job-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>User</th>
                    <th>Pattern</th>
                    <th>Database</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Finished</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((job) => (
                    <tr key={job.job_id}>
                      <td>
                        <Link to={`/results/${job.job_id}`}>{job.job_id.slice(0, 8)}…</Link>
                      </td>
                      <td>{job.user}</td>
                      <td>{job.pattern_filename}</td>
                      <td>{job.database}</td>
                      <td>
                        <StatusBadge status={job.status} />
                      </td>
                      <td>{formatDate(job.created_at)}</td>
                      <td>{job.finished_at ? formatDate(job.finished_at) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default ResultsPage
