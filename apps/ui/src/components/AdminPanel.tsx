"use client";

import { useEffect, useMemo, useState } from "react";
import { useToast } from "@/components/ToastProvider";

const CORE_URL = process.env.NEXT_PUBLIC_CORE_API_URL || "http://localhost:8000";
const PAGES_PREVIEW = process.env.NEXT_PUBLIC_PAGES_PREVIEW === "true";

type Supplier = { id: string; name: string; delivery_days?: number | null; terms?: string | null };
type PricingRule = { id: string; name: string; rule_type: string; params?: any };
type CatalogJob = { id: string; code: string; name: string; description?: string | null; base_price: number; norm_hours: number };
type Doc = { id: string; title: string; source?: string | null; uploaded_at: string };
type Offer = { supplier_id: string; sku?: string | null; oem?: string | null; name?: string | null; brand?: string | null; price?: number | null; stock?: number | null; delivery_days?: number | null };

export function AdminPanel() {
  const toast = useToast();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [rules, setRules] = useState<PricingRule[]>([]);
  const [jobs, setJobs] = useState<CatalogJob[]>([]);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [supplierId, setSupplierId] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [doc, setDoc] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");
  const [offerQuery, setOfferQuery] = useState<string>("колодки Camry 50");
  const [offers, setOffers] = useState<Offer[]>([]);
  const [compareOem, setCompareOem] = useState<string>("04465-33480");
  const [compare, setCompare] = useState<Offer[]>([]);

  const createRuleDefaults = useMemo(() => ({ name: "", rule_type: "percent_add_total", params: { percent: 10 } }), []);
  const [newRule, setNewRule] = useState<any>(createRuleDefaults);
  const [newJob, setNewJob] = useState<any>({ code: "", name: "", description: "", base_price: 0, norm_hours: 0 });

  async function load() {
    if (PAGES_PREVIEW) return;
    setStatus("");
    const [sRes, rRes, jRes, dRes] = await Promise.all([
      fetch(`${CORE_URL}/api/suppliers`),
      fetch(`${CORE_URL}/api/admin/pricing_rules`),
      fetch(`${CORE_URL}/api/catalog/jobs`),
      fetch(`${CORE_URL}/api/documents`),
    ]);
    const sData = await sRes.json();
    const rData = await rRes.json();
    const jData = await jRes.json();
    const dData = await dRes.json();
    if (sRes.ok) setSuppliers(sData);
    if (rRes.ok) setRules(rData);
    if (jRes.ok) setJobs(jData);
    if (dRes.ok) setDocs(dData);
    if (!supplierId && sData?.[0]?.id) setSupplierId(sData[0].id);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function importPrice() {
    if (!supplierId || !file) return;
    setStatus("Импорт...");
    const fd = new FormData();
    fd.append("supplier_id", supplierId);
    fd.append("file", file);
    const r = await fetch(`${CORE_URL}/api/suppliers/import`, { method: "POST", body: fd });
    const data = await r.json();
    if (!r.ok) {
      toast.error("Что-то пошло не так, попробуйте ещё раз.", "Импорт прайса");
      setStatus(`Ошибка: ${data?.detail || "import failed"}`);
      return;
    }
    toast.success(`Импортировано: ${data.imported}`, "Прайс загружен");
    setStatus(`Готово: imported=${data.imported}`);
  }

  async function uploadDoc() {
    if (!doc) return;
    setStatus("Загрузка документа...");
    const fd = new FormData();
    fd.append("file", doc);
    const r = await fetch(`${CORE_URL}/api/documents/upload`, { method: "POST", body: fd });
    const data = await r.json();
    if (!r.ok) {
      toast.error("Что-то пошло не так, попробуйте ещё раз.", "Документы");
      setStatus(`Ошибка: ${data?.detail || "upload failed"}`);
      return;
    }
    toast.success(`chunks=${data.chunks}`, "Документ загружен");
    setStatus(`Документ загружен: chunks=${data.chunks}`);
    await load();
  }

  async function searchOffers() {
    setStatus("Поиск офферов...");
    const r = await fetch(`${CORE_URL}/api/parts/search?query=${encodeURIComponent(offerQuery)}`, { cache: "no-store" });
    const data = await r.json();
    if (!r.ok) {
      setStatus(`Ошибка: ${data?.detail || "search failed"}`);
      return;
    }
    setOffers(data);
    setStatus(`Найдено офферов: ${data.length}`);
  }

  async function compareOffers() {
    setStatus("Сравнение...");
    const r = await fetch(`${CORE_URL}/api/parts/compare?oem=${encodeURIComponent(compareOem)}`, { cache: "no-store" });
    const data = await r.json();
    if (!r.ok) {
      setStatus(`Ошибка: ${data?.detail || "compare failed"}`);
      return;
    }
    setCompare(data);
    setStatus(`Сравнение: ${data.length} офферов`);
  }

  async function createPricingRule() {
    setStatus("Создаю правило...");
    const r = await fetch(`${CORE_URL}/api/admin/pricing_rules`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newRule),
    });
    const data = await r.json();
    if (!r.ok) {
      setStatus(`Ошибка: ${data?.detail || "create failed"}`);
      return;
    }
    toast.success("Правило добавлено", "Pricing rules");
    setNewRule(createRuleDefaults);
    await load();
  }

  async function createCatalogJob() {
    setStatus("Создаю работу...");
    const r = await fetch(`${CORE_URL}/api/catalog/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newJob),
    });
    const data = await r.json();
    if (!r.ok) {
      setStatus(`Ошибка: ${data?.detail || "create failed"}`);
      return;
    }
    toast.success("Работа добавлена", "Каталог");
    setNewJob({ code: "", name: "", description: "", base_price: 0, norm_hours: 0 });
    await load();
  }

  return (
    PAGES_PREVIEW ? (
      <div className="card glass">
        <div className="text-sm font-semibold">Админ-панель недоступна в GitHub Pages</div>
        <div className="mt-2 text-sm" style={{ color: "var(--muted)" }}>
          Pages показывает только превью интерфейса. Для работы админки нужен локальный запуск backend.
        </div>
      </div>
    ) : (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div className="card glass">
        <div className="text-sm font-semibold">Поставщики и импорт прайса</div>
        <div className="mt-2 text-sm" style={{ color: "var(--muted)" }}>
          Поддержка CSV/XLSX. Нормализация колонок: sku/oem/name/brand/price/stock/delivery_days.
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3">
          <select className="input" value={supplierId} onChange={(e) => setSupplierId(e.target.value)}>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          <input className="input" type="file" accept=".csv,.xlsx" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          <button className="btn-primary" onClick={importPrice} disabled={!supplierId || !file}>
            Импортировать прайс
          </button>
        </div>
      </div>

      <div className="card glass">
        <div className="text-sm font-semibold">Документы (RAG)</div>
        <div className="mt-2 text-sm" style={{ color: "var(--muted)" }}>
          Загрузка через core-api (прокси в RAG сервис) + список документов в базе.
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3">
          <input className="input" type="file" accept=".txt,.md,.csv" onChange={(e) => setDoc(e.target.files?.[0] || null)} />
          <button className="btn-primary" onClick={uploadDoc} disabled={!doc}>
            Загрузить документ
          </button>
        </div>
        <div className="mt-4 rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
          <div className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
            Документы
          </div>
          <div className="mt-2 space-y-2">
            {(docs || []).slice(0, 10).map((d) => (
              <div key={d.id} className="rounded-xl border px-3 py-2 text-sm" style={{ borderColor: "var(--border)" }}>
                <div className="font-medium">{d.title}</div>
                <div className="text-xs" style={{ color: "var(--muted)" }}>
                  {d.source || "—"} • {new Date(d.uploaded_at).toLocaleString()}
                </div>
              </div>
            ))}
            {!docs.length ? (
              <div className="text-sm" style={{ color: "var(--muted)" }}>
                Пока нет документов.
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <div className="card glass lg:col-span-2">
        <div className="text-sm font-semibold">Каталог работ и правила ценообразования</div>
        <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
            <div className="text-sm font-semibold">Catalog jobs</div>
            <div className="mt-3 grid grid-cols-1 gap-2">
              <input className="input" value={newJob.code} onChange={(e) => setNewJob((v: any) => ({ ...v, code: e.target.value }))} placeholder="code" />
              <input className="input" value={newJob.name} onChange={(e) => setNewJob((v: any) => ({ ...v, name: e.target.value }))} placeholder="name" />
              <input
                className="input"
                value={newJob.base_price}
                onChange={(e) => setNewJob((v: any) => ({ ...v, base_price: Number(e.target.value) || 0 }))}
                placeholder="base_price"
              />
              <button className="btn-secondary" onClick={createCatalogJob} disabled={!newJob.code || !newJob.name}>
                Добавить работу
              </button>
            </div>
            <div className="mt-3 space-y-2">
              {(jobs || []).slice(0, 8).map((j) => (
                <div key={j.id} className="rounded-xl border px-3 py-2 text-sm" style={{ borderColor: "var(--border)" }}>
                  <div className="font-medium">{j.name}</div>
                  <div className="text-xs" style={{ color: "var(--muted)" }}>
                    {j.code} • {Math.round(Number(j.base_price || 0))} ₽
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
            <div className="text-sm font-semibold">Pricing rules</div>
            <div className="mt-3 grid grid-cols-1 gap-2">
              <input className="input" value={newRule.name} onChange={(e) => setNewRule((v: any) => ({ ...v, name: e.target.value }))} placeholder="name" />
              <select className="input" value={newRule.rule_type} onChange={(e) => setNewRule((v: any) => ({ ...v, rule_type: e.target.value }))}>
                <option value="percent_add_total">percent_add_total</option>
                <option value="percent_mult_total">percent_mult_total</option>
                <option value="fixed_add_total">fixed_add_total</option>
              </select>
              <textarea
                className="input"
                value={JSON.stringify(newRule.params || {}, null, 2)}
                onChange={(e) => {
                  try {
                    setNewRule((v: any) => ({ ...v, params: JSON.parse(e.target.value) }));
                  } catch {}
                }}
                rows={4}
              />
              <button className="btn-secondary" onClick={createPricingRule} disabled={!newRule.name || !newRule.rule_type}>
                Добавить правило
              </button>
            </div>
            <div className="mt-3 grid grid-cols-1 gap-2">
              {rules.map((r) => (
                <div key={r.id} className="rounded-xl border px-3 py-2 text-sm" style={{ borderColor: "var(--border)" }}>
                  <div className="font-medium">{r.name}</div>
                  <div className="text-xs" style={{ color: "var(--muted)" }}>
                    {r.rule_type}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="card glass lg:col-span-2">
        <div className="text-sm font-semibold">Поиск и сравнение офферов</div>
        <div className="mt-2 text-sm" style={{ color: "var(--muted)" }}>
          Использует `/api/parts/search` и `/api/parts/compare`.
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
            <div className="text-sm font-semibold">Search</div>
            <div className="mt-3 flex gap-2">
              <input className="input" value={offerQuery} onChange={(e) => setOfferQuery(e.target.value)} />
              <button className="btn-secondary" onClick={searchOffers}>
                Найти
              </button>
            </div>
            <div className="mt-3 space-y-2">
              {(offers || []).slice(0, 8).map((o, idx) => (
                <div key={idx} className="rounded-xl border px-3 py-2 text-sm" style={{ borderColor: "var(--border)" }}>
                  <div className="font-medium">{o.name || "Запчасть"}</div>
                  <div className="text-xs" style={{ color: "var(--muted)" }}>
                    {o.brand ? `${o.brand} • ` : ""}oem={o.oem || "—"} • sku={o.sku || "—"} • {o.price ?? "—"} ₽
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
            <div className="text-sm font-semibold">Compare by OEM</div>
            <div className="mt-3 flex gap-2">
              <input className="input" value={compareOem} onChange={(e) => setCompareOem(e.target.value)} />
              <button className="btn-secondary" onClick={compareOffers}>
                Сравнить
              </button>
            </div>
            <div className="mt-3 space-y-2">
              {(compare || []).slice(0, 8).map((o, idx) => (
                <div key={idx} className="rounded-xl border px-3 py-2 text-sm" style={{ borderColor: "var(--border)" }}>
                  <div className="font-medium">{o.name || "Запчасть"}</div>
                  <div className="text-xs" style={{ color: "var(--muted)" }}>
                    {o.brand ? `${o.brand} • ` : ""}sku={o.sku || "—"} • {o.price ?? "—"} ₽ • stock={o.stock ?? "—"} • {o.delivery_days ?? "—"} дн.
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      {status ? (
        <div className="card glass lg:col-span-2">
          <div className="text-sm" style={{ color: "var(--muted)" }}>
            {status}
          </div>
        </div>
      ) : null}
    </div>
    )
  );
}

