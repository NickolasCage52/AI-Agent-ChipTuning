"use client";

import { useMemo, useState } from "react";

const AGENT_URL = process.env.NEXT_PUBLIC_AGENT_URL || "http://localhost:8001";

type AgentCitation = { title: string; section?: string | null };

type EstimateUIJob = { name: string; qty?: number; unit_price?: number | null; total?: number | null };
type EstimateUIPart = {
  name: string;
  brand?: string | null;
  oem?: string | null;
  sku?: string | null;
  qty?: number;
  unit_price?: number | null;
  total?: number | null;
  supplier_id?: string | null;
  stock?: number | null;
  delivery_days?: number | null;
};
type EstimateUI = {
  jobs: EstimateUIJob[];
  parts: { economy: EstimateUIPart[]; optimum: EstimateUIPart[]; oem: EstimateUIPart[] };
  totals: { jobs_total?: number | null; parts_total?: number | null; total?: number | null };
  requires_approval: boolean;
};
type AgentResponse = {
  answer_text: string;
  questions: string[];
  next_step: string;
  citations: AgentCitation[];
  estimate_ui?: EstimateUI | null;
};

type Msg =
  | { role: "user"; text: string }
  | { role: "assistant"; text: string; response?: AgentResponse | null };

function isAssistantMsg(m: Msg): m is Extract<Msg, { role: "assistant" }> {
  return m.role === "assistant";
}

function money(v: any) {
  try {
    if (v === null || v === undefined) return "—";
    const n = Number(v);
    if (Number.isNaN(n)) return "—";
    return `${Math.round(n)} ₽`;
  } catch {
    return "—";
  }
}

function formatCitations(citations: AgentCitation[] | undefined) {
  const list = (citations || []).filter(Boolean);
  if (!list.length) return null;
  return (
    <div className="mt-3 text-xs" style={{ color: "var(--muted)" }}>
      <div className="font-semibold">Источник</div>
      <ul className="mt-1 list-disc pl-5">
        {list.slice(0, 3).map((s, i) => (
          <li key={i}>
            {s.title}
            {s.section ? ` / ${s.section}` : ""}
          </li>
        ))}
      </ul>
    </div>
  );
}

function TierCard({ title, parts }: { title: string; parts: EstimateUIPart[] }) {
  return (
    <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
      <div className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
        {title}
      </div>
      <div className="mt-2 space-y-2">
        {parts?.length ? (
          parts.map((p, idx) => (
            <div key={idx} className="rounded-xl border px-3 py-2 text-sm" style={{ borderColor: "var(--border)" }}>
              <div className="font-medium">{p?.name || "Запчасть"}</div>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                {p?.brand ? `${p.brand} • ` : ""}oem={p?.oem || "—"} • sku={p?.sku || "—"}
              </div>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                цена={money(p?.unit_price)} • stock={p?.stock ?? "—"} • {p?.delivery_days ?? "—"} дн.
              </div>
            </div>
          ))
        ) : (
          <div className="text-sm" style={{ color: "var(--muted)" }}>
            —
          </div>
        )}
      </div>
    </div>
  );
}

