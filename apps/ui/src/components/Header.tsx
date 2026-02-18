export function Header() {
  const pagesPreview = process.env.NEXT_PUBLIC_PAGES_PREVIEW === "true";
  const repoUrl = process.env.NEXT_PUBLIC_REPO_URL || "https://github.com";
  return (
    <header className="border-b" style={{ borderColor: "var(--border)" }}>
      <div className="container-page flex h-16 items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className="h-9 w-9 rounded-xl"
            style={{
              background: "linear-gradient(135deg, var(--primary), rgba(255,255,255,0.08))",
            }}
            aria-hidden
          />
          <div className="leading-tight">
            <a href="/" className="font-semibold hover:opacity-95">
              Chiptuning / Автосервис
            </a>
            <div className="text-sm" style={{ color: "var(--muted)" }}>
              локальный AI‑приёмщик
            </div>
          </div>
        </div>
        <nav className="flex items-center gap-4 text-sm" style={{ color: "var(--muted)" }}>
          <a className="hover:text-fg" href="/#quiz">
            Рассчитать
          </a>
          {!pagesPreview ? (
            <>
              <a className="hover:text-fg" href="/operator/leads">
                Оператор
              </a>
              <a className="hover:text-fg" href="/admin">
                Админ
              </a>
            </>
          ) : (
            <a className="hover:text-fg" href={repoUrl} target="_blank" rel="noreferrer">
              Запустить локально (README)
            </a>
          )}
        </nav>
      </div>
      {pagesPreview ? (
        <div className="border-t" style={{ borderColor: "var(--border)" }}>
          <div className="container-page py-2 text-xs" style={{ color: "var(--muted)" }}>
            GitHub Pages — это превью интерфейса. Backend не разворачивается в Pages; для полного демо запустите локально:{" "}
            <span className="text-fg">docker compose up --build</span>
          </div>
        </div>
      ) : null}
    </header>
  );
}

