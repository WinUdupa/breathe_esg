import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link, useNavigate } from 'react-router-dom'
import api from '../../api/client'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'
import ScopeSummaryCard from '../../components/ScopeSummaryCard'

export default function UploadSummary() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [submitNote, setSubmitNote] = useState('')
  const [showConfirm, setShowConfirm] = useState(false)
  const [submitError, setSubmitError] = useState('')

  const { data: batch, isLoading } = useQuery({
    queryKey: ['batch', id],
    queryFn: async () => {
      const res = await api.get(`/ingestion/batches/${id}/`)
      // Set to in-review if pending
      if (res.data.status === 'PENDING_REVIEW') {
        await api.post(`/review/batches/${id}/set-in-review/`)
      }
      return res.data
    },
    refetchInterval: 5000,
  })

  const submitMutation = useMutation({
    mutationFn: () => api.post(`/review/batches/${id}/submit/`, { analyst_note: submitNote }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['batch', id] })
      qc.invalidateQueries({ queryKey: ['analyst-batches'] })
      navigate('/analyst')
    },
    onError: (err) => setSubmitError(err.response?.data?.detail || 'Submit failed'),
  })

  if (isLoading) return <Layout><p className="text-gray-500">Loading…</p></Layout>
  if (!batch) return <Layout><p className="text-red-600">Not found</p></Layout>

  const canSubmit = batch.row_stats?.flagged === 0
  const readonly = batch.status === 'ANALYST_APPROVED'

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Link to="/analyst" className="text-blue-600 hover:underline text-sm">← Dashboard</Link>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-lg font-semibold text-gray-900">{batch.file_name}</h2>
            <StatusBadge status={batch.status} />
          </div>
          <p className="text-sm text-gray-500 mb-4">
            {batch.source_type} · Submitted by {batch.uploaded_by_name} · {new Date(batch.uploaded_at).toLocaleString()}
          </p>

          <div className="grid grid-cols-3 gap-4 mb-4">
            {[1, 2, 3].map(scope => (
              <ScopeSummaryCard
                key={scope}
                scope={scope}
                stats={batch.scope_stats?.[`scope_${scope}`]}
                readonly={readonly}
                onReview={
                  batch.scope_stats?.[`scope_${scope}`]?.total > 0
                    ? () => navigate(`/analyst/batch/${id}/scope/${scope}`)
                    : null
                }
              />
            ))}
          </div>

          {batch.total_co2e > 0 && (
            <div className="pt-4 border-t border-gray-100 text-center">
              <span className="text-sm text-gray-600">Total CO₂e: </span>
              <span className="text-2xl font-bold text-gray-900">
                {batch.total_co2e.toLocaleString(undefined, { maximumFractionDigits: 0 })} kg
              </span>
            </div>
          )}
        </div>

        {!readonly && (
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            {!canSubmit ? (
              <p className="text-amber-600 text-sm font-medium">
                ⚠ Resolve all {batch.row_stats?.flagged} flagged rows before submitting.
              </p>
            ) : (
              <div>
                <p className="text-green-600 text-sm font-medium mb-3">✓ All flagged rows resolved. Ready to submit.</p>
                {!showConfirm ? (
                  <button
                    onClick={() => setShowConfirm(true)}
                    className="bg-green-600 text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-green-700"
                  >
                    Submit for Admin Review
                  </button>
                ) : (
                  <div className="flex flex-col gap-3">
                    <textarea
                      placeholder="Optional analyst note…"
                      value={submitNote}
                      onChange={e => setSubmitNote(e.target.value)}
                      className="border border-gray-300 rounded-md px-3 py-2 text-sm w-full"
                      rows={3}
                    />
                    {submitError && <p className="text-red-600 text-sm">{submitError}</p>}
                    <div className="flex gap-3">
                      <button
                        onClick={() => submitMutation.mutate()}
                        disabled={submitMutation.isPending}
                        className="bg-green-600 text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                      >
                        {submitMutation.isPending ? 'Submitting…' : 'Confirm Submit'}
                      </button>
                      <button
                        onClick={() => setShowConfirm(false)}
                        className="bg-gray-100 text-gray-700 px-4 py-2 rounded-md text-sm hover:bg-gray-200"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  )
}
