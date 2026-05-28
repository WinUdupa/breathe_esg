const COLORS = {
  PROCESSING: 'bg-blue-100 text-blue-700',
  FAILED: 'bg-red-100 text-red-700',
  PENDING_REVIEW: 'bg-amber-100 text-amber-700',
  IN_REVIEW: 'bg-blue-100 text-blue-700',
  ANALYST_APPROVED: 'bg-green-100 text-green-700',
  FINALIZED: 'bg-gray-100 text-gray-600',
  REJECTED: 'bg-red-100 text-red-700',
  PENDING: 'bg-blue-100 text-blue-600',
  FLAGGED: 'bg-amber-100 text-amber-700',
  ACCEPTED: 'bg-green-100 text-green-700',
  LOCKED: 'bg-gray-100 text-gray-500',
}

const LABELS = {
  PENDING_REVIEW: 'Pending Review',
  IN_REVIEW: 'In Review',
  ANALYST_APPROVED: 'Analyst Approved',
}

export default function StatusBadge({ status }) {
  const cls = COLORS[status] || 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {LABELS[status] || status}
    </span>
  )
}
