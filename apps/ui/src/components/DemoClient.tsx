"use client";

import { useMemo, useState } from "react";

const CORE_API_URL = process.env.NEXT_PUBLIC_CORE_API_URL || "http://localhost:8000";

type ChatResponseNew = {
  session_id: string;
  summary: string;
  questions: { id: string; text: string }[];
  bundles: { economy?: any[]; optimal?: any[]; oem?: any[] };
  next_step: string;
  safety_notes: string[];
};

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
  stock?: number | null;
  delivery_days?: number | null;
  in_stock?: boolean;
  price?: number | null;
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
  | { role: "assistant"; text: string; response?: AgentResponse | null; chatResponse?: ChatResponseNew | null; typing?: boolean };

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

function TypingBubble() {
  return (
    <div className="typing-dots flex gap-1" aria-label="Ассистент печатает">
      <span className="w-2 h-2 rounded-full bg-current opacity-60 animate-pulse" />
      <span className="w-2 h-2 rounded-full bg-current opacity-60 animate-pulse" style={{ animationDelay: "0.2s" }} />
      <span className="w-2 h-2 rounded-full bg-current opacity-60 animate-pulse" style={{ animationDelay: "0.4s" }} />
    </div>
  );
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
      <div className="text-xs font-semibold mb-2" style={{ color: "var(--muted)" }}>{title}</div>
      <div className="space-y-2">
        {parts?.length ? (
          parts.map((p, idx) => (
            <div key={idx} className="rounded-xl border px-3 py-2 text-sm" style={{ borderColor: "var(--border)" }}>
              <div className="font-medium">{p?.name || "Запчасть"}</div>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                {p?.brand && <span>{p.brand}</span>}
                {p?.oem && <span> • Артикул: {p.oem}</span>}
              </div>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                {money(p?.unit_price ?? p?.price)} • {p?.in_stock ?? (p?.stock ? p.stock > 0 : false) ? `${p?.delivery_days ?? "—"} дн.` : "Под заказ"}
              </div>
            </div>
          ))
        ) : (
          <div className="text-sm" style={{ color: "var(--muted)" }}>—</div>
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
        {estimate?.requires_approval != null && (
          <div className="text-xs" style={{ color: "var(--muted)" }}>
            требует подтверждения: <span className="text-fg">{String(estimate.requires_approval)}</span>
          </div>
        )}
      </div>
      {jobs.length > 0 && (
        <div className="mb-4 rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
          <div className="text-xs font-semibold mb-2" style={{ color: "var(--muted)" }}>Работы</div>
          <div className="space-y-2">
            {jobs.map((j: any, idx: number) => (
              <div key={idx} className="rounded-xl border px-3 py-2 text-sm" style={{ borderColor: "var(--border)" }}>
                <div className="font-medium">{j?.name || "Работа"}</div>
                <div className="text-xs" style={{ color: "var(--muted)" }}>{money(j?.total)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="grid gap-3 md:grid-cols-3">
        <TierCard title="Эконом" parts={estimate?.parts?.economy || []} />
        <TierCard title="Оптимум" parts={estimate?.parts?.optimum || []} />
        <TierCard title="OEM" parts={estimate?.parts?.oem || []} />
      </div>
      {totals && (totals.total != null || totals.parts_total != null) && (
        <div className="mt-4 rounded-xl border px-4 py-3" style={{ borderColor: "var(--border)" }}>
          <div className="flex justify-between text-sm">
            <div style={{ color: "var(--muted)" }}>Итого</div>
            <div className="font-semibold">{money(totals?.total ?? totals?.parts_total)}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function toEstimateUI(chatResp: ChatResponseNew): EstimateUI | null {
  const parts = chatResp.bundles || {};
  const econ = (parts.economy || []).map((p: any) => ({
    name: p.name,
    brand: p.brand,
    oem: p.oem,
    sku: p.sku,
    unit_price: p.price,
    price: p.price,
    stock: p.stock,
    delivery_days: p.delivery_days,
    in_stock: p.in_stock,
  }));
  const opt = (parts.optimal || []).map((p: any) => ({ ...p, unit_price: p.price }));
  const oem = (parts.oem || []).map((p: any) => ({ ...p, unit_price: p.price }));
  if (!econ.length && !opt.length && !oem.length) return null;
  const total = [...econ, ...opt, ...oem][0]?.price;
  return {
    jobs: [],
    parts: { economy: econ, optimum: opt, oem },
    totals: { total },
    requires_approval: true,
  };
}

export function DemoClient() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([
    { role: "assistant", text: "Привет! Выберите: ТО / Запчасти / Проблема или напишите запрос. Укажите марку, модель и год авто." },
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

  function getCarContext() {
    const ctx: Record<string, string | number | null> = {};
    if (brand.trim()) ctx.brand = brand.trim();
    if (model.trim()) ctx.model = model.trim();
    if (year.trim()) ctx.year = year.trim() as any;
    if (engine.trim()) ctx.engine = engine.trim();
    if (mileage.trim()) ctx.mileage = mileage.trim() as any;
    if (vin.trim()) ctx.vin = vin.trim();
    return ctx;
  }

  async function send(msg: string) {
    const trimmed = msg.trim();
    if (!trimmed) return;

    const userText = trimmed;
    setMessages((m) => [...m, { role: "user", text: userText }, { role: "assistant", text: "", typing: true }]);
    setText("");
    setLoading(true);

    try {
        const r = await fetch(`${CORE_API_URL}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: userText,
            car_context: getCarContext(),
            session_id: sessionId,
          }),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data?.detail?.[0]?.msg || data?.detail || r.statusText);

        setSessionId(data.session_id);
        setMessages((m) => {
          const withoutTyping = m.filter((x) => !("typing" in x) || !x.typing);
          return [...withoutTyping, { role: "assistant", text: data.summary, chatResponse: data }];
        });
    } catch (e: any) {
      setMessages((m) => {
        const withoutTyping = m.filter((x) => !("typing" in x) || !x.typing);
        return [...withoutTyping, { role: "assistant", text: `Не удалось обработать запрос. ${e?.message || "Попробуйте позже."}` }];
      });
    } finally {
      setLoading(false);
    }
  }

  const lastChatMsg = [...messages].reverse().find((m) => "chatResponse" in m && !!(m as { chatResponse?: ChatResponseNew }).chatResponse);
  const lastChatResponseData = lastChatMsg ? (lastChatMsg as { chatResponse: ChatResponseNew }).chatResponse : undefined;
  const fallbackEstimateMsg = [...messages].reverse().find((m) => isAssistantMsg(m) && (m as { response?: { estimate_ui?: EstimateUI } }).response?.estimate_ui);
  const lastEstimate = lastChatResponseData ? toEstimateUI(lastChatResponseData) : fallbackEstimateMsg ? (fallbackEstimateMsg as { response?: { estimate_ui?: EstimateUI } }).response?.estimate_ui : undefined;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="card">
        <div className="mb-3 flex items-center justify-between">
          <div className="text-sm font-semibold">Чат</div>
          <div className="text-xs" style={{ color: "var(--muted)" }}>
            session: {(sessionId || "—").toString().slice(0, 8)}
          </div>
        </div>

        <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-3">
          <input className="input" value={brand} onChange={(e) => setBrand(e.target.value)} placeholder="Марка" />
          <input className="input" value={model} onChange={(e) => setModel(e.target.value)} placeholder="Модель" />
          <input className="input" value={year} onChange={(e) => setYear(e.target.value)} placeholder="Год" />
          <input className="input" value={engine} onChange={(e) => setEngine(e.target.value)} placeholder="Двигатель" />
          <input className="input" value={mileage} onChange={(e) => setMileage(e.target.value)} placeholder="Пробег" />
          <input className="input" value={vin} onChange={(e) => setVin(e.target.value)} placeholder="VIN" />
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
                    border: "1px solid var(--border)",
                  }}
                >
                  {"typing" in m && m.typing ? <TypingBubble /> : m.text}
                  {"chatResponse" in m && m.chatResponse && (
                    <div className="mt-3 border-t pt-3" style={{ borderColor: "var(--border)" }}>
                      <AssistantMessageBlock data={m.chatResponse} />
                    </div>
                  )}
                  {"response" in m && m.response && !m.chatResponse && formatCitations(m.response?.citations)}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-3 flex gap-2">
          <input
            className="input flex-1"
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
              Отправьте запрос (ТО / Запчасти / Проблема) или напишите, что нужно — получите варианты комплектаций.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function AssistantMessageBlock({ data }: { data: ChatResponseNew }) {
  const tiers = [
    { key: "economy" as const, label: "Эконом" },
    { key: "optimal" as const, label: "Оптимум" },
    { key: "oem" as const, label: "OEM" },
  ];
  const bundles = data.bundles || {};

  return (
    <div className="space-y-3 text-left">
      {data.questions?.length > 0 && (
        <div>
          <div className="text-xs font-semibold mb-1" style={{ color: "var(--muted)" }}>Уточните:</div>
          <div className="flex flex-wrap gap-1">
            {data.questions.map((q) => (
              <span
                key={q.id}
                className="rounded-full border px-2 py-0.5 text-xs"
                style={{ borderColor: "var(--border)" }}
              >
                {q.text}
              </span>
            ))}
          </div>
        </div>
      )}
      {Object.keys(bundles).length > 0 && (
        <div>
          <div className="text-xs font-semibold mb-1" style={{ color: "var(--muted)" }}>Варианты:</div>
          <div className="grid grid-cols-3 gap-2">
            {tiers.map(({ key, label }) => {
              const items = bundles[key] || [];
              if (!items.length) return null;
              return (
                <div key={key} className="rounded-xl border p-2" style={{ borderColor: "var(--border)" }}>
                  <div className="text-xs font-semibold mb-1" style={{ color: "var(--muted)" }}>{label}</div>
                  {items.slice(0, 2).map((p: any, i: number) => (
                    <div key={i} className="text-xs py-1">
                      <div>{p.name}</div>
                      <div style={{ color: "var(--muted)" }}>{p.brand} {money(p.price)}</div>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      )}
      {data.safety_notes?.map((n, i) => (
        <div key={i} className="text-xs" style={{ color: "var(--muted)" }}>⚠️ {n}</div>
      ))}
    </div>
  );
}
