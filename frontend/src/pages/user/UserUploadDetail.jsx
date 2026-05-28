import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import api from '../../api/client'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'
import ScopeSummaryCard from '../../components/ScopeSummaryCard'
import FlagBadge from '../../components/FlagBadge'

export default function UserUploadDetail() {
  const { id } = useParams()

  const { data: batch, isLoading } = useQuery({
    queryKey: ['batch', id],
    queryFn: () => api.get(`/ingestion/batches/${id}/`).then(r => r.data),
  })

  const { data: rows } = useQuery({
    queryKey: ['rows', id],
    queryFn: () => api.get(`/review/rows/?batch_id=${id}&page_size=100`).then(r => r.data),
    enabled: !!batch,
  })

  if (isLoading) return <Layout><p className="text-gray-500">Loading…</p></Layout>
  if (!batch) return <Layout><p className="text-red-600">Not found</p></Layout>

  return (
    <Layout>
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Link to="/dashboard" className="text-blue-600 hover:underline text-sm">← Dashboard</Link>
        </div>

        {batch.status === 'REJECTED' && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4 text-red-700">
            <strong>Rejected:</strong> {batch.analyst_note || 'No reason provided'}
          </div>
        )}

        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{batch.file_name}</h2>
              <p className="text-sm text-gray-500">
                {batch.source_type} · Submitted {new Date(batch.uploaded_at).toLocaleString()}
              </p>
            </div>
            <StatusBadge status={batch.status} />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <ScopeSummaryCard scope={1} stats={batch.scope_stats?.scope_1} readonly />
            <ScopeSummaryCard scope={2} stats={batch.scope_stats?.scope_2} readonly />
            <ScopeSummaryCard scope={3} stats={batch.scope_stats?.scope_3} readonly />
          </div>

          {batch.total_co2e > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <span className="text-sm text-gray-600">Total CO₂e: </span>
              <span className="text-lg font-semibold text-gray-900">
                {batch.total_co2e.toLocaleString(undefined, { maximumFractionDigits: 1 })} kg
              </span>
            </div>
          )}
        </div>

        {rows?.results && (
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Row</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Date</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Type</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">CO₂e (kg)</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Flags</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {rows.results.map(row => (
                  <tr key={row.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500">{row.row_number}</td>
                    <td className="px-4 py-3">{row.activity_period_start || row.raw_date_text}</td>
                    <td className="px-4 py-3 text-gray-600">{row.activity_subtype}</td>
                    <td className="px-4 py-3 text-right">
                      {row.co2e_kg != null ? row.co2e_kg.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '—'}
                    </td>
                    <td className="px-4 py-3"><FlagBadge flags={row.flags} /></td>
                    <td className="px-4 py-3"><StatusBadge status={row.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  )
}
