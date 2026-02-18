"use client";

import { useEffect, useMemo, useState } from "react";

const CORE_URL = process.env.NEXT_PUBLIC_CORE_API_URL || "http://localhost:8000";

type Lead = {
  id: string;
  channel: string;
  status: string;
  problem_text?: string | null;
  created_at: string;
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
  agent_plan?: any;
  tool_calls?: any;
  final_answer?: string | null;
  created_at: string;
};

export function OperatorPanel() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [estimates, setEstimates] = useState<Estimate[]>([]);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selLead = useMemo(() => leads.find((l) => l.id === selected) || null, [leads, selected]);

  async function loadLeads() {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`${CORE_URL}/api/leads`);
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || r.statusText);
      setLeads(data);
      if (!selected && data?.[0]?.id) setSelected(data[0].id);
    } catch (e: any) {
      setError(e?.message || "Ошибка загрузки лидов");
    } finally {
      setLoading(false);
    }
  }

  async function loadLeadDetails(leadId: string) {
    setError(null);
    try {
      const [eRes, rRes] = await Promise.all([
        fetch(`${CORE_URL}/api/estimates?lead_id=${leadId}`),
        fetch(`${CORE_URL}/api/agent_runs?lead_id=${leadId}`),
      ]);
      const eData = await eRes.json();
      const rData = await rRes.json();
      if (!eRes.ok) throw new Error(eData?.detail || eRes.statusText);
      if (!rRes.ok) throw new Error(rData?.detail || rRes.statusText);
      setEstimates(eData);
      setRuns(rData);
    } catch (e: any) {
      setError(e?.message || "Ошибка загрузки деталей");
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
      if (selected) await loadLeadDetails(selected);
    } catch (e: any) {
      setError(e?.message || "Ошибка подтверждения");
    }
  }

  useEffect(() => {
    loadLeads();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selected) loadLeadDetails(selected);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-[360px_1fr]">
      <div className="card">
        <div className="mb-3 flex items-center justify-between">
          <div className="text-sm font-semibold">Leads</div>
          <button
            className="rounded-xl border px-3 py-2 text-xs"
            style={{ borderColor: "var(--border)", color: "var(--muted)" }}
            onClick={loadLeads}
            disabled={loading}
          >
            {loading ? "..." : "Обновить"}
          </button>
        </div>
        {error ? <div className="mb-3 text-sm text-red-400">{error}</div> : null}
        <div className="flex flex-col gap-2">
          {leads.map((l) => (
            <button
              key={l.id}
              onClick={() => setSelected(l.id)}
              className="rounded-2xl border p-3 text-left"
              style={{
                borderColor: "var(--border)",
                background: selected === l.id ? "rgba(225,29,46,0.12)" : "rgba(255,255,255,0.02)",
              }}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="text-sm font-semibold">{l.channel}</div>
                <div className="text-xs" style={{ color: "var(--muted)" }}>
                  {new Date(l.created_at).toLocaleString()}
                </div>
              </div>
              <div className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
                статус: <span className="text-fg">{l.status}</span>
              </div>
              <div className="mt-2 line-clamp-2 text-sm">{l.problem_text || "—"}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="mb-2 text-sm font-semibold">Карточка</div>
        {selLead ? (
          <>
            <div className="text-xs" style={{ color: "var(--muted)" }}>
              lead_id: <span className="text-fg">{selLead.id}</span>
            </div>
            <div className="mt-2 whitespace-pre-wrap">{selLead.problem_text}</div>

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
                          requires_approval: <span className="text-fg">{String(e.requires_approval)}</span>
                        </div>
                        {e.requires_approval ? (
                          <button className="btn-primary mt-3 w-full" onClick={() => approve(e.id)}>
                            Approve
                          </button>
                        ) : (
                          <div className="mt-3 text-xs" style={{ color: "var(--muted)" }}>
                            approved_by: <span className="text-fg">{e.approved_by}</span>
                          </div>
                        )}
                        <details className="mt-2">
                          <summary className="cursor-pointer text-xs" style={{ color: "var(--muted)" }}>
                            items
                          </summary>
                          <pre className="mt-2 overflow-auto text-xs">{JSON.stringify(e.items, null, 2)}</pre>
                        </details>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)" }}>
                <div className="mb-2 text-sm font-semibold">Логи agent_runs</div>
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
          </>
        ) : (
          <div className="text-sm" style={{ color: "var(--muted)" }}>
            Выберите lead слева.
          </div>
        )}
      </div>
    </div>
  );
}

