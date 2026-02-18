import { OperatorLeadDetail } from "@/components/OperatorLeadDetail";

export const dynamicParams = false;

export function generateStaticParams() {
  // GitHub Pages build needs at least one static param to export dynamic route.
  return [{ id: "demo" }];
}

export default function OperatorLeadDetailPage({ params }: { params: { id: string } }) {
  return (
    <main className="container-page py-10">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="text-2xl font-semibold">Оператор • Lead</div>
          <div className="text-sm" style={{ color: "var(--muted)" }}>
            Детали лида + `agent_runs` + сметы/approval.
          </div>
        </div>
        <a
          href="/operator/leads"
          className="rounded-xl border px-4 py-2 text-sm font-semibold"
          style={{ borderColor: "var(--border)" }}
        >
          ← К списку
        </a>
      </div>
      <OperatorLeadDetail leadId={params.id} />
    </main>
  );
}

