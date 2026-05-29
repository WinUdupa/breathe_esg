import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link, useNavigate } from 'react-router-dom'
import api from '../../api/client'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'
import ScopeSummaryCard from '../../components/ScopeSummaryCard'

const SOURCE_ICONS = { SAP: '🏭', UTILITY: '⚡', TRAVEL: '✈️' }
const SOURCE_LABELS = { SAP: 'SAP Fuel & Procurement', UTILITY: 'Utility Electricity', TRAVEL: 'Corporate Travel' }

export default function AdminSubmissionView() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showConfirm, setShowConfirm] = useState(false)
  const [finalizeError, setFinalizeError] = useState('')
  const [expandedFile, setExpandedFile] = useState(null)

  const { data: submission, isLoading } = useQuery({
    queryKey: ['admin-submission', id],
    queryFn: () => api.get(`/ingestion/submissions/${id}/`).then(r => r.data),
  })

  // Load expanded file's batch detail
  const { data: expandedBatch } = useQuery({
    queryKey: ['batch', expandedFile],
    queryFn: () => api.get(`/ingestion/batches/${expandedFile}/`).then(r => r.data),
    enabled: !!expandedFile,
  })

  const finalizeMutation = useMutation({
    mutationFn: () => api.post(`/admin/submissions/${id}/finalize/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-submissions'] })
      navigate('/admin')
    },
    onError: (err) => setFinalizeError(err.response?.data?.detail || 'Finalize failed'),
  })

  if (isLoading) return <Layout><p className="text-gray-500">Loading…</p></Layout>
  if (!submission) return <Layout><p className="text-red-600">Not found</p></Layout>

  const canFinalize = submission.status === 'ANALYST_APPROVED'
  const files = submission.files || []

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Link to="/admin" className="text-blue-600 hover:underline text-sm">← Admin Dashboard</Link>
        </div>

        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Batch #{submission.batch_number}</h2>
            <p className="text-sm text-gray-500 mt-0.5">
              {submission.created_by_name} · {new Date(submission.created_at).toLocaleDateString()}
              {submission.reviewed_by_name && ` · Reviewed by ${submission.reviewed_by_name}`}
            </p>
          </div>
          <StatusBadge status={submission.status} />
        </div>

        {/* File list */}
        <div className="flex flex-col gap-3 mb-6">
          {files.map(file => (
            <div key={file.id} className="bg-white border border-gray-200 rounded-lg">
              <div className="flex items-center justify-between p-5">
                <div className="flex items-center gap-4">
                  <span className="text-2xl">{SOURCE_ICONS[file.source_type]}</span>
                  <div>
                    <div className="font-medium text-gray-900">{SOURCE_LABELS[file.source_type]}</div>
                    <div className="text-sm text-gray-500">{file.file_name} · {file.row_count ?? '—'} rows</div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={file.status} />
                  <button
                    onClick={() => setExpandedFile(expandedFile === file.id ? null : file.id)}
                    className="px-3 py-1.5 bg-gray-100 text-gray-700 text-sm rounded hover:bg-gray-200"
                  >
                    {expandedFile === file.id ? 'Hide' : 'Inspect'}
                  </button>
                </div>
              </div>

              {expandedFile === file.id && expandedBatch && (
                <div className="border-t border-gray-100 p-5">
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    {[1, 2, 3].map(scope => (
                      <ScopeSummaryCard
                        key={scope}
                        scope={scope}
                        stats={expandedBatch.scope_stats?.[`scope_${scope}`]}
                        readonly
                        onReview={
                          expandedBatch.scope_stats?.[`scope_${scope}`]?.total > 0
                            ? () => navigate(`/admin/batch/${file.id}/scope/${scope}`)
                            : null
                        }
                      />
                    ))}
                  </div>
                  {expandedBatch.total_co2e > 0 && (
                    <div className="text-center text-sm text-gray-600">
                      CO₂e:{' '}
                      <span className="font-semibold text-gray-900">
                        {expandedBatch.total_co2e.toLocaleString(undefined, { maximumFractionDigits: 0 })} kg
                      </span>
                    </div>
                  )}
                  {file.analyst_note && (
                    <div className="mt-3 text-sm text-gray-600 bg-gray-50 rounded p-3">
                      <strong>Analyst note:</strong> {file.analyst_note}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {canFinalize && (
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            {!showConfirm ? (
              <button
                onClick={() => setShowConfirm(true)}
                className="bg-gray-900 text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-gray-700"
              >
                Finalize Batch
              </button>
            ) : (
              <div>
                <p className="text-red-700 font-medium text-sm mb-4">
                  ⚠ Finalizing Batch #{submission.batch_number} will permanently lock all
                  accepted records across all files. This cannot be undone.
                </p>
                {finalizeError && <p className="text-red-600 text-sm mb-3">{finalizeError}</p>}
                <div className="flex gap-3">
                  <button
                    onClick={() => finalizeMutation.mutate()}
                    disabled={finalizeMutation.isPending}
                    className="bg-red-600 text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-red-700 disabled:opacity-50"
                  >
                    {finalizeMutation.isPending ? 'Finalizing…' : 'Finalize'}
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
    </Layout>
  )
}
