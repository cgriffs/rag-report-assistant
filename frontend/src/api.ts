export interface DocumentInfo {
  name: string;
  chunks: number;
}

export interface Citation {
  ref: number;
  document: string;
  chunk_id: string;
  score: number;
  excerpt: string;
}

export interface AskResponse {
  answer: string;
  mode: string;
  citations: Citation[];
}

const BASE = "/api";

export async function fetchDocuments(): Promise<DocumentInfo[]> {
  const response = await fetch(`${BASE}/documents`);
  if (!response.ok) throw new Error("Could not load documents");
  return (await response.json()) as DocumentInfo[];
}

export async function uploadDocument(file: File): Promise<DocumentInfo> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${BASE}/documents`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    const detail = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(detail?.detail ?? "Upload failed");
  }
  return (await response.json()) as DocumentInfo;
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const response = await fetch(`${BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) throw new Error("Question failed");
  return (await response.json()) as AskResponse;
}
