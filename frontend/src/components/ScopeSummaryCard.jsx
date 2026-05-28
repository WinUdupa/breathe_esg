export default function ScopeSummaryCard({ scope, stats, onReview, readonly }) {
  const flagged = stats?.flagged || 0
  const total = stats?.total || 0
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 flex flex-col gap-2">
      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Scope {scope}</div>
      <div className="text-2xl font-bold text-gray-900">{total} rows</div>
      {flagged > 0 ? (
        <div className="text-amber-600 text-sm font-medium">⚠ {flagged} flagged</div>
      ) : (
        <div className="text-green-600 text-sm font-medium">{total > 0 ? '✓ All clean' : '—'}</div>
      )}
      {onReview && total > 0 && (
        <button
          onClick={onReview}
          className="mt-2 px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
        >
          {readonly ? 'View' : 'Review'} Scope {scope}
        </button>
      )}
    </div>
  )
}
