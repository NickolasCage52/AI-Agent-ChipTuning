"use client";

import { useEffect, useState } from "react";

const CORE_URL = process.env.NEXT_PUBLIC_CORE_API_URL || "http://localhost:8000";
const PAGES_PREVIEW = process.env.NEXT_PUBLIC_PAGES_PREVIEW === "true";

type LeadExpanded = {
  id: string;
  channel: string;
  status: string;
  problem_text?: string | null;
  created_at: string;
  updated_at: string;
  client: { id: string; name?: string | null; phone?: string | null; tg_id?: number | null };
  car?: { id: string; vin?: string | null; brand?: string | null; model?: string | null; year?: number | null; engine?: string | null; mileage?: number | null } | null;
};

type Estimate = {
  id: string;
  lead_id: string;
  total_price: number;
  requires_approval: boolean;
  items: any;
  created_at: string;
  approved_by?: string | null;
  approved_at?: string | null;
};

type AgentRun = {
  id: string;
  lead_id: string;
  user_message: string;
  tool_calls?: any;
  final_answer?: string | null;
  created_at: string;
};

type LeadEvent = {
  id: string;
  lead_id: string;
  event_type: string;
  payload?: any;
  request_id?: string | null;
  created_at: string;
};

function humanizeEvent(eventType: string) {
  const map: Record<string, string> = {
    "lead.created": "Создан лид",
    "lead.updated": "Обновлены данные лида",
    "estimate.draft_created": "Сформирован черновик сметы",
    "estimate.saved": "Смета сохранена",
    "estimate.approval_requested": "Запрошено подтверждение сметы",
    "estimate.approved": "Смета подтверждена",
    "supplier.price_imported": "Импорт прайса поставщика",
    "widget.session_created": "Создана сессия виджета",
    "agent.message_received": "Сообщение клиента",
    "agent.plan_created": "План агента",
    "agent.tool_called": "Инструмент агента",
    "agent.final_answer_sent": "Ответ отправлен клиенту",
  };
  return map[eventType] || eventType;
}

