import { redirect } from "next/navigation";
import { PulseWordmark } from "@/components/Brand";
import { TopBar } from "@/components/Shell";
import { AuthError } from "@/lib/api";
import { fetchMe, fetchProjects } from "@/lib/server-api";

export const dynamic = "force-dynamic";

const highlights = [
  { label: "Tokens", body: "See what every run actually spent." },
  { label: "Cost", body: "Watch spend land live, by repo." },
  { label: "Efficiency", body: "Success rate, latency, and cost per outcome." },
];

export default async function HomePage() {
  const user = await fetchMe().catch(() => null);
  if (!user) redirect("/login");

  let first: string | null = null;
  try {
    const projects = await fetchProjects();
    first = projects[0]?.slug || null;
  } catch (err) {
    if (err instanceof AuthError) redirect("/login");
    first = null;
  }

  if (first) redirect(`/p/${first}`);

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <TopBar user={user} />
      <div className="matte overflow-hidden p-8 sm:p-10">
        <PulseWordmark size="lg" />
        <h1 className="mt-6 font-serif text-4xl italic tracking-tight text-paper sm:text-5xl">
          Welcome to Pulse
        </h1>
        <p className="mt-4 max-w-lg text-sm leading-relaxed text-mist">
          Signed in as <span className="font-mono text-paper">{user.email}</span>. Connecting GitHub
          opens a tab — the Pulse SDK in that repo is what sends tokens, cost, and traces.
        </p>
        <a href="/connect" className="btn-primary mt-8 inline-flex px-5">
          Connect a repo
        </a>
        <div className="mt-10 grid gap-3 sm:grid-cols-3">
          {highlights.map((item) => (
            <div key={item.label} className="matte-sunk p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-mist">{item.label}</div>
              <p className="mt-2 text-sm leading-relaxed text-paper/80">{item.body}</p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
