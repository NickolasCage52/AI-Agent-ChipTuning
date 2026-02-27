"use client";

interface Bundle {
  id?: string;
  name: string;
  brand?: string | null;
  sku?: string | null;
  oem?: string | null;
  price?: number | null;
  delivery_days?: number | null;
  in_stock?: boolean;
  stock?: number | null;
  rationale?: string;
}

interface ChatResponseData {
  summary: string;
  questions: { id: string; text: string }[];
  bundles: {
    economy?: Bundle[];
    optimal?: Bundle[];
    oem?: Bundle[];
  };
  next_step: string;
  safety_notes: string[];
}

function money(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  return `${Math.round(n).toLocaleString("ru")} ₽`;
}

export function AssistantMessage({ data }: { data: ChatResponseData }) {
  const tiers = [
    { key: "economy" as const, label: "Эконом" },
    { key: "optimal" as const, label: "Оптимум" },
    { key: "oem" as const, label: "OEM" },
  ];

  return (
    <div className="assistant-message space-y-4">
      <div className="summary-block">
        <p className="text-sm">{data.summary}</p>
      </div>

      {data.questions?.length > 0 && (
        <div className="clarify-block">
          <h4 className="text-xs font-semibold mb-2" style={{ color: "var(--muted)" }}>Уточните:</h4>
          <div className="flex flex-wrap gap-2">
            {data.questions.map((q) => (
              <div
                key={q.id}
                className="question-chip rounded-full border px-3 py-1.5 text-xs cursor-default"
                style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.03)" }}
              >
                {q.text}
              </div>
            ))}
          </div>
        </div>
      )}

      {data.bundles && Object.keys(data.bundles).length > 0 && (
        <div className="variants-block">
          <h4 className="text-xs font-semibold mb-2" style={{ color: "var(--muted)" }}>Варианты:</h4>
          <div className="grid gap-3 md:grid-cols-3">
            {tiers.map(({ key, label }) => {
              const items = data.bundles[key];
              if (!items?.length) return null;
              return (
                <div
                  key={key}
                  className={`tier-card rounded-2xl border p-4`}
                  style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}
                >
                  <div className="text-xs font-semibold mb-2" style={{ color: "var(--muted)" }}>
                    {key === "economy" ? "Эконом" : key === "optimal" ? "Оптимум" : "OEM"}
                  </div>
                  <div className="space-y-2">
                    {items.map((item, i) => (
                      <div
                        key={i}
                        className="part-item rounded-xl border px-3 py-2 text-sm"
                        style={{ borderColor: "var(--border)" }}
                      >
                        <div className="font-medium">{item.name || "Запчасть"}</div>
                        <div className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                          {item.brand && <span>{item.brand}</span>}
                          {item.oem && <span> • Арт: {item.oem}</span>}
                        </div>
                        <div className="text-xs mt-0.5 flex justify-between" style={{ color: "var(--muted)" }}>
                          <span>{money(item.price)}</span>
                          <span>{item.in_stock ? `${item.delivery_days ?? "—"} дн.` : "Под заказ"}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {data.next_step === "show_offers" && data.bundles && Object.keys(data.bundles).length > 0 && (
        <div className="next-step-block">
          <p className="text-xs mb-2" style={{ color: "var(--muted)" }}>Выберите вариант или задайте вопрос:</p>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-select rounded-lg border px-3 py-2 text-xs" style={{ borderColor: "var(--border)" }}>
              Выбрать эконом
            </button>
            <button type="button" className="btn-select rounded-lg border px-3 py-2 text-xs" style={{ borderColor: "var(--border)" }}>
              Выбрать оптимум
            </button>
            <button type="button" className="btn-select rounded-lg border px-3 py-2 text-xs" style={{ borderColor: "var(--border)" }}>
              Выбрать OEM
            </button>
          </div>
        </div>
      )}

      {data.safety_notes?.map((note, i) => (
        <div key={i} className="safety-note text-xs" style={{ color: "var(--muted)" }}>
          ⚠️ {note}
        </div>
      ))}
    </div>
  );
}
