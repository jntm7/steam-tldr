import { ChevronLeft, ChevronRight } from "lucide-react";

// Page numbers to show: the first, the last and the ones around the current page, with "…" for the gaps
function pageList(page, count) {
  const wanted = new Set([1, count, page - 1, page, page + 1]);
  const numbers = [...wanted].filter((n) => n >= 1 && n <= count).sort((a, b) => a - b);
  return numbers.flatMap((n, i) => (i > 0 && n - numbers[i - 1] > 1 ? [`gap${n}`, n] : [n]));
}

// Previous / numbered / next page buttons
export default function Pagination({ page, count, onChange, className = "" }) {
  return (
    <nav className={`pagination ${className}`} aria-label="Pages">
      <button disabled={page === 1} aria-label="Previous page" onClick={() => onChange(page - 1)}><ChevronLeft size={16} /></button>
      {pageList(page, count).map((item) => (
        typeof item === "string" ? <span key={item} className="gap">…</span> : (
          <button key={item} className={item === page ? "on" : ""} aria-current={item === page ? "page" : undefined} onClick={() => onChange(item)}>{item}</button>
        )
      ))}
      <button disabled={page === count} aria-label="Next page" onClick={() => onChange(page + 1)}><ChevronRight size={16} /></button>
    </nav>
  );
}
