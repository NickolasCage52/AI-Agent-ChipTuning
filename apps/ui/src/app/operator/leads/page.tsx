import { OperatorLeadsList } from "@/components/OperatorLeadsList";

export default function OperatorLeadsPage() {
  return (
    <main className="container-page py-10">
      <div className="mb-6">
        <div className="text-2xl font-semibold">Оператор • Leads</div>
        <div className="text-sm" style={{ color: "var(--muted)" }}>
          Slice 1: листинг лидов (chat → lead → UI list).
        </div>
      </div>
      <OperatorLeadsList />
    </main>
  );
}

