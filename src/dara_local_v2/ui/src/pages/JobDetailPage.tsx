import Plot from 'react-plotly.js'
import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import StatusBadge from '../components/StatusBadge'
import type { JobDetail, SolutionResult } from '../types/jobs'
import { fetchJSON } from '../utils/api'

function formatNumber(value: number, fractionDigits = 2) {
  if (Number.isNaN(value)) {
    return '—'
  }
  return value.toFixed(fractionDigits)
}

function formatDateTime(value?: string | null) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

function PhaseTable({ solution }: { solution: SolutionResult }) {
  const { phases_table: table } = solution
  if (!table.rows.length) {
    return <p className="muted-text">Phase table not available.</p>
  }
  return (
    <div className="phase-table-wrapper">
      <table className="phase-table">
        <thead>
          <tr>
            {table.columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {table.columns.map((column) => (
                <td key={column}>{row[column] ?? '—'}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const [detail, setDetail] = useState<JobDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!jobId) {
      setError('Job ID missing from URL.')
      setLoading(false)
      return
    }
    let active = true
    async function loadDetail() {
      try {
        setLoading(true)
        setError(null)
        const data = await fetchJSON<JobDetail>(`/api/jobs/${jobId}`)
        if (active) {
          setDetail(data)
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : 'Unable to load job detail')
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadDetail()
    return () => {
      active = false
    }
  }, [jobId])

  const diagnostics = detail?.diagnostics
  const solutions = detail?.solutions ?? []

  const job = detail?.job
  const summaryItems = useMemo(() => {
    if (!job) return []
    return [
      { label: 'User', value: job.user },
      { label: 'Pattern', value: job.pattern_filename },
      { label: 'Database', value: job.database },
      { label: 'Created', value: formatDateTime(job.created_at) },
      { label: 'Started', value: formatDateTime(job.started_at) },
      { label: 'Finished', value: formatDateTime(job.finished_at) },
      { label: 'Phases fetched', value: job.num_phases },
    ]
  }, [job])

  return (
    <div className="page-stack">
      <div className="section-card">
        <div className="form-actions" style={{ marginBottom: '1rem' }}>
          <div>
            <p className="eyebrow">Job detail</p>
            <h3>{jobId}</h3>
          </div>
          <div className="status-links">
            <Link to="/results">Back to queue</Link>
          </div>
        </div>

        {error && <div className="error-panel">{error}</div>}
        {!error && loading && <div className="loading-panel">Loading job…</div>}

        {detail && (
          <div className="detail-grid">
            <div className="section-card" style={{ boxShadow: 'none', border: '1px solid rgba(226,232,240,0.7)' }}>
              <div className="summary-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <p className="eyebrow">Status</p>
                  <StatusBadge status={detail.job.status} />
                </div>
                {detail.job.error_message && <span className="helper-text">{detail.job.error_message}</span>}
              </div>
              <ul className="summary-list">
                {summaryItems.map((item) => (
                  <li key={item.label}>
                    <span>{item.label}</span>
                    <span>{item.value}</span>
                  </li>
                ))}
              </ul>
            </div>

            {diagnostics && (
              <div className="section-card" style={{ boxShadow: 'none', border: '1px solid rgba(226,232,240,0.7)' }}>
                <p className="eyebrow">Diagnostics</p>
                <div className="diagnostics-grid">
                  <div className="diagnostic-card">
                    <span>2θ range</span>
                    {diagnostics.two_theta_min.toFixed(1)} – {diagnostics.two_theta_max.toFixed(1)}
                  </div>
                  <div className="diagnostic-card">
                    <span>Intensity</span>
                    {formatNumber(diagnostics.intensity_min, 0)} – {formatNumber(diagnostics.intensity_max, 0)}
                  </div>
                  <div className="diagnostic-card">
                    <span>Points</span>
                    {diagnostics.num_points}
                  </div>
                </div>
                <p className="muted-text" style={{ marginTop: '0.5rem' }}>
                  Checks: {Object.entries(diagnostics.checks).map(([key, value]) => `${key}:${value}`).join(', ')}
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {detail && (
        <div className="section-card">
          <p className="eyebrow">Solutions</p>
          <h3>Refined fits</h3>
          {solutions.length === 0 ? (
            <p className="muted-text">
              {detail.job.status === 'FAILED'
                ? 'Job failed before producing solutions.'
                : detail.job.status === 'COMPLETED'
                  ? 'Job completed but no solutions were found that passed the filters. Try relaxing database filters or checking the pattern quality.'
                  : 'Solutions will appear here after the worker completes this job.'}
            </p>
          ) : (
            <div className="solutions-grid">
              {solutions.map((solution) => (
                <div key={solution.index} className="solution-card">
                  <div>
                    <p className="eyebrow">Solution #{solution.index}</p>
                    <h4>Rwp {formatNumber(solution.rwp, 3)}</h4>
                    <p className="muted-text">{solution.num_phases} phases</p>
                  </div>
                  <div className="plot-wrapper">
                    <Plot
                      data={Array.isArray((solution.plotly_figure as { data?: any[] }).data)
                        ? (solution.plotly_figure as { data?: any[] }).data
                        : []}
                      layout={{
                        height: 320,
                        margin: { t: 32, r: 12, b: 60, l: 48 },
                        ...(solution.plotly_figure as { layout?: Record<string, unknown> }).layout,
                      }}
                      frames={(solution.plotly_figure as { frames?: any[] }).frames}
                      config={{ displaylogo: false, responsive: true }}
                      style={{ width: '100%', height: '100%' }}
                    />
                  </div>
                  <PhaseTable solution={solution} />
                  <a
                    className="download-link"
                    href={`/api/jobs/${jobId}/download/${solution.index}/zip`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Download report ZIP
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default JobDetailPage
