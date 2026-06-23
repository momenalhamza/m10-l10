import { useState } from "react";
import { useRouter } from "next/router";

import { KGResponse } from "../lib/types";
import { API_URL, authFetch } from "../lib/api";

export default function KgPage() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<KGResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    setResult(null);
    try {
      const res = await authFetch(`${API_URL}/kg/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (res.status === 401) {
        router.push("/login");
        return;
      }
      if (res.status === 403) {
        setError("Your credential is valid but lacks the required scope.");
        return;
      }
      if (res.status === 422) {
        const body = await res.json();
        const detail = body.detail;
        if (detail && Array.isArray(detail.supported_patterns)) {
          setError(
            `Unsupported question. Supported patterns: ${detail.supported_patterns.join(", ")}`,
          );
        } else {
          setError(typeof detail === "string" ? detail : JSON.stringify(detail));
        }
        return;
      }
      if (res.status === 503) {
        setError("The backend is starting up — please try again in a moment.");
        return;
      }
      if (!res.ok) {
        setError(`Request failed (${res.status}).`);
        return;
      }
      const data: KGResponse = await res.json();
      setResult(data);
    } catch {
      setError("Could not reach the backend.");
    }
  }

  return (
    <main>
      <h1>Knowledge Graph — Recipe Query</h1>
      <input
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="e.g. Find Sichuan recipes"
      />
      <button onClick={submit} disabled={!question}>Ask</button>
      {error && <p role="alert">{error}</p>}
      {result && (
        <>
          <pre>{result.cypher}</pre>
          <table>
            <tbody>
              {result.rows.map((row, i) => (
                <tr key={i} data-testid="kg-row">
                  {Object.values(row).map((val, j) => (
                    <td key={j}>{String(val)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </main>
  );
}
