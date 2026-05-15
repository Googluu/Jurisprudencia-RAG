export interface SourceDocument {
  doc_id: string;
  source_file: string;
  section_type: string;
  section_name: string;
  chunk_text: string;
  semantic_score: number;
  lexical_score: number;
  rrf_score: number;
}

export interface QueryMetadata {
  model: string;
  generation_time_ms: number;
  sources_count: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceDocument[];
  metadata?: QueryMetadata;
  isStreaming?: boolean;
  error?: string;
}
