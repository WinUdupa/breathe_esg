import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../api/client'

export default function RowDetailPanel({ row, batchId, onClose, readonly }) {
  const qc = useQueryClient()
  const [note, setNote] = useState('')
  const [error, setError] = useState('')

  const acceptMutation = useMutation({
    mutationFn: () => api.post(`/review/rows/${row.id}/accept/`, { review_note: note }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rows', batchId] })
      qc.invalidateQueries({ queryKey: ['batch', batchId] })
      onClose()
    },
    onError: (err) => setError(err.response?.data?.detail || 'Error'),
  })

  const rejectMutation = useMutation({
    mutationFn: () => api.post(`/review/rows/${row.id}/reject/`, { review_note: note }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rows', batchId] })
      qc.invalidateQueries({ queryKey: ['batch', batchId] })
      onClose()
    },
    onError: (err) => setError(err.response?.data?.detail || 'Error'),
  })

  const noteRequired = row.status === 'FLAGGED' || !note

  return (
    <div className="fixed inset-0 z-40 flex">
      <div className="flex-1 bg-black/20" onClick={onClose} />
      <div className="w-[480px] bg-white shadow-xl overflow-y-auto border-l border-gray-200 flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="font-semibold text-gray-900">Row {row.row_number} — {row.activity_subtype}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-xl leading-none">×</button>
        </div>

        <div className="flex-1 px-6 py-4 space-y-6">
          {/* Raw Data */}
          <section>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Raw Data</h4>
            <div className="bg-gray-50 rounded-lg p-3 text-xs space-y-1">
              {row.raw_data && Object.entries(row.raw_data).map(([k, v]) => (
                <div key={k} className="flex gap-2">
                  <span className="text-gray-500 min-w-[140px]">{k}:</span>
                  <span className="text-gray-900 font-mono">{v}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Normalization */}
          <section>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">What the System Did</h4>
            <div className="space-y-1 text-sm">
              {row.conversion_display && (
                <div className="bg-blue-50 rounded px-3 py-2 text-blue-800 font-mono text-xs">{row.conversion_display}</div>
              )}
              {row.co2e_display ? (
                <div className="bg-green-50 rounded px-3 py-2 text-green-800 font-mono text-xs">{row.co2e_display}</div>
              ) : (
                <div className="bg-red-50 rounded px-3 py-2 text-red-700 text-xs">CO₂e cannot be calculated</div>
              )}
              {row.emission_factor_detail && (
                <div className="text-xs text-gray-500">
                  Factor: {row.emission_factor_detail.source} {row.emission_factor_detail.year} — {row.emission_factor_detail.value} kgCO₂e/{row.emission_factor_detail.denominator_unit}
                </div>
              )}
            </div>
          </section>

          {/* Flags */}
          {row.flags?.length > 0 && (
            <section>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Flag Explanations</h4>
              <div className="space-y-2">
                {row.flag_messages?.map(f => (
                  <div key={f.code} className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                    <div className="text-xs font-semibold text-amber-700 mb-0.5">{f.code}</div>
                    <div className="text-xs text-amber-800">{f.message}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Edit history */}
          {row.edit_history?.length > 0 && (
            <section>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Edit History</h4>
              {row.edit_history.map((h, i) => (
                <div key={i} className="text-xs text-gray-600 mb-1">
                  <span className="font-medium">{h.changed_by}</span> changed <span className="font-mono">{h.field}</span>: {h.old_value} → {h.new_value}
                </div>
              ))}
            </section>
          )}

          {/* Analyst decision */}
          {!readonly && (
            <section>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Decision</h4>
              <textarea
                placeholder={row.status === 'FLAGGED' ? 'Comment required for flagged rows…' : 'Optional comment…'}
                value={note}
                onChange={e => { setNote(e.target.value); setError('') }}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm mb-3"
                rows={3}
              />
              {error && <p className="text-red-600 text-sm mb-2">{error}</p>}
              <div className="flex gap-3">
                <button
                  onClick={() => acceptMutation.mutate()}
                  disabled={(row.status === 'FLAGGED' && !note.trim()) || acceptMutation.isPending || rejectMutation.isPending}
                  className="flex-1 bg-green-600 text-white py-2 rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                >
                  Accept
                </button>
                <button
                  onClick={() => rejectMutation.mutate()}
                  disabled={!note.trim() || acceptMutation.isPending || rejectMutation.isPending}
                  className="flex-1 bg-red-600 text-white py-2 rounded-md text-sm font-medium hover:bg-red-700 disabled:opacity-50"
                >
                  Reject
                </button>
              </div>
            </section>
          )}

          {/* Readonly: show review decision */}
          {readonly && (row.review_note || row.status) && (
            <section>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Review Decision</h4>
              <div className="text-sm">
                <div className="font-medium">{row.reviewed_by} — {row.status}</div>
                {row.review_note && <div className="text-gray-600 mt-1">{row.review_note}</div>}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}
