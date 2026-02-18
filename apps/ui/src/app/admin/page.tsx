import { AdminPanel } from "@/components/AdminPanel";

export default function AdminPage() {
  return (
    <main className="container-page py-10">
      <div className="mb-6">
        <div className="text-2xl font-semibold">Админ</div>
        <div className="text-sm" style={{ color: "var(--muted)" }}>
          Seed-данные (работы/правила/поставщики), импорт прайса, загрузка документов (RAG).
        </div>
      </div>
      <AdminPanel />
    </main>
  );
}

