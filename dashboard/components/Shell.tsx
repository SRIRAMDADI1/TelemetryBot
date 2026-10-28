import Link from "next/link";
import { PulseWordmark } from "@/components/Brand";
import { RefreshButton } from "@/components/RefreshButton";
import { UserMenu } from "@/components/UserMenu";
import type { Project, User } from "@/lib/api";

export function TopBar({
  user,
  trailing,
}: {
  user?: User | null;
  trailing?: React.ReactNode;
}) {
  return (
    <header className="mb-8 flex flex-wrap items-center justify-between gap-4 border-b border-line/80 pb-5">
      <Link href="/" className="inline-flex w-fit !text-paper hover:!text-paper">
        <PulseWordmark />
      </Link>
      <div className="flex items-center gap-2">
        {trailing}
        {user ? <UserMenu user={user} /> : null}
      </div>
    </header>
  );
}

export function PageFrame({
  projects,
  slug,
  section = "",
  title,
  subtitle,
  user,
  children,
}: {
  projects: Project[];
  slug: string;
  section?: string;
  title: string;
  subtitle?: string;
  user?: User | null;
  children: React.ReactNode;
}) {
  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <TopBar user={user} trailing={<RefreshButton />} />

      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-paper sm:text-3xl">{title}</h1>
        {subtitle ? <p className="mt-1 font-mono text-sm text-mist">{subtitle}</p> : null}
      </div>

      <ProjectTabs projects={projects} activeSlug={slug} section={section} />
      <SectionNav slug={slug} section={section} />

      {children}
    </main>
  );
}

export function ProjectTabs({
  projects,
  activeSlug,
  section = "",
}: {
  projects: Project[];
  activeSlug: string;
  section?: string;
}) {
  const suffix = section ? `/${section}` : "";
  return (
    <div className="flex items-end gap-1 overflow-x-auto border-b border-line">
      {projects.map((p) => {
        const active = p.slug === activeSlug;
        return (
          <Link
            key={p.id}
            href={`/p/${p.slug}${suffix}`}
            aria-current={active ? "page" : undefined}
            className={
              active
                ? "matte -mb-px whitespace-nowrap rounded-b-none border-b-0 px-4 py-2 text-sm font-semibold !text-paper shadow-none hover:!text-paper"
                : "whitespace-nowrap rounded-t-lg px-4 py-2 text-sm !text-mist transition-colors hover:bg-white/[0.04] hover:!text-paper"
            }
          >
            {p.name}
          </Link>
        );
      })}
      <Link
        href="/connect"
        className="ml-2 whitespace-nowrap rounded-t-lg border border-dashed border-line px-3 py-2 text-sm !text-mist transition-colors hover:border-mist/50 hover:!text-paper"
      >
        + Connect
      </Link>
    </div>
  );
}

export function SectionNav({
  slug,
  section,
  onSelect,
}: {
  slug: string;
  section: string;
  onSelect?: (id: string) => void;
}) {
  const items = [
    { id: "", label: "Overview" },
    { id: "runs", label: "Runs" },
    { id: "agents", label: "Agents" },
    { id: "efficiency", label: "Efficiency" },
    { id: "settings", label: "Settings" },
  ];
  return (
    <nav className="matte-sunk mt-5 inline-flex flex-wrap gap-1 p-1">
      {items.map((item) => {
        const href = item.id ? `/p/${slug}/${item.id}` : `/p/${slug}`;
        const active = section === item.id;
        return (
          <a
            key={item.id || "overview"}
            href={href}
            aria-current={active ? "page" : undefined}
            onClick={(event) => {
              if (!onSelect) return;
              if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) {
                return;
              }
              event.preventDefault();
              onSelect(item.id);
            }}
            className={
              active
                ? "rounded-md border border-line bg-white/[0.09] px-3 py-1.5 text-sm font-medium !text-paper shadow-matte hover:!text-paper"
                : "rounded-md border border-transparent px-3 py-1.5 text-sm !text-mist transition-colors hover:bg-white/[0.04] hover:!text-paper"
            }
          >
            {item.label}
          </a>
        );
      })}
    </nav>
  );
}

export function Panel({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`matte p-4 ${className}`}>
      {title ? <h2 className="mb-3 text-sm font-medium tracking-wide text-mist">{title}</h2> : null}
      {children}
    </div>
  );
}

export function StatCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="matte matte-hover p-4">
      <div className="text-[11px] uppercase tracking-[0.18em] text-mist">{label}</div>
      <div className="mt-2 font-mono text-2xl font-semibold tracking-tight text-paper">{value}</div>
      {hint ? <div className="mt-1 text-xs text-mist">{hint}</div> : null}
    </div>
  );
}

export function DataTable({ headers, children }: { headers: string[]; children: React.ReactNode }) {
  return (
    <div className="matte overflow-x-auto p-0">
      <table className="min-w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line bg-white/[0.03]">
            {headers.map((h) => (
              <th key={h} className="px-3 py-2.5 text-[11px] font-medium uppercase tracking-[0.12em] text-mist">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="matte-sunk mt-8 border-dashed p-10 text-center">
      <h2 className="text-lg font-semibold text-paper">{title}</h2>
      <p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed text-mist">{body}</p>
    </div>
  );
}
