import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link, useNavigate } from 'react-router-dom'
import api from '../../api/client'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'
import ScopeSummaryCard from '../../components/ScopeSummaryCard'

export default function AdminBatchView() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showConfirm, setShowConfirm] = useState(false)
  const [finalizeError, setFinalizeError] = useState('')

  const { data: batch, isLoading } = useQuery({
    queryKey: ['batch', id],
    queryFn: () => api.get(`/ingestion/batches/${id}/`).then(r => r.data),
  })

  const finalizeMutation = useMutation({
    mutationFn: () => api.post(`/admin/batches/${id}/finalize/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['batch', id] })
      qc.invalidateQueries({ queryKey: ['admin-batches'] })
      navigate('/admin')
    },
    onError: (err) => setFinalizeError(err.response?.data?.detail || 'Finalize failed'),
  })

  if (isLoading) return <Layout><p className="text-gray-500">Loading…</p></Layout>
  if (!batch) return <Layout><p className="text-red-600">Not found</p></Layout>

  const canFinalize = batch.status === 'ANALYST_APPROVED'

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Link to="/admin" className="text-blue-600 hover:underline text-sm">← Dashboard</Link>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-lg font-semibold text-gray-900">{batch.file_name}</h2>
            <StatusBadge status={batch.status} />
          </div>
          <p className="text-sm text-gray-500 mb-4">
            {batch.source_type} · Uploaded by {batch.uploaded_by_name} · {new Date(batch.uploaded_at).toLocaleString()}
          </p>
          {batch.reviewed_by_name && (
            <p className="text-sm text-gray-500 mb-4">
              Analyst: {batch.reviewed_by_name} · Reviewed {batch.reviewed_at && new Date(batch.reviewed_at).toLocaleString()}
            </p>
          )}

          <div className="grid grid-cols-3 gap-4 mb-4">
            {[1, 2, 3].map(scope => (
              <ScopeSummaryCard
                key={scope}
                scope={scope}
                stats={batch.scope_stats?.[`scope_${scope}`]}
                readonly
                onReview={
                  batch.scope_stats?.[`scope_${scope}`]?.total > 0
                    ? () => navigate(`/admin/batch/${id}/scope/${scope}`)
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

        {canFinalize && (
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            {!showConfirm ? (
              <button
                onClick={() => setShowConfirm(true)}
                className="bg-gray-900 text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-gray-700"
              >
                Finalize Upload
              </button>
            ) : (
              <div>
                <p className="text-red-700 font-medium text-sm mb-4">
                  ⚠ You are finalizing this upload. All records will be permanently locked. This action cannot be undone.
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
