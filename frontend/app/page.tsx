"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ChatInput from "@/components/ChatInput";
import ChatMessage from "@/components/ChatMessage";
import { streamQuery } from "@/lib/api";
import type { Message } from "@/lib/types";

const SUGGESTED_QUESTIONS = [
  "¿Qué criterios usa la Corte para determinar la responsabilidad en contratos de mandato?",
  "¿Cuándo procede el recurso de casación en materia civil?",
  "¿Cómo define la Corte el daño moral en accidentes de tránsito?",
];

let msgCounter = 0;
const nextId = () => `msg-${++msgCounter}`;

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleQuestion = useCallback(async (question: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const userMsg: Message = { id: nextId(), role: "user", content: question };
    const assistantId = nextId();
    const assistantMsg: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setStreaming(true);

    await streamQuery(
      question,
      8,
      {
        onText: (token) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: m.content + token } : m
            )
          );
        },
        onSources: (sources, metadata) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, sources, metadata } : m
            )
          );
        },
        onError: (message) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, error: message, isStreaming: false }
                : m
            )
          );
        },
        onDone: () => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, isStreaming: false } : m
            )
          );
          setStreaming(false);
        },
      },
      controller.signal
    );
  }, []);

  const isEmpty = messages.length === 0;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-4 py-3 flex items-center gap-3 sticky top-0 z-10">
        <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center shrink-0">
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
        </div>
        <div>
          <h1 className="text-sm font-semibold text-slate-800 leading-tight">
            Jurisprudencia CSJ
          </h1>
          <p className="text-xs text-slate-500">
            Sala de Casación Civil · Asistente RAG
          </p>
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6">
          {isEmpty ? (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center gap-6">
              <div>
                <h2 className="text-xl font-semibold text-slate-800 mb-1">
                  Asistente de Jurisprudencia
                </h2>
                <p className="text-sm text-slate-500 max-w-md">
                  Consulta sentencias de la Corte Suprema de Justicia, Sala de
                  Casación Civil. Las respuestas citan el documento y la sección
                  específica de origen.
                </p>
              </div>

              <div className="w-full max-w-md flex flex-col gap-2">
                <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
                  Preguntas sugeridas
                </p>
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => handleQuestion(q)}
                    disabled={streaming}
                    className="text-left text-sm text-slate-600 bg-white border border-slate-200 rounded-xl px-4 py-3 hover:border-slate-400 hover:text-slate-800 transition-all disabled:opacity-40"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-5">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>
      </main>

      {/* Input */}
      <footer className="bg-slate-50 border-t border-slate-200 px-4 py-3 sticky bottom-0">
        <div className="max-w-3xl mx-auto">
          <ChatInput onSubmit={handleQuestion} disabled={streaming} />
          <p className="text-center text-xs text-slate-400 mt-2">
            Las respuestas se generan con base en 100 sentencias de la CSJ · Sala Civil
          </p>
        </div>
      </footer>
    </div>
  );
}
