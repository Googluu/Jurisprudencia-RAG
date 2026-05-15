"use client";

import type { SourceDocument } from "@/lib/types";

const SECTION_COLORS: Record<string, string> = {
  encabezado: "bg-slate-100 text-slate-700 border-slate-300",
  antecedentes: "bg-blue-50 text-blue-700 border-blue-300",
  consideraciones: "bg-amber-50 text-amber-700 border-amber-300",
  decision: "bg-green-50 text-green-700 border-green-300",
};

const SECTION_LABELS: Record<string, string> = {
  encabezado: "Encabezado",
  antecedentes: "Antecedentes",
  consideraciones: "Consideraciones",
  decision: "Decisión",
};

interface Props {
  source: SourceDocument;
  index: number;
}

export default function SourceCard({ source, index }: Props) {
  const colorClass = SECTION_COLORS[source.section_type] ?? "bg-gray-50 text-gray-700 border-gray-300";
  const sectionLabel = SECTION_LABELS[source.section_type] ?? source.section_type;
  const relevance = Math.round(source.rrf_score * 10000) / 10000;

  return (
    <div className="border border-slate-200 rounded-lg p-3 text-sm bg-white hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="shrink-0 w-5 h-5 rounded-full bg-slate-700 text-white text-xs flex items-center justify-center font-medium">
            {index}
          </span>
          <span className="font-medium text-slate-800 truncate text-xs" title={source.source_file}>
            {source.doc_id}
          </span>
        </div>
        <span className="shrink-0 text-xs text-slate-400 font-mono">
          {relevance.toFixed(4)}
        </span>
      </div>

      <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-medium mb-2 ${colorClass}`}>
        <span>{sectionLabel}</span>
        {source.section_name && source.section_name !== source.section_type && (
          <>
            <span className="opacity-40">—</span>
            <span className="truncate max-w-40" title={source.section_name}>
              {source.section_name}
            </span>
          </>
        )}
      </div>

      <p className="text-slate-600 text-xs leading-relaxed line-clamp-3">
        {source.chunk_text}
      </p>
    </div>
  );
}
