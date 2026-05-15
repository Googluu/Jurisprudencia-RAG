import type { QueryMetadata, SourceDocument } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface StreamCallbacks {
  onText: (token: string) => void;
  onSources: (sources: SourceDocument[], metadata: QueryMetadata) => void;
  onError: (message: string) => void;
  onDone: () => void;
}

export async function streamQuery(
  question: string,
  topK: number = 8,
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: topK }),
      signal,
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") return;
    callbacks.onError("No se pudo conectar con el servidor. Verifica que el backend esté activo.");
    callbacks.onDone();
    return;
  }

  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText);
    callbacks.onError(`Error del servidor (${response.status}): ${text}`);
    callbacks.onDone();
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    callbacks.onError("Stream no disponible.");
    callbacks.onDone();
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE messages are separated by double newlines
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";

      for (const part of parts) {
        const lines = part.trim().split("\n");
        let eventType = "message";
        let dataLine = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) eventType = line.slice(7).trim();
          if (line.startsWith("data: ")) dataLine = line.slice(6);
        }

        if (!dataLine) continue;

        try {
          const payload = JSON.parse(dataLine);
          if (eventType === "text" || payload.type === "text") {
            callbacks.onText(payload.content ?? "");
          } else if (eventType === "sources" || payload.type === "sources") {
            callbacks.onSources(payload.sources ?? [], payload.metadata ?? {});
          } else if (eventType === "error" || payload.type === "error") {
            callbacks.onError(payload.message ?? "Error desconocido.");
          }
        } catch {
          // malformed JSON — skip
        }
      }
    }
  } catch (err) {
    if ((err as Error).name !== "AbortError") {
      callbacks.onError("Se perdió la conexión con el servidor.");
    }
  } finally {
    callbacks.onDone();
    reader.releaseLock();
  }
}
