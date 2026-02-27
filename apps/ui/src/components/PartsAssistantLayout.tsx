"use client";

import { useCallback, useMemo } from "react";
import { VehicleSelector } from "./VehicleSelector";

type ChatResponseData = {
  session_id: string;
  summary: string;
  questions: { id: string; text: string }[];
  bundles: { economy?: unknown[]; optimal?: unknown[]; oem?: unknown[] };
  next_step: string;
  safety_notes: string[];
};

export type PartsAssistantMsg =
  | { role: "user"; text: string }
  | { role: "assistant"; text: string; chatResponse?: ChatResponseData | null; typing?: boolean };

type LayoutProps = {
  messages: PartsAssistantMsg[];
  text: string;
  loading: boolean;
  brand: string;
  model: string;
  year: string;
  engine: string;
  mileage: string;
  vin: string;
  onBrandChange: (v: string) => void;
  onModelChange: (v: string) => void;
  onYearChange: (v: string) => void;
  onEngineChange: (v: string) => void;
  onMileageChange: (v: string) => void;
  onVinChange: (v: string) => void;
  onTextChange: (v: string) => void;
  onSend: (msg: string) => void;
};

export function PartsAssistantLayout(props: LayoutProps) {
  const { messages, text, loading, brand, model, year, engine, mileage, vin } = props;
  const { onBrandChange, onModelChange, onYearChange, onEngineChange, onMileageChange, onVinChange, onTextChange, onSend } = props;

  const handleVehicleChange = useCallback(
    (v: { make?: { label: string } | null; model?: { label: string } | null; year?: number | null; engine?: { label: string } | null }) => {
      onBrandChange(v.make?.label ?? "");
      onModelChange(v.model?.label ?? "");
      onYearChange(v.year ? String(v.year) : "");
      onEngineChange(v.engine?.label ?? "");
    },
    [onBrandChange, onModelChange, onYearChange, onEngineChange]
  );

  const quick = useMemo(
    () => [
      { label: "ТО", message: "Нужно ТО" },
      { label: "Колодки", message: "Тормозные колодки передние" },
      { label: "Фильтр", message: "Масляный фильтр" },
      { label: "Свечи", message: "Свечи зажигания" },
    ],
    []
  );

  const carDisplay = [brand, model].filter(Boolean).join(" ").trim() || "—";
  const yearSuffix = year ? " " + year : "";

  return (
    <div className="space-y-6">
      <div className="card" style={{ background: "rgba(255,255,255,0.03)" }}>
        <div className="text-sm font-semibold mb-3">Данные автомобиля</div>
        <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>
          Чат учитывает эти данные при подборе. Заполните хотя бы марку, модель и год.
        </p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-6">
          <VehicleSelector onChange={handleVehicleChange} />
          <div className="field">
            <label className="mb-1 block text-xs font-medium" style={{ color: "var(--muted)" }}>
              Пробег
            </label>
            <input className="input" value={mileage} onChange={(e) => onMileageChange(e.target.value)} placeholder="Пробег" />
          </div>
          <div className="field">
            <label className="mb-1 block text-xs font-medium" style={{ color: "var(--muted)" }}>
              VIN
            </label>
            <input className="input" value={vin} onChange={(e) => onVinChange(e.target.value)} placeholder="VIN" />
          </div>
        </div>
      </div>
      <div className="card glass">
        <div className="mb-3 flex items-center justify-between">
          <div className="text-sm font-semibold">AI подборщик запчастей</div>
          <div className="text-xs" style={{ color: "var(--muted)" }}>{carDisplay}{yearSuffix}</div>
        </div>
        <div className="mb-3 flex flex-wrap gap-2">
          {quick.map((q) => (
            <button key={q.label} type="button" className="rounded-full border px-3 py-1.5 text-xs transition-colors hover:bg-white/5" style={{ borderColor: "var(--border)", color: "var(--muted)" }} onClick={() => onSend(q.message)} disabled={loading}>
              {q.label}
            </button>
          ))}
        </div>
        <div className="h-80 overflow-auto rounded-xl border p-3 scroll-smooth" style={{ borderColor: "var(--border)" }}>
          <div className="flex flex-col gap-3">
            {messages.map((m, idx) => (
              <div key={idx} className={m.role === "user" ? "self-end" : "self-start"}>
                <div className="max-w-[90%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm" style={{ background: m.role === "user" ? "rgba(225,29,46,0.12)" : "rgba(255,255,255,0.04)", border: "1px solid var(--border)" }}>
                  {"typing" in m && m.typing ? <TypingBubble /> : m.text}
                  {"chatResponse" in m && m.chatResponse ? <AssistantBlock data={m.chatResponse} /> : null}
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="mt-3 flex gap-2">
          <input className="input flex-1" value={text} onChange={(e) => onTextChange(e.target.value)} placeholder="Напишите запрос: колодки, фильтр, ТО, артикул…" onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSend(text); } }} />
          <button type="button" className="btn-primary" disabled={loading} onClick={() => onSend(text)}>
            {loading ? "..." : "Отправить"}
          </button>
        </div>
      </div>
    </div>
  );
}

