import { useQuery } from '@tanstack/react-query'
import { useParams, Link, useNavigate } from 'react-router-dom'
import api from '../../api/client'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'
import ScopeSummaryCard from '../../components/ScopeSummaryCard'

export default function UploadSummary() {
  const { id } = useParams()
  const navigate = useNavigate()

  const { data: batch, isLoading } = useQuery({
    queryKey: ['batch', id],
    queryFn: () => api.get(`/ingestion/batches/${id}/`).then(r => r.data),
    refetchInterval: 5000,
  })

  if (isLoading) return <Layout><p className="text-gray-500">Loading…</p></Layout>
  if (!batch) return <Layout><p className="text-red-600">Not found</p></Layout>

  const backHref = batch.submission_id
    ? `/analyst/submission/${batch.submission_id}`
    : '/analyst'

  const readonly = ['ANALYST_APPROVED', 'FINALIZED'].includes(batch.status)

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Link to={backHref} className="text-blue-600 hover:underline text-sm">← Back</Link>
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

        {batch.row_stats?.flagged > 0 && !readonly && (
          <p className="text-sm text-amber-600 font-medium text-center mb-3">
            ⚠ {batch.row_stats.flagged} flagged rows remain — resolve them before the batch can be submitted.
          </p>
        )}

        {batch.row_stats?.rejected > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700 mt-3">
            <strong>{batch.row_stats.rejected} row{batch.row_stats.rejected !== 1 ? 's' : ''} rejected</strong>
            {batch.rejected_co2e > 0 && (
              <span className="ml-2">
                — approx. {Number(batch.rejected_co2e).toLocaleString(undefined, { maximumFractionDigits: 1 })} kg CO₂e excluded from this file's totals.
              </span>
            )}
          </div>
        )}
      </div>
    </Layout>
  )
}
