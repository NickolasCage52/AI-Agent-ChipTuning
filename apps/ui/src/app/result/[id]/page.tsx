import { ResultClient } from "@/components/ResultClient";

export const dynamicParams = false;

export function generateStaticParams() {
  // GitHub Pages build needs at least one static param to export dynamic route.
  return [{ id: "demo" }];
}

export default function ResultPage({ params }: { params: { id: string } }) {
  return (
    <main className="container-page py-10">
      <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="text-2xl font-semibold">Результат расчёта</div>
          <div className="text-sm" style={{ color: "var(--muted)" }}>
            Варианты комплектаций и черновик сметы. Финальная стоимость — после подтверждения оператором.
          </div>
        </div>
        <a className="btn-secondary" href="/widget">
          ← Вернуться в чат
        </a>
      </div>
      <ResultClient leadId={params.id} />
    </main>
  );
}

