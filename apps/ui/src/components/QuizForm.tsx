"use client";

import { useMemo, useState } from "react";

const AGENT_URL = process.env.NEXT_PUBLIC_AGENT_URL || "http://localhost:8001";
const PAGES_PREVIEW = process.env.NEXT_PUBLIC_PAGES_PREVIEW === "true";
const REPO_URL = process.env.NEXT_PUBLIC_REPO_URL || "https://github.com";

type AgentCitation = { title: string; section?: string | null };
type EstimateUI = {
  jobs: { name: string; qty?: number; unit_price?: number | null; total?: number | null }[];
  parts: { economy: any[]; optimum: any[]; oem: any[] };
  totals: { jobs_total?: number | null; parts_total?: number | null; total?: number | null };
  requires_approval: boolean;
};
type AgentUiResponse = {
  answer_text: string;
  questions: string[];
  estimate_ui?: EstimateUI | null;
  next_step: string;
  citations: AgentCitation[];
};
type AgentMessageOut = {
  lead_id: string;
  answer: string;
  requires_approval?: boolean;
  response?: AgentUiResponse | null;
};

export function QuizForm() {
  const [brand, setBrand] = useState("Kia");
  const [model, setModel] = useState("Rio");
  const [year, setYear] = useState("2017");
  const [engine, setEngine] = useState("");
  const [mileage, setMileage] = useState("120000");
  const [vin, setVin] = useState("");
  const [problem, setProblem] = useState("Нужно ТО");
  const [loading, setLoading] = useState(false);
  const [resp, setResp] = useState<AgentMessageOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  const message = useMemo(() => {
    const parts = [
      problem,
      `${brand} ${model} ${year}`.trim(),
      mileage ? `пробег ${mileage}` : "",
      engine ? `двигатель ${engine}` : "",
      vin ? `VIN ${vin}` : "",
    ].filter(Boolean);
    return parts.join(", ");
  }, [brand, model, year, mileage, engine, vin, problem]);

  async function submit() {
    if (PAGES_PREVIEW) {
      setError("GitHub Pages показывает только превью. Для полного демо запустите проект локально (см. README).");
      return;
    }
    setLoading(true);
    setError(null);
    setResp(null);
    try {
      const r = await fetch(`${AGENT_URL}/api/agent/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel: "web", message }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || r.statusText);
      setResp(data);
    } catch (e: any) {
      setError(e?.message || "Ошибка запроса");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <div className="mb-3 text-sm" style={{ color: "var(--muted)" }}>
        Квиз-заявка (MVP): агент соберёт параметры и сделает черновик сметы
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <input className="input" value={brand} onChange={(e) => setBrand(e.target.value)} placeholder="Марка" />
        <input className="input" value={model} onChange={(e) => setModel(e.target.value)} placeholder="Модель" />
        <input className="input" value={year} onChange={(e) => setYear(e.target.value)} placeholder="Год" />
        <input className="input" value={engine} onChange={(e) => setEngine(e.target.value)} placeholder="Двигатель (опц.)" />
        <input className="input" value={mileage} onChange={(e) => setMileage(e.target.value)} placeholder="Пробег" />
        <input className="input" value={vin} onChange={(e) => setVin(e.target.value)} placeholder="VIN (опц.)" />
        <input className="input md:col-span-2" value={problem} onChange={(e) => setProblem(e.target.value)} placeholder="Запрос/симптом" />
      </div>
      <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <button className="btn-primary" disabled={loading} onClick={submit}>
          {loading ? "Отправка..." : "Получить предварительную смету"}
        </button>
        <div className="text-sm" style={{ color: "var(--muted)" }}>
          Текст запроса: <span className="text-fg">{message}</span>
        </div>
      </div>
      {error ? (
        <div className="mt-4 text-sm text-red-400">{error}</div>
      ) : null}
      {PAGES_PREVIEW ? (
        <div className="mt-3 text-xs" style={{ color: "var(--muted)" }}>
          README: <a className="underline hover:text-fg" href={REPO_URL} target="_blank" rel="noreferrer">{REPO_URL}</a>
        </div>
      ) : null}
      {resp ? (
        <div className="mt-4">
          <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
            <div className="text-sm font-semibold">Заявка принята</div>
            <div className="mt-2 whitespace-pre-wrap text-sm">{resp.response?.answer_text || resp.answer}</div>
            {resp.response?.next_step ? (
              <div className="mt-3 text-sm" style={{ color: "var(--muted)" }}>
                Следующий шаг: <span className="text-fg">{resp.response.next_step}</span>
              </div>
            ) : null}
            <div className="mt-4 flex flex-col gap-2 sm:flex-row">
              <a className="btn-primary" href={`/result/${resp.lead_id}`}>
                Открыть результат
              </a>
              <a className="inline-flex items-center justify-center rounded-xl px-5 py-3 font-semibold" style={{ border: "1px solid var(--border)" }} href="/operator/leads">
                Перейти оператору
              </a>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