export function OperatorLeadDetail({ leadId }: { leadId: string }) {
  const [lead, setLead] = useState<LeadExpanded | null>(null);
  const [estimates, setEstimates] = useState<Estimate[]>([]);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [events, setEvents] = useState<LeadEvent[]>([]);
  const [eventFilter, setEventFilter] = useState<"all" | "agent" | "estimate" | "widget" | "telegram" | "supplier" | "rag">("all");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (PAGES_PREVIEW) return;
    setLoading(true);
    setError(null);
    try {
      const [lRes, eRes, rRes] = await Promise.all([
        fetch(`${CORE_URL}/api/leads/${leadId}`, { cache: "no-store" }),
        fetch(`${CORE_URL}/api/estimates?lead_id=${leadId}`, { cache: "no-store" }),
        fetch(`${CORE_URL}/api/agent_runs?lead_id=${leadId}`, { cache: "no-store" }),
      ]);
      const evRes = await fetch(`${CORE_URL}/api/leads/${leadId}/events`, { cache: "no-store" });
      const lData = await lRes.json();
      const eData = await eRes.json();
      const rData = await rRes.json();
      const evData = await evRes.json();
      if (!lRes.ok) throw new Error(lData?.detail || lRes.statusText);
      if (!eRes.ok) throw new Error(eData?.detail || eRes.statusText);
      if (!rRes.ok) throw new Error(rData?.detail || rRes.statusText);
      if (!evRes.ok) throw new Error(evData?.detail || evRes.statusText);
      setLead(lData);
      setEstimates(eData);
      setRuns(rData);
      setEvents(evData);
    } catch (e: any) {
      setError(e?.message || "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }

  async function approve(estimateId: string) {
    setError(null);
    try {
      const r = await fetch(`${CORE_URL}/api/estimate/${estimateId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved_by: "operator_ui" }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || r.statusText);
      await load();
    } catch (e: any) {
      setError(e?.message || "Ошибка подтверждения");
    }
  }

  useEffect(() => {
    load();
  }, [leadId]);

  return (
    PAGES_PREVIEW ? (
      <div className="card glass">
        <div className="text-sm font-semibold">Операторская карточка недоступна в GitHub Pages</div>
        <div className="mt-2 text-sm" style={{ color: "var(--muted)" }}>
          Pages показывает только превью интерфейса. Для просмотра лидов нужен локальный backend.
        </div>
      </div>
    ) : (
    <div className="card glass">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold">Карточка лида</div>
          <div className="text-xs" style={{ color: "var(--muted)" }}>
            lead_id: <span className="text-fg">{leadId}</span>
          </div>
        </div>
        <button
          className="rounded-xl border px-3 py-2 text-xs"
          style={{ borderColor: "var(--border)", color: "var(--muted)" }}
          onClick={load}
          disabled={loading}
        >
          {loading ? "..." : "Обновить"}
        </button>
      </div>

      {error ? <div className="mb-3 text-sm text-red-400">{error}</div> : null}

      {lead ? (
        <>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)" }}>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                канал / статус
              </div>
              <div className="mt-1 text-sm">
                <span className="font-semibold">{lead.channel}</span> • <span className="font-semibold">{lead.status}</span>
              </div>
              <div className="mt-3 text-xs" style={{ color: "var(--muted)" }}>
                запрос клиента
              </div>
              <div className="mt-1 whitespace-pre-wrap text-sm">{lead.problem_text || "—"}</div>
            </div>

            <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)" }}>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                авто
              </div>
              <div className="mt-1 text-sm">
                {lead.car?.brand || "—"} {lead.car?.model || ""} {lead.car?.year || ""}
              </div>
              <div className="mt-2 text-xs" style={{ color: "var(--muted)" }}>
                VIN: <span className="text-fg">{lead.car?.vin || "—"}</span>
              </div>
              <div className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
                engine: <span className="text-fg">{lead.car?.engine || "—"}</span> • mileage:{" "}
                <span className="text-fg">{lead.car?.mileage || "—"}</span>
              </div>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)" }}>
              <div className="mb-2 text-sm font-semibold">Сметы</div>
              {estimates.length === 0 ? (
                <div className="text-sm" style={{ color: "var(--muted)" }}>
                  Пока нет смет.
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  {estimates.map((e) => (
                    <div key={e.id} className="rounded-2xl border p-3" style={{ borderColor: "var(--border)" }}>
                      <div className="flex items-center justify-between">
                        <div className="text-sm font-semibold">{e.total_price} ₽</div>
                        <div className="text-xs" style={{ color: "var(--muted)" }}>
                          {new Date(e.created_at).toLocaleString()}
                        </div>
                      </div>
                      <div className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
                        требует подтверждения: <span className="text-fg">{String(e.requires_approval)}</span>
                      </div>
                      {e.requires_approval ? (
                        <button className="btn-primary mt-3 w-full" onClick={() => approve(e.id)}>
                          Подтвердить смету
                        </button>
                      ) : (
                        <div className="mt-3 text-xs" style={{ color: "var(--muted)" }}>
                          подтверждено: <span className="text-fg">{e.approved_by}</span>
                        </div>
                      )}
                      <details className="mt-2">
                        <summary className="cursor-pointer text-xs" style={{ color: "var(--muted)" }}>
                          детали
                        </summary>
                        <pre className="mt-2 overflow-auto text-xs">{JSON.stringify(e.items, null, 2)}</pre>
                      </details>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)" }}>
              <div className="mb-2 text-sm font-semibold">История диалога (agent_runs)</div>
              {runs.length === 0 ? (
                <div className="text-sm" style={{ color: "var(--muted)" }}>
                  Пока нет логов.
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  {runs.map((r) => (
                    <div key={r.id} className="rounded-2xl border p-3" style={{ borderColor: "var(--border)" }}>
                      <div className="flex items-center justify-between">
                        <div className="text-xs" style={{ color: "var(--muted)" }}>
                          {new Date(r.created_at).toLocaleString()}
                        </div>
                        <div className="text-xs" style={{ color: "var(--muted)" }}>
                          run_id: <span className="text-fg">{r.id.slice(0, 8)}…</span>
                        </div>
                      </div>
                      <div className="mt-2 text-sm font-semibold">user</div>
                      <div className="whitespace-pre-wrap text-sm">{r.user_message}</div>
                      <div className="mt-2 text-sm font-semibold">assistant</div>
                      <div className="whitespace-pre-wrap text-sm">{r.final_answer}</div>
                      <details className="mt-2">
                        <summary className="cursor-pointer text-xs" style={{ color: "var(--muted)" }}>
                          tool_calls
                        </summary>
                        <pre className="mt-2 overflow-auto text-xs">{JSON.stringify(r.tool_calls, null, 2)}</pre>
                      </details>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="mt-6 rounded-2xl border p-4" style={{ borderColor: "var(--border)" }}>
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <div className="text-sm font-semibold">Таймлайн событий</div>
              <div className="flex flex-wrap gap-2">
                {(["all", "agent", "estimate", "widget", "telegram", "supplier", "rag"] as const).map((k) => (
                  <button
                    key={k}
                    className="rounded-full border px-3 py-1 text-xs"
                    style={{
                      borderColor: "var(--border)",
                      color: eventFilter === k ? "var(--fg)" : "var(--muted)",
                      background: eventFilter === k ? "rgba(225,29,46,0.12)" : "transparent",
                    }}
                    onClick={() => setEventFilter(k)}
                  >
                    {k}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex flex-col gap-2">
              {(events || [])
                .filter((e) => {
                  if (eventFilter === "all") return true;
                  if (eventFilter === "agent") return e.event_type.startsWith("agent.");
                  if (eventFilter === "estimate") return e.event_type.startsWith("estimate.");
                  if (eventFilter === "widget") return e.event_type.startsWith("widget.");
                  if (eventFilter === "telegram") return e.event_type.startsWith("telegram.");
                  if (eventFilter === "supplier") return e.event_type.startsWith("supplier.");
                  if (eventFilter === "rag") return e.event_type.startsWith("rag.");
                  return true;
                })
                .map((e) => (
                  <div key={e.id} className="rounded-2xl border p-3" style={{ borderColor: "var(--border)" }}>
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <div className="text-sm font-semibold">{humanizeEvent(e.event_type)}</div>
                        <div className="text-xs" style={{ color: "var(--muted)" }}>
                          {e.event_type}
                        </div>
                      </div>
                      <div className="text-xs" style={{ color: "var(--muted)" }}>
                        {new Date(e.created_at).toLocaleString()}
                      </div>
                    </div>
                    <div className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
                      request_id: <span className="text-fg">{e.request_id || "—"}</span>
                    </div>
                    <details className="mt-2">
                      <summary className="cursor-pointer text-xs" style={{ color: "var(--muted)" }}>
                        детали (payload)
                      </summary>
                      <pre className="mt-2 overflow-auto text-xs">{JSON.stringify(e.payload || {}, null, 2)}</pre>
                    </details>
                  </div>
                ))}
              {events.length === 0 ? (
                <div className="text-sm" style={{ color: "var(--muted)" }}>
                  Нет событий.
                </div>
              ) : null}
            </div>
          </div>
        </>
      ) : (
        <div className="text-sm" style={{ color: "var(--muted)" }}>
          {loading ? "Загрузка..." : "Lead не найден"}
        </div>
      )}
    </div>
    )
  );
}

