"use client";

import { useEffect, useMemo, useState } from "react";
import { useToast } from "@/components/ToastProvider";

const CORE_URL = process.env.NEXT_PUBLIC_CORE_API_URL || "http://localhost:8000";

type EstimateUIJob = { name: string; qty?: number; unit_price?: number | null; total?: number | null };
type EstimateUIPart = {
  name: string;
  brand?: string | null;
  oem?: string | null;
  sku?: string | null;
  unit_price?: number | null;
  stock?: number | null;
  delivery_days?: number | null;
};
type EstimateUI = {
  jobs: EstimateUIJob[];
  parts: { economy: EstimateUIPart[]; optimum: EstimateUIPart[]; oem: EstimateUIPart[] };
  totals: { jobs_total?: number | null; parts_total?: number | null; total?: number | null };
  requires_approval: boolean;
};

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

function Tier({ title, hint, parts }: { title: string; hint: string; parts: EstimateUIPart[] }) {
  return (
    <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">{title}</div>
          <div className="text-xs" style={{ color: "var(--muted)" }}>
            {hint}
          </div>
        </div>
        <div className="text-xs" style={{ color: "var(--muted)" }}>
          {parts?.[0]?.unit_price ? money(parts[0].unit_price) : "—"}
        </div>
      </div>
      <div className="mt-3 space-y-2">
        {parts?.length ? (
          parts.map((p, idx) => (
            <div key={idx} className="rounded-xl border px-3 py-2 text-sm" style={{ borderColor: "var(--border)" }}>
              <div className="font-medium">{p.name}</div>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                {p.brand ? `${p.brand} • ` : ""}oem={p.oem || "—"} • sku={p.sku || "—"}
              </div>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                цена={money(p.unit_price)} • stock={p.stock ?? "—"} • {p.delivery_days ?? "—"} дн.
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

export function ResultClient({ leadId }: { leadId: string }) {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [estimate, setEstimate] = useState<EstimateUI | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const tiers = useMemo(() => {
    return {
      economy: estimate?.parts?.economy || [],
      optimum: estimate?.parts?.optimum || [],
      oem: estimate?.parts?.oem || [],
    };
  }, [estimate]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      // take latest estimate for lead
      const r = await fetch(`${CORE_URL}/api/estimates?lead_id=${leadId}`, { cache: "no-store" });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || r.statusText);
      const latest = Array.isArray(data) ? data[0] : null;
      const ui = latest?.items?.ui || null;
      // fallback: if backend didn't store estimate_ui, compute minimal view from items
      if (ui) {
        setEstimate(ui as EstimateUI);
      } else if (latest?.items) {
        const items = latest.items || {};
        setEstimate({
          jobs: Array.isArray(items.jobs) ? items.jobs : [],
          parts: { economy: [], optimum: Array.isArray(items.parts) ? items.parts : [], oem: [] },
          totals: items.totals || { total: latest.total_price },
          requires_approval: Boolean(latest.requires_approval ?? true),
        });
      } else {
        setEstimate(null);
      }
    } catch (e: any) {
      setError(e?.message || "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }

  async function submitApplication() {
    setSubmitting(true);
    try {
      const r = await fetch(`${CORE_URL}/api/leads/${leadId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "submitted" }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || r.statusText);
      toast.success("Заявка отправлена оператору. Мы свяжемся с вами для подтверждения.", "Готово");
    } catch {
      toast.error("Что-то пошло не так, попробуйте ещё раз.", "Ошибка");
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leadId]);

  if (loading && !estimate) {
    return (
      <div className="card glass">
        <div className="text-sm font-semibold">Загрузка…</div>
        <div className="mt-2 text-sm" style={{ color: "var(--muted)" }}>
          Собираю расчёт.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="card glass">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <div className="text-sm font-semibold">Итог (черновик)</div>
            <div className="mt-1 text-sm" style={{ color: "var(--muted)" }}>
              Работы + варианты расходников. Нажмите “Отправить заявку”, чтобы оператор подтвердил и предложил запись.
            </div>
          </div>
          <div className="rounded-xl border px-4 py-3 text-sm" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
            <div style={{ color: "var(--muted)" }}>Итого</div>
            <div className="text-lg font-semibold">{money(estimate?.totals?.total)}</div>
          </div>
        </div>
        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <button className="btn-primary" onClick={submitApplication} disabled={submitting}>
            {submitting ? "Отправка…" : "Отправить заявку / Продолжить"}
          </button>
          <button className="btn-secondary" onClick={load} disabled={loading}>
            {loading ? "Обновляю…" : "Обновить"}
          </button>
        </div>
      </div>

      {error ? (
        <div className="card">
          <div className="text-sm font-semibold">Не удалось загрузить</div>
          <div className="mt-1 text-sm" style={{ color: "var(--muted)" }}>
            {error}
          </div>
        </div>
      ) : null}

      <div className="grid gap-3 md:grid-cols-3">
        <Tier title="Эконом" hint="Оптимально по цене" parts={tiers.economy} />
        <Tier title="Оптимум" hint="Баланс цена/ресурс" parts={tiers.optimum} />
        <Tier title="OEM" hint="Максимально близко к оригиналу" parts={tiers.oem} />
      </div>

      <div className="card glass">
        <div className="text-sm font-semibold">Работы</div>
        <div className="mt-3 space-y-2">
          {estimate?.jobs?.length ? (
            estimate.jobs.map((j, idx) => (
              <div key={idx} className="rounded-xl border px-3 py-2 text-sm" style={{ borderColor: "var(--border)" }}>
                <div className="font-medium">{j.name}</div>
                <div className="text-xs" style={{ color: "var(--muted)" }}>
                  qty={j.qty ?? 1} • unit={money(j.unit_price)} • total={money(j.total)}
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
  );
}

