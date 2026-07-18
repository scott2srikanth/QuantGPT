export function Header() {
  return (
    <header className="border-b border-black/10 dark:border-white/10">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <span className="font-semibold">QuantGPT</span>
        <nav className="flex gap-4 text-sm">
          <a href="/" className="hover:underline">Home</a>
          <a href="/health" className="hover:underline">Health</a>
          <a href="/login" className="hover:underline">Login</a>
        </nav>
      </div>
    </header>
  );
}
