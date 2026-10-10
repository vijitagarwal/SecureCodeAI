export function Pagination({ offset, limit, total, onPage }: { offset: number; limit: number; total: number; onPage: (value: number) => void }) {
  return <nav className="pagination" aria-label="Pagination">
    <button className="secondary small" disabled={offset === 0} onClick={() => onPage(Math.max(0, offset - limit))}>Previous</button>
    <span>{total === 0 ? "0" : `${offset + 1}–${Math.min(total, offset + limit)}`} of {total}</span>
    <button className="secondary small" disabled={offset + limit >= total} onClick={() => onPage(offset + limit)}>Next</button>
  </nav>;
}
