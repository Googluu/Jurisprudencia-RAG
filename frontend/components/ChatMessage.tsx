"use client";

import { useState } from "react";
import type { Message } from "@/lib/types";
import SourceCard from "./SourceCard";

interface Props {
  message: Message;
}

export default function ChatMessage({ message }: Props) {
  const [showSources, setShowSources] = useState(false);
  const isUser = message.role === "user";

  return (
    <div className={`flex flex-col gap-2 ${isUser ? "items-end" : "items-start"}`}>
      {/* Bubble */}
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? "bg-slate-800 text-white rounded-br-sm"
            : "bg-white border border-slate-200 text-slate-800 rounded-bl-sm shadow-sm"
        }`}
      >
        {message.content || (message.isStreaming && <span className="animate-pulse">▍</span>)}
        {message.isStreaming && message.content && (
          <span className="animate-pulse">▍</span>
        )}
        {message.error && (
          <span className="text-red-500">{message.error}</span>
        )}
      </div>

      {/* Sources toggle */}
      {!isUser && message.sources && message.sources.length > 0 && (
        <div className="max-w-[85%] w-full">
          <button
            onClick={() => setShowSources((v) => !v)}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 transition-colors mb-2"
          >
            <svg
              className={`w-3.5 h-3.5 transition-transform ${showSources ? "rotate-90" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
            <span>
              {showSources ? "Ocultar" : "Ver"} {message.sources.length} fuente
              {message.sources.length !== 1 ? "s" : ""}
            </span>
            {message.metadata && (
              <span className="text-slate-400 ml-1">
                · {message.metadata.model} · {Math.round(message.metadata.generation_time_ms)}ms
              </span>
            )}
          </button>

          {showSources && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {message.sources.map((src, i) => (
                <SourceCard key={`${src.doc_id}-${i}`} source={src} index={i + 1} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