function EstimateCard({ estimate }: { estimate: EstimateUI }) {
  const jobs = Array.isArray(estimate?.jobs) ? estimate.jobs : [];
  const totals = estimate?.totals || {};

  return (
    <div className="card">
      <div className="mb-2 flex items-center justify-between">
        <div className="text-sm font-semibold">Результат</div>
        <div className="text-xs" style={{ color: "var(--muted)" }}>
          требует подтверждения: <span className="text-fg">{String(estimate?.requires_approval ?? true)}</span>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
          <div className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
            Работы
          </div>
          <div className="mt-2 space-y-2">
            {jobs.length ? (
              jobs.map((j: any, idx: number) => (
                <div key={idx} className="rounded-xl border px-3 py-2 text-sm" style={{ borderColor: "var(--border)" }}>
                  <div className="font-medium">{j?.name || "Работа"}</div>
                  <div className="text-xs" style={{ color: "var(--muted)" }}>
                    qty={j?.qty ?? 1} • unit={money(j?.unit_price)} • total={money(j?.total)}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-sm" style={{ color: "var(--muted)" }}>
                —
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <TierCard title="Эконом" parts={estimate?.parts?.economy || []} />
        <TierCard title="Оптимум" parts={estimate?.parts?.optimum || []} />
        <TierCard title="OEM" parts={estimate?.parts?.oem || []} />
      </div>

      <div className="mt-4 rounded-xl border px-4 py-3" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center justify-between text-sm">
          <div style={{ color: "var(--muted)" }}>Итого</div>
          <div className="font-semibold">{money(totals?.total)}</div>
        </div>
        <div className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
          jobs_total={money(totals?.jobs_total)} • parts_total={money(totals?.parts_total)}
        </div>
      </div>
    </div>
  );
}

export function DemoClient() {
  const [leadId, setLeadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "assistant",
      text: "Привет! Это локальный demo-режим. Выберите intent: ТО / Запчасти / Проблема или напишите своим текстом.",
    },
  ]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);

  const [brand, setBrand] = useState("");
  const [model, setModel] = useState("");
  const [year, setYear] = useState("");
  const [engine, setEngine] = useState("");
  const [mileage, setMileage] = useState("");
  const [vin, setVin] = useState("");

  const quick = useMemo(
    () => [
      { label: "ТО", message: "Нужно ТО" },
      { label: "Запчасти", message: "Нужны запчасти" },
      { label: "Проблема", message: "Проблема: стук/шум, нужна диагностика" },
    ],
    []
  );

  function buildMessage(userText: string) {
    const base = userText.trim();
    const ctx: string[] = [];
    if (brand.trim()) ctx.push(`Марка: ${brand.trim()}`);
    if (model.trim()) ctx.push(`Модель: ${model.trim()}`);
    if (year.trim()) ctx.push(`Год: ${year.trim()}`);
    if (engine.trim()) ctx.push(`Двигатель: ${engine.trim()}`);
    if (mileage.trim()) ctx.push(`Пробег: ${mileage.trim()}`);
    if (vin.trim()) ctx.push(`VIN: ${vin.trim()}`);
    if (!ctx.length) return base;
    return `${base}\n${ctx.join("\n")}`;
  }

  async function send(msg: string) {
    const enriched = buildMessage(msg);
    if (!enriched.trim()) return;
    setMessages((m) => [...m, { role: "user", text: enriched }]);
    setText("");
    setLoading(true);
    try {
      const r = await fetch(`${AGENT_URL}/api/agent/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel: "web", lead_id: leadId, message: enriched }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || r.statusText);

      setLeadId(data.lead_id);
      const resp: AgentResponse | null = data?.response || null;
      setMessages((m) => [...m, { role: "assistant", text: data.answer, response: resp }]);
    } catch (e: any) {
      setMessages((m) => [...m, { role: "assistant", text: `Ошибка: ${e?.message || e}` }]);
    } finally {
      setLoading(false);
    }
  }

  const lastEstimate = [...messages]
    .reverse()
    .filter(isAssistantMsg)
    .find((m) => !!m.response?.estimate_ui)?.response?.estimate_ui;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="card">
        <div className="mb-3 flex items-center justify-between">
          <div className="text-sm font-semibold">Чат</div>
          <div className="text-xs" style={{ color: "var(--muted)" }}>
            lead_id: <span className="text-fg">{leadId || "—"}</span>
            {leadId ? (
              <>
                {" "}
                •{" "}
                <a className="underline hover:text-fg" href={`/operator/leads/${leadId}`}>
                  открыть в операторе
                </a>
              </>
            ) : null}
          </div>
        </div>

        <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-3">
          <input className="input" value={brand} onChange={(e) => setBrand(e.target.value)} placeholder="brand" />
          <input className="input" value={model} onChange={(e) => setModel(e.target.value)} placeholder="model" />
          <input className="input" value={year} onChange={(e) => setYear(e.target.value)} placeholder="year" />
          <input className="input" value={engine} onChange={(e) => setEngine(e.target.value)} placeholder="engine" />
          <input className="input" value={mileage} onChange={(e) => setMileage(e.target.value)} placeholder="mileage" />
          <input className="input" value={vin} onChange={(e) => setVin(e.target.value)} placeholder="vin" />
        </div>

        <div className="mb-3 flex flex-wrap gap-2">
          {quick.map((q) => (
            <button
              key={q.label}
              className="rounded-full border px-3 py-1 text-xs"
              style={{ borderColor: "var(--border)", color: "var(--muted)" }}
              onClick={() => send(q.message)}
              disabled={loading}
            >
              {q.label}
            </button>
          ))}
        </div>

        <div className="h-[420px] overflow-auto rounded-xl border p-3" style={{ borderColor: "var(--border)" }}>
          <div className="flex flex-col gap-3">
            {messages.map((m, idx) => (
              <div key={idx} className={m.role === "user" ? "self-end" : "self-start"}>
                <div
                  className="max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm"
                  style={{
                    background: m.role === "user" ? "rgba(225,29,46,0.15)" : "rgba(255,255,255,0.04)",
                    border: `1px solid var(--border)`,
                  }}
                >
                  {m.text}
                  {"response" in m ? formatCitations(m.response?.citations) : null}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-3 flex gap-2">
          <input
            className="input"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Напишите сообщение..."
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(text);
              }
            }}
          />
          <button className="btn-primary" disabled={loading} onClick={() => send(text)}>
            {loading ? "..." : "Отправить"}
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {lastEstimate ? (
          <EstimateCard estimate={lastEstimate} />
        ) : (
          <div className="card">
            <div className="text-sm font-semibold">Результат</div>
            <div className="mt-1 text-sm" style={{ color: "var(--muted)" }}>
              Отправьте запрос “ТО” / “Запчасти” / “Проблема”, чтобы получить расчёт и варианты комплектаций.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

