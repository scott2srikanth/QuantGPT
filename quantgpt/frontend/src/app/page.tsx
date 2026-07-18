import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-4xl font-bold tracking-tight">QuantGPT</h1>
      <p className="mt-3 text-lg opacity-80">
        AI-assisted algorithmic trading intelligence layer. Integrates with OpenAlgo through a
        dedicated Integration Layer — OpenAlgo is never modified.
      </p>
      <p className="mt-2 text-sm opacity-60">
        Project infrastructure only. No AI and no trading logic yet.
      </p>
      <div className="mt-8 flex gap-4">
        <Link
          href="/health"
          className="rounded-md bg-brand-500 px-4 py-2 text-white hover:bg-brand-600"
        >
          Health
        </Link>
        <Link
          href="/login"
          className="rounded-md border border-brand-500 px-4 py-2 text-brand-600 hover:bg-brand-50"
        >
          Login
        </Link>
      </div>
    </main>
  );
}
