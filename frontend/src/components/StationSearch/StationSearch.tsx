/**
 * StationSearch.tsx — Typeahead autocomplete for station selection.
 * Queries /api/stations?q=<input> with debounce.
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import { fetchStations } from "../../services/api";
import type { Station } from "../../types";
import { LINE_COLORS } from "../../types";

interface StationSearchProps {
  label: string;
  value: string;
  onSelect: (name: string) => void;
  placeholder?: string;
  id: string;
}

function LineTag({ line }: { line: string }) {
  const color = (LINE_COLORS as Record<string, string>)[line] ?? "#888";
  return (
    <span
      className="inline-block w-2 h-2 rounded-full flex-shrink-0"
      style={{ backgroundColor: color }}
    />
  );
}

const StationSearch: React.FC<StationSearchProps> = ({
  label, value, onSelect, placeholder = "Search station…", id,
}) => {
  const [query, setQuery] = useState(value);
  const [results, setResults] = useState<Station[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [highlightIdx, setHighlightIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync external value
  useEffect(() => { setQuery(value); }, [value]);

  const search = useCallback((q: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!q.trim()) {
      setResults([]);
      setOpen(false);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetchStations(q);
        setResults(res.stations.slice(0, 8));
        setOpen(res.stations.length > 0);
        setHighlightIdx(0);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 200);
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const q = e.target.value;
    setQuery(q);
    search(q);
  };

  const handleSelect = (station: Station) => {
    setQuery(station.name);
    setResults([]);
    setOpen(false);
    onSelect(station.name);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIdx((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && results[highlightIdx]) {
      handleSelect(results[highlightIdx]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div className="relative">
      <label htmlFor={id} className="block text-xs font-data text-cream/50 mb-1.5 uppercase tracking-widest">
        {label}
      </label>
      <div className="relative">
        <input
          ref={inputRef}
          id={id}
          type="text"
          className="input-field pr-8"
          placeholder={placeholder}
          value={query}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => { if (query) search(query); }}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          autoComplete="off"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={`${id}-listbox`}
        />
        {loading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="w-3.5 h-3.5 border-2 border-cream/20 border-t-cream/60 rounded-full animate-spin" />
          </div>
        )}
      </div>

      {open && results.length > 0 && (
        <ul
          id={`${id}-listbox`}
          role="listbox"
          className="absolute z-50 w-full mt-1 bg-dark-card border border-dark-border rounded-md overflow-hidden shadow-xl animate-fade-in"
        >
          {results.map((s, i) => (
            <li
              key={s.representative_id}
              role="option"
              aria-selected={i === highlightIdx}
              className={`
                flex items-center gap-2.5 px-3 py-2.5 cursor-pointer transition-colors duration-100
                ${i === highlightIdx ? "bg-dark-hover" : "hover:bg-dark-hover"}
                ${i < results.length - 1 ? "border-b border-dark-border" : ""}
              `}
              onMouseDown={() => handleSelect(s)}
              onMouseEnter={() => setHighlightIdx(i)}
            >
              <div className="flex gap-1 flex-shrink-0">
                {s.lines.map((l) => <LineTag key={l} line={l} />)}
              </div>
              <span className="text-cream text-sm truncate flex-1">{s.name}</span>
              {s.is_interchange && (
                <span className="text-mustard text-[10px] font-data flex-shrink-0">XFER</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default StationSearch;
