import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link, useNavigate } from 'react-router-dom'
import api from '../../api/client'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'
import FlagBadge from '../../components/FlagBadge'
import RowDetailPanel from './RowDetailPanel'

export default function ScopeRowView({ readonly = false }) {
  const { id, scope } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [selectedRow, setSelectedRow] = useState(null)
  const [page, setPage] = useState(1)

  const { data: batch } = useQuery({
    queryKey: ['batch', id],
    queryFn: () => api.get(`/ingestion/batches/${id}/`).then(r => r.data),
  })

  const { data: rowsData, isLoading } = useQuery({
    queryKey: ['rows', id, scope, page],
    queryFn: () => api.get(`/review/rows/?batch_id=${id}&scope=${scope}&page=${page}`).then(r => r.data),
    keepPreviousData: true,
  })

  const bulkAcceptMutation = useMutation({
    mutationFn: () => api.post('/review/bulk-accept/', { batch_id: id, scope: parseInt(scope) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rows', id] })
      qc.invalidateQueries({ queryKey: ['batch', id] })
    },
  })

  const rows = rowsData?.results || []
  const totalCount = rowsData?.count || 0
  const pageSize = 20
  const totalPages = Math.ceil(totalCount / pageSize)

  const scopeStats = batch?.scope_stats?.[`scope_${scope}`]
  const pendingCount = scopeStats?.pending || 0
  const flaggedCount = scopeStats?.flagged || 0

  const navScopes = [1, 2, 3].filter(s => (batch?.scope_stats?.[`scope_${s}`]?.total || 0) > 0)

  return (
    <Layout>
      <div className="max-w-7xl mx-auto flex gap-6">
        {/* Main table */}
        <div className="flex-1">
          <div className="flex items-center justify-between mb-4">
            <div>
              <Link to={`${readonly ? '/admin' : '/analyst'}/batch/${id}`} className="text-blue-600 hover:underline text-sm">
                ← Back to Summary
              </Link>
              <h2 className="text-lg font-semibold text-gray-900 mt-1">Scope {scope} Rows</h2>
              <p className="text-sm text-gray-500">Showing {rows.length} of {totalCount} rows</p>
            </div>
            {!readonly && pendingCount > 0 && (
              <button
                onClick={() => bulkAcceptMutation.mutate()}
                disabled={bulkAcceptMutation.isPending}
                className="px-4 py-2 bg-blue-50 text-blue-700 border border-blue-200 rounded-md text-sm font-medium hover:bg-blue-100 disabled:opacity-50"
              >
                Accept All {pendingCount} Clean Rows
              </button>
            )}
          </div>

          {isLoading ? (
            <p className="text-gray-500">Loading…</p>
          ) : (
            <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-gray-600 w-12">Row</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Date</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Type</th>
                    <th className="text-right px-4 py-3 font-medium text-gray-600">Qty</th>
                    <th className="text-right px-4 py-3 font-medium text-gray-600">CO₂e (kg)</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Flags</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                    <th className="px-4 py-3 w-20"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {rows.map(row => (
                    <tr
                      key={row.id}
                      className={`hover:bg-gray-50 ${row.status === 'FLAGGED' ? 'bg-amber-50 border-l-2 border-amber-400' : ''} ${selectedRow?.id === row.id ? 'bg-blue-50' : ''}`}
                    >
                      <td className="px-4 py-3 text-gray-500">{row.row_number}</td>
                      <td className="px-4 py-3 text-gray-600 text-xs">{row.activity_period_start || row.raw_date_text}</td>
                      <td className="px-4 py-3 text-gray-700 font-mono text-xs">{row.activity_subtype}</td>
                      <td className="px-4 py-3 text-right text-gray-600">
                        {row.normalized_quantity != null
                          ? `${row.normalized_quantity.toLocaleString(undefined, { maximumFractionDigits: 1 })} ${row.normalized_unit}`
                          : '—'}
                      </td>
                      <td className="px-4 py-3 text-right font-medium text-gray-900">
                        {row.co2e_kg != null
                          ? row.co2e_kg.toLocaleString(undefined, { maximumFractionDigits: 1 })
                          : '—'}
                      </td>
                      <td className="px-4 py-3"><FlagBadge flags={row.flags} /></td>
                      <td className="px-4 py-3"><StatusBadge status={row.status} /></td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => setSelectedRow(row)}
                          className="text-blue-600 hover:underline text-xs"
                        >
                          Review
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {totalPages > 1 && (
                <div className="border-t border-gray-100 px-4 py-3 flex items-center justify-between">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="text-sm text-blue-600 hover:underline disabled:text-gray-400"
                  >
                    Previous
                  </button>
                  <span className="text-sm text-gray-500">Page {page} of {totalPages}</span>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="text-sm text-blue-600 hover:underline disabled:text-gray-400"
                  >
                    Next
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Scope sidebar */}
        <div className="w-44 shrink-0">
          <div className="bg-white border border-gray-200 rounded-lg p-4 sticky top-4">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Scopes</div>
            {[1, 2, 3].map(s => {
              const ss = batch?.scope_stats?.[`scope_${s}`]
              if (!ss || ss.total === 0) return null
              const isActive = parseInt(scope) === s
              return (
                <button
                  key={s}
                  onClick={() => navigate(`${readonly ? '/admin' : '/analyst'}/batch/${id}/scope/${s}`)}
                  className={`w-full text-left px-3 py-2 rounded-md mb-1 text-sm ${isActive ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700 hover:bg-gray-50'}`}
                >
                  Scope {s}
                  {ss.flagged > 0 && (
                    <span className="ml-1 text-amber-500">⚠ {ss.flagged}</span>
                  )}
                  {ss.flagged === 0 && ss.total > 0 && (
                    <span className="ml-1 text-green-500">✓</span>
                  )}
                </button>
              )
            })}
            <hr className="my-3 border-gray-200" />
            <Link
              to={`${readonly ? '/admin' : '/analyst'}/batch/${id}`}
              className="text-xs text-blue-600 hover:underline"
            >
              ← Summary
            </Link>
          </div>
        </div>
      </div>

      {selectedRow && (
        <RowDetailPanel
          row={selectedRow}
          batchId={id}
          readonly={readonly}
          onClose={() => setSelectedRow(null)}
        />
      )}
    </Layout>
  )
}