function TypingBubble() {
  return (
    <div className="flex gap-1" aria-label="Ассистент печатает">
      <span className="h-2 w-2 rounded-full bg-current opacity-60 animate-pulse" />
      <span className="h-2 w-2 rounded-full bg-current opacity-60 animate-pulse" style={{ animationDelay: "0.2s" }} />
      <span className="h-2 w-2 rounded-full bg-current opacity-60 animate-pulse" style={{ animationDelay: "0.4s" }} />
    </div>
  );
}

function money(v: unknown): string {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  return `${Math.round(n).toLocaleString("ru")} ₽`;
}

function AssistantBlock({ data }: { data: ChatResponseData }) {
  const tiers: { key: "economy" | "optimal" | "oem"; label: string }[] = [
    { key: "economy", label: "Эконом" },
    { key: "optimal", label: "Оптимум" },
    { key: "oem", label: "OEM" },
  ];

  return (
    <div className="mt-3 space-y-3 border-t pt-3" style={{ borderColor: "var(--border)" }}>
      {data.questions?.length > 0 ? (
        <div>
          <div className="text-xs font-semibold mb-1.5" style={{ color: "var(--muted)" }}>Уточните:</div>
          <div className="flex flex-wrap gap-1.5">
            {data.questions.map((q) => (
              <span key={q.id} className="rounded-full border px-2.5 py-1 text-xs" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.03)" }}>
                {q.text}
              </span>
            ))}
          </div>
        </div>
      ) : null}
      {Object.keys(data.bundles || {}).length > 0 ? (
        <div>
          <div className="text-xs font-semibold mb-1.5" style={{ color: "var(--muted)" }}>Варианты:</div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {tiers.map(({ key, label }) => {
              const items = (data.bundles || {})[key] || [];
              if (!Array.isArray(items) || items.length === 0) return null;
              return (
                <div key={key} className="rounded-xl border p-3" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
                  <div className="text-xs font-semibold mb-2" style={{ color: "var(--muted)" }}>{label}</div>
                  {(items as { name?: string; brand?: string; oem?: string; price?: number; in_stock?: boolean; delivery_days?: number }[]).slice(0, 2).map((p, i) => (
                    <div key={i} className="text-xs py-1.5 border-b last:border-b-0" style={{ borderColor: "var(--border)" }}>
                      <div className="font-medium">{p.name || "Запчасть"}</div>
                      <div style={{ color: "var(--muted)" }}>{p.brand || ""} {p.oem ? " • " + p.oem : ""}</div>
                      <div style={{ color: "var(--muted)" }}>{money(p.price)} • {p.in_stock ? (p.delivery_days ?? "—") + " дн." : "Под заказ"}</div>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
      {(data.safety_notes || []).map((n, i) => (
        <div key={i} className="text-xs" style={{ color: "var(--muted)" }}>⚠️ {n}</div>
      ))}
    </div>
  );
}
