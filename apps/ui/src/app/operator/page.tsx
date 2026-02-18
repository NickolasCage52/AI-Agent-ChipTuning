import { OperatorPanel } from "@/components/OperatorPanel";

export default function OperatorPage() {
  return (
    <main className="container-page py-10">
      <div className="mb-6">
        <div className="text-2xl font-semibold">Оператор</div>
        <div className="text-sm" style={{ color: "var(--muted)" }}>
          Быстрый обзор. Для Slice 1 маршрутов используйте `/operator/leads` и `/operator/leads/[id]`.
        </div>
      </div>
      <OperatorPanel />
    </main>
  );
}

