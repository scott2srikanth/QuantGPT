"use client";

import { useEffect, useState } from "react";

type Health = {
  status: string;
  version: string;
  environment: string;
  timestamp: string;
};

export default function HealthPage() {
  const [data, setData] = useState<Health | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/proxy/health")
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setErr(String(e)));
  }, []);

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-2xl font-bold">Health</h1>
      {err && <p className="mt-4 text-red-500">error: {err}</p>}
      {data && (
        <pre className="mt-4 rounded-md bg-black/5 p-4 text-sm dark:bg-white/10">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
      {!data && !err && <p className="mt-4 opacity-60">loading…</p>}
    </main>
  );
}
