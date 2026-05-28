import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../../api/client'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'

const SOURCE_ICONS = { SAP: '🏭', UTILITY: '⚡', TRAVEL: '✈️' }

export default function AnalystDashboard() {
  const { data: batches = [], isLoading } = useQuery({
    queryKey: ['analyst-batches'],
    queryFn: () => api.get('/ingestion/batches/').then(r => r.data),
    refetchInterval: 10000,
  })

  const sorted = [...batches].sort((a, b) => new Date(a.uploaded_at) - new Date(b.uploaded_at))

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Review Queue</h2>
        {isLoading ? (
          <p className="text-gray-500">Loading…</p>
        ) : sorted.length === 0 ? (
          <p className="text-gray-500">No uploads pending review.</p>
        ) : (
          <div className="grid gap-4">
            {sorted.map(b => (
              <div key={b.id} className="bg-white border border-gray-200 rounded-lg p-5 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <span className="text-2xl">{SOURCE_ICONS[b.source_type] || '📄'}</span>
                  <div>
                    <div className="font-medium text-gray-900">{b.file_name}</div>
                    <div className="text-sm text-gray-500">
                      {b.uploaded_by_name} · {new Date(b.uploaded_at).toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-500 mt-1">
                      {b.row_count} rows
                      {b.row_stats?.flagged > 0 && (
                        <span className="ml-2 text-amber-600 font-medium">
                          ⚠ {b.row_stats.flagged} flagged
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={b.status} />
                  {['PENDING_REVIEW', 'IN_REVIEW'].includes(b.status) ? (
                    <Link
                      to={`/analyst/batch/${b.id}`}
                      className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                    >
                      Review
                    </Link>
                  ) : (
                    <Link
                      to={`/analyst/batch/${b.id}`}
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
