import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../../api/client'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'

const SOURCE_ICONS = { SAP: '🏭', UTILITY: '⚡', TRAVEL: '✈️' }

export default function AnalystDashboard() {
  const { data: submissions = [], isLoading } = useQuery({
    queryKey: ['analyst-submissions'],
    queryFn: () => api.get('/ingestion/submissions/').then(r => r.data),
    refetchInterval: 10000,
  })

  const sorted = [...submissions].sort((a, b) => new Date(a.created_at) - new Date(b.created_at))

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Review Queue</h2>
        {isLoading ? (
          <p className="text-gray-500">Loading…</p>
        ) : sorted.length === 0 ? (
          <p className="text-gray-500">No batches pending review.</p>
        ) : (
          <div className="flex flex-col gap-4">
            {sorted.map(s => (
              <div key={s.id} className="bg-white border border-gray-200 rounded-lg p-5">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <span className="text-base font-semibold text-gray-900">
                      Batch #{s.batch_number}
                    </span>
                    <span className="ml-3 text-sm text-gray-500">
                      Submitted by {s.created_by_name} · {new Date(s.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge status={s.status} />
                    <Link
                      to={`/analyst/submission/${s.id}`}
                      className={`px-4 py-2 text-sm rounded ${
                        ['PENDING_REVIEW', 'IN_REVIEW'].includes(s.status)
                          ? 'bg-blue-600 text-white hover:bg-blue-700'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {['PENDING_REVIEW', 'IN_REVIEW'].includes(s.status) ? 'Review' : 'View'}
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

                <div className="text-sm text-gray-500">
                  {s.total_rows} rows
                  {s.total_flagged > 0 && (
                    <span className="ml-2 text-amber-600 font-medium">
                      ⚠ {s.total_flagged} flagged
                    </span>
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
