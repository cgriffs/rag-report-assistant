import { useEffect, useRef, useState } from "react";

import type { AskResponse, Citation, DocumentInfo } from "./api";
import { askQuestion, fetchDocuments, uploadDocument } from "./api";

const EXAMPLE_QUESTIONS = [
  "What was the first time fix rate in Q3?",
  "How much were Scope 2 emissions?",
  "When is Project Beacon going live and what is the main risk?",
];

function renderAnswer(answer: string, onCitation: (ref: number) => void) {
  const parts = answer.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    const match = /^\[(\d+)\]$/.exec(part);
    if (match) {
      const ref = Number(match[1]);
      return (
        <button
          key={i}
          className="cite-chip"
          onClick={() => onCitation(ref)}
          title={`See source ${ref}`}
        >
          {ref}
        </button>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

export default function App() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [activeRef, setActiveRef] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const citationRefs = useRef<Record<number, HTMLLIElement | null>>({});

  useEffect(() => {
    fetchDocuments()
      .then(setDocuments)
      .catch(() => setError("Backend not reachable. Is the API running?"));
  }, []);

  async function handleAsk(text: string) {
    if (text.trim().length < 3) return;
    setBusy(true);
    setError(null);
    setActiveRef(null);
    try {
      setResult(await askQuestion(text.trim()));
    } catch {
      setError("Something went wrong asking that question.");
    } finally {
      setBusy(false);
    }
  }

  async function handleUpload(file: File | undefined) {
    if (!file) return;
    setError(null);
    try {
      await uploadDocument(file);
      setDocuments(await fetchDocuments());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  }

  function jumpToCitation(ref: number) {
    setActiveRef(ref);
    citationRefs.current[ref]?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  }

  return (
    <div className="page">
      <header>
        <h1>RAG Report Assistant</h1>
        <p>
          Ask plain language questions of business documents. Every answer
          carries citations back to the source passages.
        </p>
      </header>

      <main>
        <section className="panel">
          <h2>Indexed documents</h2>
          {documents.length === 0 ? (
            <p className="muted">No documents indexed yet.</p>
          ) : (
            <ul className="doc-list">
              {documents.map((doc) => (
                <li key={doc.name}>
                  <span>{doc.name}</span>
                  <span className="muted">{doc.chunks} chunks</span>
                </li>
              ))}
            </ul>
          )}
          <label className="upload">
            Add a document (PDF or Markdown)
            <input
              type="file"
              accept=".pdf,.md,.markdown,.txt"
              onChange={(event) => {
                void handleUpload(event.target.files?.[0]);
                event.target.value = "";
              }}
            />
          </label>
        </section>

        <section className="panel">
          <h2>Ask a question</h2>
          <div className="examples">
            {EXAMPLE_QUESTIONS.map((example) => (
              <button
                key={example}
                className="example"
                onClick={() => {
                  setQuestion(example);
                  void handleAsk(example);
                }}
              >
                {example}
              </button>
            ))}
          </div>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void handleAsk(question);
            }}
          >
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="What did the emissions summary say about Scope 1?"
              rows={3}
            />
            <button type="submit" disabled={busy}>
              {busy ? "Searching documents..." : "Ask"}
            </button>
          </form>

          {error && <p className="error">{error}</p>}

          {result && (
            <div className="answer">
              <p className="answer-text">
                {renderAnswer(result.answer, jumpToCitation)}
              </p>
              <p className="muted">Answer mode: {result.mode}</p>
              {result.citations.length > 0 && (
                <>
                  <h3>Sources</h3>
                  <ol className="citations">
                    {result.citations.map((citation: Citation) => (
                      <li
                        key={citation.ref}
                        ref={(el) => {
                          citationRefs.current[citation.ref] = el;
                        }}
                        className={
                          activeRef === citation.ref ? "active" : undefined
                        }
                      >
                        <div className="cite-head">
                          <strong>
                            [{citation.ref}] {citation.document}
                          </strong>
                          <span className="muted">
                            {citation.chunk_id} · score{" "}
                            {citation.score.toFixed(3)}
                          </span>
                        </div>
                        <p>{citation.excerpt}...</p>
                      </li>
                    ))}
                  </ol>
                </>
              )}
            </div>
          )}
        </section>
      </main>

      <footer className="muted">
        Demo mode runs fully locally with TF-IDF retrieval and extractive
        answers. Configure Azure OpenAI on the backend for generated answers.
        Sample documents are fictional.
      </footer>
    </div>
  );
}
