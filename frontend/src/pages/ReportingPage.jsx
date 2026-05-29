import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import Layout from '../components/Layout'

const SCOPE_COLORS = {
  1: 'bg-blue-100 text-blue-800',
  2: 'bg-green-100 text-green-800',
  3: 'bg-purple-100 text-purple-800',
}

function fmt(n) {
  if (n == null) return '—'
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: 1 })
}

export default function ReportingPage() {
  const [periodId, setPeriodId] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['reporting', periodId],
    queryFn: () =>
      api.get(`/reporting/summary/${periodId ? `?period_id=${periodId}` : ''}`).then(r => r.data),
  })

  const periods = data?.periods || []

  return (
    <Layout>
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">Emissions Report</h2>
          <select
            value={periodId}
            onChange={e => setPeriodId(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm text-gray-700"
          >
            <option value="">All periods</option>
            {periods.map(p => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.start_date} – {p.end_date}){p.is_locked ? ' 🔒' : ''}
              </option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <p className="text-gray-500">Loading…</p>
        ) : !data ? null : (
          <>
            {/* Summary cards */}
            <div className="grid grid-cols-4 gap-4 mb-6">
              {[
                { label: 'Total CO₂e', value: fmt(data.total_co2e_kg) + ' kg', sub: `${data.total_rows} rows` },
                { label: 'Scope 1', value: fmt(data.by_scope.scope_1.co2e_kg) + ' kg', sub: `${data.by_scope.scope_1.rows} rows` },
                { label: 'Scope 2', value: fmt(data.by_scope.scope_2.co2e_kg) + ' kg', sub: `${data.by_scope.scope_2.rows} rows` },
                { label: 'Scope 3', value: fmt(data.by_scope.scope_3.co2e_kg) + ' kg', sub: `${data.by_scope.scope_3.rows} rows` },
              ].map(card => (
                <div key={card.label} className="bg-white border border-gray-200 rounded-lg p-4">
                  <div className="text-xs text-gray-500 mb-1">{card.label}</div>
                  <div className="text-lg font-bold text-gray-900">{card.value}</div>
                  <div className="text-xs text-gray-400">{card.sub}</div>
                </div>
              ))}
            </div>

            {/* Rejected row banner */}
            {data.rejected.rows > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-start gap-3">
                <span className="text-red-500 text-lg">⚠</span>
                <div>
                  <span className="font-medium text-red-700">
                    {data.rejected.rows} row{data.rejected.rows !== 1 ? 's' : ''} rejected
                  </span>
                  <span className="text-red-600 text-sm ml-2">
                    — approx. {fmt(data.rejected.co2e_kg)} kg CO₂e excluded from totals above.
                    These rows were intentionally rejected by the analyst during review.
                  </span>
                </div>
              </div>
            )}

            {/* Breakdown by source */}
            {data.by_source.length > 0 ? (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-100 font-medium text-gray-700 text-sm">
                  Breakdown by Source
                </div>
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="text-left px-5 py-3 font-medium text-gray-600">Source</th>
                      <th className="text-left px-5 py-3 font-medium text-gray-600">Scope</th>
                      <th className="text-right px-5 py-3 font-medium text-gray-600">Rows</th>
                      <th className="text-right px-5 py-3 font-medium text-gray-600">CO₂e (kg)</th>
                      <th className="text-right px-5 py-3 font-medium text-gray-600">% of Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.by_source.map((row, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-5 py-3 text-gray-900">{row.label}</td>
                        <td className="px-5 py-3">
                          <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${SCOPE_COLORS[row.scope]}`}>
                            Scope {row.scope}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-right text-gray-600">{row.rows}</td>
                        <td className="px-5 py-3 text-right font-medium text-gray-900">{fmt(row.co2e_kg)}</td>
                        <td className="px-5 py-3 text-right text-gray-500">
                          {data.total_co2e_kg > 0
                            ? ((row.co2e_kg / data.total_co2e_kg) * 100).toFixed(1) + '%'
                            : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-gray-50 border-t border-gray-200">
                    <tr>
                      <td colSpan={3} className="px-5 py-3 font-semibold text-gray-900">Total</td>
                      <td className="px-5 py-3 text-right font-bold text-gray-900">{fmt(data.total_co2e_kg)}</td>
                      <td className="px-5 py-3 text-right text-gray-600">100%</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            ) : (
              <div className="bg-white border border-gray-200 rounded-lg p-8 text-center text-gray-500">
                No finalized emissions data yet for the selected period.
              </div>
            )}
          </>
        )}
      </div>
    </Layout>
  )
}
