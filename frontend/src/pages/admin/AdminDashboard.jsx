import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../../api/client'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'

const SOURCE_ICONS = { SAP: '🏭', UTILITY: '⚡', TRAVEL: '✈️' }

export default function AdminDashboard() {
  const { data: submissions = [], isLoading } = useQuery({
    queryKey: ['admin-submissions'],
    queryFn: () => api.get('/ingestion/submissions/').then(r => r.data),
    refetchInterval: 10000,
  })

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Admin Review</h2>
        {isLoading ? (
          <p className="text-gray-500">Loading…</p>
        ) : submissions.length === 0 ? (
          <p className="text-gray-500">No batches awaiting finalization.</p>
        ) : (
          <div className="flex flex-col gap-4">
            {submissions.map(s => (
              <div key={s.id} className="bg-white border border-gray-200 rounded-lg p-5">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <span className="text-base font-semibold text-gray-900">
                      Batch #{s.batch_number}
                    </span>
                    <span className="ml-3 text-sm text-gray-500">
                      {s.created_by_name} · {new Date(s.created_at).toLocaleDateString()}
                    </span>
                    {s.reviewed_by_name && (
                      <span className="ml-2 text-sm text-gray-500">
                        · Reviewed by {s.reviewed_by_name}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge status={s.status} />
                    <Link
                      to={`/admin/submission/${s.id}`}
                      className={`px-4 py-2 text-sm rounded ${
                        s.status === 'ANALYST_APPROVED'
                          ? 'bg-blue-600 text-white hover:bg-blue-700'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {s.status === 'ANALYST_APPROVED' ? 'Review & Finalize' : 'View'}
                    </Link>
                  </div>
                </div>

                <div className="flex gap-2 mb-2">
                  {s.files.map(f => (
                    <span
                      key={f.id}
                      className="inline-flex items-center gap-1 text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded"
                    >
                      {SOURCE_ICONS[f.source_type]} {f.source_type}
                    </span>
                  ))}
                </div>

                <div className="text-sm text-gray-500">{s.total_rows} rows</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  )
}
