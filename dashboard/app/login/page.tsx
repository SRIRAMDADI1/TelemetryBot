import { Suspense } from "react";
import { BrandScreen } from "@/components/Brand";
import { LoginForm } from "@/components/LoginForm";
import { API_BASE, fetchProviders } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function LoginPage() {
  let providers;
  try {
    providers = await fetchProviders();
  } catch {
    return (
      <BrandScreen title="Collector unreachable">
        <p>
          Pulse couldn’t reach <span className="font-mono text-paper">{API_BASE}</span>. Start the
          server, then refresh.
        </p>
      </BrandScreen>
    );
  }

  return (
    <Suspense fallback={<main className="px-6 py-20 text-center text-mist">Loading Pulse…</main>}>
      <LoginForm providers={providers} />
    </Suspense>
  );
}
