import type { JobStatus } from '../types/jobs'

const statusMap: Record<Exclude<JobStatus, 'FAILED'> | 'FAILED', { label: string; className: string }> = {
  PENDING: { label: 'Pending', className: 'badge badge-pending' },
  RUNNING: { label: 'Running', className: 'badge badge-running' },
  COMPLETED: { label: 'Completed', className: 'badge badge-completed' },
  FAILED: { label: 'Failed', className: 'badge badge-failed' },
}

interface StatusBadgeProps {
  status: JobStatus
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = statusMap[status]
  return <span className={config.className}>{config.label}</span>
}

export default StatusBadge
