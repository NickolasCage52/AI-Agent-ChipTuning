import { PartsAssistant } from "@/components/PartsAssistant";

export default function Page() {
  return (
    <main>
      <section className="border-b" style={{ borderColor: "var(--border)" }}>
        <div className="container-page py-8 md:py-12">
          <div className="max-w-3xl">
            <div className="badge">
              <span
                aria-hidden
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: 999,
                  background: "var(--accent)",
                  boxShadow: "0 0 18px rgba(82,255,168,0.45)",
                }}
              />
              AI подбор запчастей
            </div>
            <h1 className="mt-4 font-semibold leading-tight" style={{ fontFamily: "var(--font-display)", fontSize: 36 }}>
              Подборщик запчастей
            </h1>
            <p className="mt-2 text-base" style={{ color: "var(--muted)" }}>
              Заполните данные авто, напишите что нужно — получите варианты в эконом, оптимум и OEM.
            </p>
          </div>
        </div>
      </section>

      <section className="container-page py-8 pb-16">
        <PartsAssistant />
      </section>
    </main>
  );
}
