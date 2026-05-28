import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../../api/client'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'

const SOURCE_ICONS = { SAP: '🏭', UTILITY: '⚡', TRAVEL: '✈️' }

export default function AdminDashboard() {
  const { data: batches = [], isLoading } = useQuery({
    queryKey: ['admin-batches'],
    queryFn: () => api.get('/ingestion/batches/').then(r => r.data),
    refetchInterval: 10000,
  })

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Admin Review</h2>
        {isLoading ? (
          <p className="text-gray-500">Loading…</p>
        ) : batches.length === 0 ? (
          <p className="text-gray-500">No uploads awaiting finalization.</p>
        ) : (
          <div className="grid gap-4">
            {batches.map(b => (
              <div key={b.id} className="bg-white border border-gray-200 rounded-lg p-5 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <span className="text-2xl">{SOURCE_ICONS[b.source_type] || '📄'}</span>
                  <div>
                    <div className="font-medium text-gray-900">{b.file_name}</div>
                    <div className="text-sm text-gray-500">
                      {b.uploaded_by_name} · {new Date(b.uploaded_at).toLocaleString()}
                    </div>
                    {b.reviewed_by_name && (
                      <div className="text-sm text-gray-500 mt-0.5">
                        Reviewed by {b.reviewed_by_name} · {b.reviewed_at && new Date(b.reviewed_at).toLocaleDateString()}
                      </div>
                    )}
                    <div className="text-sm text-gray-500">
                      {b.row_count} rows
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={b.status} />
                  {b.status === 'ANALYST_APPROVED' ? (
                    <Link
                      to={`/admin/batch/${b.id}`}
                      className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                    >
                      Review & Finalize
                    </Link>
                  ) : (
                    <Link
                      to={`/admin/batch/${b.id}`}
                      className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded hover:bg-gray-200"
                    >
                      View
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  )
}
