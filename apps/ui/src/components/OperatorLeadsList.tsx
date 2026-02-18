"use client";

import { useEffect, useState } from "react";

const CORE_URL = process.env.NEXT_PUBLIC_CORE_API_URL || "http://localhost:8000";
const PAGES_PREVIEW = process.env.NEXT_PUBLIC_PAGES_PREVIEW === "true";

type Lead = {
  id: string;
  channel: string;
  status: string;
  problem_text?: string | null;
  created_at: string;
};

export function OperatorLeadsList() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("all");

  function statusStyle(s: string) {
    if (s === "approved") return { border: "rgba(82,255,168,0.35)", bg: "rgba(82,255,168,0.08)", text: "var(--fg)" };
    if (s === "estimated") return { border: "rgba(225,29,46,0.35)", bg: "rgba(225,29,46,0.10)", text: "var(--fg)" };
    if (s === "submitted") return { border: "rgba(255,255,255,0.18)", bg: "rgba(255,255,255,0.04)", text: "var(--fg)" };
    return { border: "var(--border)", bg: "rgba(255,255,255,0.02)", text: "var(--muted)" };
  }

  async function load() {
    if (PAGES_PREVIEW) return;
    setLoading(true);
    setError(null);
    try {
      const qs = status && status !== "all" ? `?status=${encodeURIComponent(status)}` : "";
      const r = await fetch(`${CORE_URL}/api/leads${qs}`, { cache: "no-store" });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || r.statusText);
      setLeads(data);
    } catch (e: any) {
      setError(e?.message || "Ошибка загрузки лидов");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  return (
    PAGES_PREVIEW ? (
      <div className="card glass">
        <div className="text-sm font-semibold">Операторская панель недоступна в GitHub Pages</div>
        <div className="mt-2 text-sm" style={{ color: "var(--muted)" }}>
          Pages показывает только превью интерфейса. Для работы оператора нужен локальный backend.
        </div>
      </div>
    ) : (
    <div className="card glass">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-sm font-semibold">Лиды</div>
        <button
          className="rounded-xl border px-3 py-2 text-xs"
          style={{ borderColor: "var(--border)", color: "var(--muted)" }}
          onClick={load}
          disabled={loading}
        >
          {loading ? "..." : "Обновить"}
        </button>
      </div>
      <div className="mb-3 grid grid-cols-1 gap-2 md:grid-cols-3">
        <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="all">Все статусы</option>
          <option value="new">new</option>
          <option value="estimated">estimated</option>
          <option value="approved">approved</option>
          <option value="submitted">submitted</option>
          <option value="closed">closed</option>
        </select>
        <div className="md:col-span-2 text-sm" style={{ color: "var(--muted)" }}>
          Подсказка: клиентская заявка создаётся в `/widget` или на лендинге через квиз.
        </div>
      </div>
      {error ? <div className="mb-3 text-sm text-red-400">{error}</div> : null}
      <div className="flex flex-col gap-2">
        {leads.map((l) => (
          <a
            key={l.id}
            href={`/operator/leads/${l.id}`}
            className="rounded-2xl border p-3 text-left hover:opacity-95"
            style={{
              borderColor: "var(--border)",
              background: "rgba(255,255,255,0.02)",
            }}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">{l.channel}</div>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                {new Date(l.created_at).toLocaleString()}
              </div>
            </div>
            <div className="mt-2">
              <span
                className="inline-flex items-center rounded-full border px-3 py-1 text-xs"
                style={{
                  borderColor: statusStyle(l.status).border,
                  background: statusStyle(l.status).bg,
                  color: statusStyle(l.status).text,
                }}
              >
                {l.status}
              </span>
            </div>
            <div className="mt-2 line-clamp-2 text-sm">{l.problem_text || "—"}</div>
          </a>
        ))}
        {leads.length === 0 && !loading ? (
          <div className="text-sm" style={{ color: "var(--muted)" }}>
            Пока нет лидов. Создайте через `/widget` или квиз на главной.
          </div>
        ) : null}
      </div>
    </div>
    )
  );
}

