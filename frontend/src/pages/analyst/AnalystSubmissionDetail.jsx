import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link, useNavigate } from 'react-router-dom'
import api from '../../api/client'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'

const SOURCE_ICONS = { SAP: '🏭', UTILITY: '⚡', TRAVEL: '✈️' }
const SOURCE_LABELS = { SAP: 'SAP Fuel & Procurement', UTILITY: 'Utility Electricity', TRAVEL: 'Corporate Travel' }

export default function AnalystSubmissionDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [submitNote, setSubmitNote] = useState('')
  const [showConfirm, setShowConfirm] = useState(false)
  const [submitError, setSubmitError] = useState('')

  const { data: submission, isLoading } = useQuery({
    queryKey: ['analyst-submission', id],
    queryFn: async () => {
      const res = await api.get(`/ingestion/submissions/${id}/`)
      if (res.data.status === 'PENDING_REVIEW') {
        await api.post(`/review/submissions/${id}/set-in-review/`)
        res.data.status = 'IN_REVIEW'
      }
      return res.data
    },
    refetchInterval: 5000,
  })

  const submitMutation = useMutation({
    mutationFn: () => api.post(`/review/submissions/${id}/submit/`, { analyst_note: submitNote }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['analyst-submissions'] })
      qc.invalidateQueries({ queryKey: ['analyst-submission', id] })
      navigate('/analyst')
    },
    onError: (err) => setSubmitError(err.response?.data?.detail || 'Submit failed'),
  })

  if (isLoading) return <Layout><p className="text-gray-500">Loading…</p></Layout>
  if (!submission) return <Layout><p className="text-red-600">Not found</p></Layout>

  const readonly = submission.status === 'ANALYST_APPROVED'
  const canSubmit = submission.total_flagged === 0 && submission.files.length > 0
  const files = submission.files || []

  // Sum total CO2e across all files (not returned directly — we show per-file details)
  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Link to="/analyst" className="text-blue-600 hover:underline text-sm">← Review Queue</Link>
        </div>

        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Batch #{submission.batch_number}</h2>
            <p className="text-sm text-gray-500 mt-0.5">
              Submitted by {submission.created_by_name} · {new Date(submission.created_at).toLocaleDateString()}
            </p>
          </div>
          <StatusBadge status={submission.status} />
        </div>

        <div className="flex flex-col gap-3 mb-6">
          {files.map(file => (
            <div
              key={file.id}
              className="bg-white border border-gray-200 rounded-lg p-5 flex items-center justify-between"
            >
              <div className="flex items-center gap-4">
                <span className="text-2xl">{SOURCE_ICONS[file.source_type]}</span>
                <div>
                  <div className="font-medium text-gray-900">{SOURCE_LABELS[file.source_type]}</div>
                  <div className="text-sm text-gray-500">{file.file_name}</div>
                  <div className="text-sm text-gray-500 mt-0.5">
                    {file.row_count ?? '—'} rows
                    {file.flagged_count > 0 && (
                      <span className="ml-2 text-amber-600 font-medium">
                        ⚠ {file.flagged_count} flagged
                      </span>
                    )}
                    {file.flagged_count === 0 && file.row_count > 0 && (
                      <span className="ml-2 text-green-600">✓ all clean</span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={file.status} />
                <Link
                  to={`/analyst/batch/${file.id}`}
                  className={`px-4 py-2 text-sm rounded ${
                    readonly
                      ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  }`}
                >
                  {readonly ? 'View' : 'Review'}
                </Link>
              </div>
            </div>
          ))}
        </div>

        {submission.total_flagged > 0 && (
          <div className="text-sm text-amber-600 font-medium mb-4">
            ⚠ {submission.total_flagged} flagged rows must be resolved across all files before submitting.
          </div>
        )}

        {/* Rejected row summary across files */}
        {files.some(f => f.row_stats?.rejected > 0) && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4 text-sm text-red-700">
            <strong>Rejected rows:</strong>{' '}
            {files.filter(f => f.row_stats?.rejected > 0).map(f => (
              <span key={f.id} className="mr-3">
                {f.source_type}: {f.row_stats.rejected} row{f.row_stats.rejected !== 1 ? 's' : ''}
                {f.rejected_co2e > 0 ? ` (${f.rejected_co2e?.toLocaleString(undefined, { maximumFractionDigits: 1 })} kg CO₂e excluded)` : ''}
              </span>
            ))}
          </div>
        )}

        {!readonly && (
          <div className="bg-white border border-gray-200 rounded-lg p-5">
            {canSubmit ? (
              !showConfirm ? (
                <div>
                  <p className="text-green-600 text-sm font-medium mb-3">
                    ✓ All flagged rows resolved. Ready to submit for admin review.
                  </p>
                  <button
                    onClick={() => setShowConfirm(true)}
                    className="bg-green-600 text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-green-700"
                  >
                    Submit for Admin Review
                  </button>
                </div>
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
              )
            ) : (
              <p className="text-amber-600 text-sm font-medium">
                ⚠ Resolve all flagged rows in every file before submitting.
              </p>
            )}
          </div>
        )}

        {readonly && submission.analyst_note && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mt-4 text-sm text-gray-700">
            <strong>Analyst note:</strong> {submission.analyst_note}
          </div>
        )}
      </div>
    </Layout>
  )
}
