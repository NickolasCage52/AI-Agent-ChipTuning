import { QuizForm } from "@/components/QuizForm";

const brands = ["Kia", "Hyundai", "Toyota", "VW", "BMW", "Mercedes", "Audi", "Skoda"];

export default function Page() {
  return (
    <main>
      <section className="border-b" style={{ borderColor: "var(--border)" }}>
        <div className="container-page py-10 md:py-16">
          <div className="grid grid-cols-1 gap-8 md:grid-cols-2 md:items-center">
            <div>
              <div className="badge">
                <span aria-hidden style={{ width: 8, height: 8, borderRadius: 999, background: "var(--accent)", boxShadow: "0 0 18px rgba(82,255,168,0.45)" }} />
                Локально • без внешних интеграций • demo-ready
              </div>
              <h1 className="mt-5 font-semibold leading-tight" style={{ fontFamily: "var(--font-display)", fontSize: 46 }}>
                Премиальный сервис
                <br />
                с AI‑приёмщиком
              </h1>
              <p className="mt-4 text-base" style={{ color: "var(--muted)" }}>
                В пару сообщений соберём детали по авто и запросу, сформируем предварительную смету и варианты комплектаций. Финальная стоимость — только после подтверждения оператором.
              </p>
              <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                <a className="btn-primary" href="#quiz">
                  Рассчитать стоимость
                </a>
                <a className="btn-secondary" href="/widget">
                  Открыть чат
                </a>
              </div>
              <div className="mt-4 text-xs" style={{ color: "var(--muted)" }}>
                Политика: диагноз не утверждаем без осмотра. Любые деньги/закуп — только после подтверждения.
              </div>
            </div>
            <div className="card glass">
              <div className="text-sm font-semibold">Что вы получите</div>
              <div className="mt-3 grid grid-cols-1 gap-3">
                <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
                  <div className="text-xs" style={{ color: "var(--muted)" }}>
                    Предварительная смета
                  </div>
                  <div className="mt-1 text-lg font-semibold">работы + расходники</div>
                </div>
                <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
                  <div className="text-xs" style={{ color: "var(--muted)" }}>
                    Варианты комплектаций
                  </div>
                  <div className="mt-1 text-lg font-semibold">эконом / оптимум / OEM</div>
                </div>
                <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
                  <div className="text-xs" style={{ color: "var(--muted)" }}>
                    Следующий шаг
                  </div>
                  <div className="mt-1 text-lg font-semibold">подтверждение оператором</div>
                </div>
              </div>
              <div className="mt-4 text-sm" style={{ color: "var(--muted)" }}>
                Для точного подбора ускоряет VIN (если есть). Для симптомов — 1–2 уточнения.
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="container-page py-10">
        <div className="mb-4 text-sm font-semibold">Выбор марки</div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {brands.map((b) => (
            <div key={b} className="rounded-2xl border px-4 py-4 text-center font-semibold" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
              {b}
            </div>
          ))}
        </div>
      </section>

      <section id="quiz" className="container-page pb-16">
        <div className="mb-4 text-sm font-semibold">Быстрый расчёт</div>
        <QuizForm />
      </section>
    </main>
  );
}

