import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import api from '../../api/client'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'

const SOURCE_LABELS = { SAP: 'SAP', UTILITY: 'Utility', TRAVEL: 'Travel' }
const SOURCE_ICONS = { SAP: '🏭', UTILITY: '⚡', TRAVEL: '✈️' }
const ALL_TYPES = ['SAP', 'UTILITY', 'TRAVEL']

export default function UserDashboard() {
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: submissions = [], isLoading } = useQuery({
    queryKey: ['submissions'],
    queryFn: () => api.get('/ingestion/submissions/').then(r => r.data),
  })

  const createMutation = useMutation({
    mutationFn: () => api.post('/ingestion/submissions/create/'),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['submissions'] })
      navigate(`/submissions/${res.data.id}`)
    },
  })

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">My Upload Batches</h2>
          <button
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending}
            className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {createMutation.isPending ? 'Creating…' : '+ New Batch'}
          </button>
        </div>

        {isLoading ? (
          <p className="text-gray-500">Loading…</p>
        ) : submissions.length === 0 ? (
          <p className="text-gray-500">No batches yet. Click "New Batch" to get started.</p>
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
                      {new Date(s.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge status={s.status} />
                    <Link
                      to={`/submissions/${s.id}`}
                      className="px-3 py-1.5 bg-gray-100 text-gray-700 text-sm rounded hover:bg-gray-200"
                    >
                      {s.status === 'OPEN' ? 'Manage' : 'View'}
                    </Link>
                  </div>
                </div>

                <div className="flex gap-3">
                  {ALL_TYPES.map(type => {
                    const file = s.files.find(f => f.source_type === type)
                    return (
                      <div
                        key={type}
                        className={`flex-1 rounded-md border px-3 py-2 text-xs ${
                          file ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-gray-50'
                        }`}
                      >
                        <div className="font-medium text-gray-700 mb-0.5">
                          {SOURCE_ICONS[type]} {SOURCE_LABELS[type]}
                        </div>
                        {file ? (
                          <>
                            <div className="text-gray-600 truncate">{file.file_name}</div>
                            <StatusBadge status={file.status} />
                          </>
                        ) : (
                          <div className="text-gray-400">Not uploaded</div>
                        )}
                      </div>
                    )
                  })}
                </div>

                {s.total_rows > 0 && (
                  <div className="mt-2 text-xs text-gray-500">
                    {s.total_rows} rows
                    {s.total_flagged > 0 && (
                      <span className="ml-2 text-amber-600 font-medium">
                        ⚠ {s.total_flagged} flagged
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  )
}
