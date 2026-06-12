"use client";

import { useState, useMemo } from "react";
import { heatmapDisplay } from "@/lib/labels";

interface Props {
  tickers: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
}

export default function TickerSelector({ tickers, selected, onChange }: Props) {
  const [expanded, setExpanded] = useState(false);

  const selectedSet = useMemo(() => new Set(selected), [selected]);
  const allSelected = selected.length === tickers.length;
  const noneSelected = selected.length === 0;

  const toggle = (ticker: string) => {
    if (selectedSet.has(ticker)) {
      onChange(selected.filter(t => t !== ticker));
    } else {
      onChange([...selected, ticker]);
    }
  };

  const selectAll = () => onChange([...tickers]);
  const selectNone = () => onChange([]);

  if (!expanded) {
    return (
      <div className="flex items-center gap-3">
        <button
          onClick={() => setExpanded(true)}
          className="text-sm text-gray-400 hover:text-accent transition-colors flex items-center gap-1.5"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="6 9 12 15 18 9" />
          </svg>
          Select Tickers ({selected.length}/{tickers.length})
        </button>
      </div>
    );
  }

  return (
    <div className="rounded border border-border bg-surface p-3 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-300">
          Select Tickers ({selected.length}/{tickers.length})
        </span>
        <button
          onClick={() => setExpanded(false)}
          className="text-gray-500 hover:text-gray-300 transition-colors"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="18 15 12 9 6 15" />
          </svg>
        </button>
      </div>

      <div className="flex gap-2">
        <button
          onClick={selectAll}
          disabled={allSelected}
          className="text-xs px-2 py-1 rounded bg-accent/20 text-accent hover:bg-accent/30 disabled:opacity-40 transition-colors"
        >
          All
        </button>
        <button
          onClick={selectNone}
          disabled={noneSelected}
          className="text-xs px-2 py-1 rounded bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-40 transition-colors"
        >
          None
        </button>
      </div>

      <div className="flex flex-wrap gap-1.5 max-h-[200px] overflow-y-auto">
        {tickers.map(ticker => {
          const isSelected = selectedSet.has(ticker);
          const label = heatmapDisplay(ticker);
          return (
            <button
              key={ticker}
              onClick={() => toggle(ticker)}
              className={`text-xs px-2 py-1 rounded border transition-colors ${
                isSelected
                  ? "bg-accent/20 border-accent/40 text-accent"
                  : "bg-gray-800 border-gray-700 text-gray-500 hover:text-gray-300"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
