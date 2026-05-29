import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import Layout from '../../components/Layout'

const ACTION_LABELS = {
  ROW_ACCEPTED: 'Row Accepted',
  ROW_REJECTED: 'Row Rejected',
  ROW_EDITED: 'Row Edited',
  ROWS_BULK_ACCEPTED: 'Bulk Accept',
  FILE_UPLOADED: 'File Uploaded',
  FILE_DELETED: 'File Deleted',
  SUBMISSION_SUBMITTED: 'Submitted for Review',
  SUBMISSION_ANALYST_APPROVED: 'Analyst Approved',
  SUBMISSION_FINALIZED: 'Finalized',
  PERIOD_CREATED: 'Period Created',
  PERIOD_LOCKED: 'Period Locked',
}

const ACTION_COLORS = {
  ROW_ACCEPTED: 'bg-green-100 text-green-700',
  ROW_REJECTED: 'bg-red-100 text-red-700',
  ROW_EDITED: 'bg-amber-100 text-amber-700',
  ROWS_BULK_ACCEPTED: 'bg-green-100 text-green-700',
  FILE_UPLOADED: 'bg-blue-100 text-blue-700',
  FILE_DELETED: 'bg-red-100 text-red-700',
  SUBMISSION_SUBMITTED: 'bg-blue-100 text-blue-700',
  SUBMISSION_ANALYST_APPROVED: 'bg-purple-100 text-purple-700',
  SUBMISSION_FINALIZED: 'bg-gray-200 text-gray-700',
  PERIOD_CREATED: 'bg-blue-100 text-blue-700',
  PERIOD_LOCKED: 'bg-gray-200 text-gray-700',
}

function detailSummary(action, detail) {
  if (!detail) return ''
  switch (action) {
    case 'ROW_ACCEPTED':
    case 'ROW_REJECTED':
      return `Row #${detail.row_number} · ${detail.subtype || ''} · ${detail.co2e_kg != null ? detail.co2e_kg.toLocaleString(undefined, { maximumFractionDigits: 1 }) + ' kg' : '—'}${detail.note ? ` — "${detail.note}"` : ''}`
    case 'ROW_EDITED':
      return `Row #${detail.row_number} · ${(detail.changes || []).length} field(s) changed`
    case 'ROWS_BULK_ACCEPTED':
      return `${detail.count} rows · scope ${detail.scope || 'all'}`
    case 'FILE_UPLOADED':
      return `${detail.source_type} — ${detail.file_name} (${detail.row_count ?? '?'} rows)`
    case 'FILE_DELETED':
      return `${detail.source_type} — ${detail.file_name}`
    case 'SUBMISSION_SUBMITTED':
    case 'SUBMISSION_ANALYST_APPROVED':
    case 'SUBMISSION_FINALIZED':
      return `Batch #${detail.batch_number}${detail.note ? ` — "${detail.note}"` : ''}`
    case 'PERIOD_CREATED':
      return `${detail.name} (${detail.start_date} – ${detail.end_date})`
    case 'PERIOD_LOCKED':
      return detail.name
    default:
      return JSON.stringify(detail)
  }
}

export default function AuditLogPage() {
  const [actionFilter, setActionFilter] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['audit-logs', actionFilter, page],
    queryFn: () => {
      const params = new URLSearchParams({ page })
      if (actionFilter) params.set('action', actionFilter)
      return api.get(`/audit/logs/?${params}`).then(r => r.data)
    },
  })

  const entries = data?.results || []
  const totalCount = data?.count || 0

  return (
    <Layout>
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">Audit Trail</h2>
          <select
            value={actionFilter}
            onChange={e => { setActionFilter(e.target.value); setPage(1) }}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm text-gray-700"
          >
            <option value="">All actions</option>
            {Object.entries(ACTION_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <p className="text-gray-500">Loading…</p>
        ) : entries.length === 0 ? (
          <p className="text-gray-500">No audit entries yet.</p>
        ) : (
          <>
            <div className="bg-white border border-gray-200 rounded-lg overflow-hidden mb-4">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-gray-600 w-40">When</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600 w-28">Who</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600 w-40">Action</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Detail</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {entries.map(e => (
                    <tr key={e.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                        {new Date(e.timestamp).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-gray-700 font-mono text-xs">{e.actor}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${ACTION_COLORS[e.action] || 'bg-gray-100 text-gray-700'}`}>
                          {ACTION_LABELS[e.action] || e.action}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600 text-xs">
                        {detailSummary(e.action, e.detail)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between text-sm text-gray-500">
              <span>{totalCount} total entries</span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-40"
                >
                  ← Prev
                </button>
                <span className="px-3 py-1">Page {page}</span>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={!data?.next}
                  className="px-3 py-1 rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-40"
                >
                  Next →
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </Layout>
  )
}
