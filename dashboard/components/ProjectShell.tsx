"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { RefreshButton } from "@/components/RefreshButton";
import { ProjectTabs, SectionNav, TopBar } from "@/components/Shell";
import type { Project, User } from "@/lib/api";

const TITLES: Record<string, string> = {
  "": "Overview",
  runs: "Runs",
  agents: "Agents",
  efficiency: "Efficiency",
  settings: "Settings",
};

type ProjectNav = {
  slug: string;
  section: string;
  setSection: (id: string) => void;
};

const ProjectNavContext = createContext<ProjectNav | null>(null);

export function useProjectNav(): ProjectNav {
  const ctx = useContext(ProjectNavContext);
  if (!ctx) throw new Error("useProjectNav must be used inside ProjectShell");
  return ctx;
}

export function parseSection(pathname: string, slug: string): { section: string; title: string; runDetail: boolean } {
  const prefix = `/p/${slug}`;
  if (pathname === prefix || pathname === `${prefix}/`) return { section: "", title: TITLES[""], runDetail: false };
  const rest = pathname.slice(prefix.length).replace(/^\//, "");
  const [head, nested] = rest.split("/");
  if (head === "runs" && nested) return { section: "runs", title: "Run detail", runDetail: true };
  return { section: head || "", title: TITLES[head] || head, runDetail: false };
}

function sectionHref(slug: string, id: string) {
  return id ? `/p/${slug}/${id}` : `/p/${slug}`;
}

const SECTION_IDS = new Set(["", "runs", "agents", "efficiency", "settings"]);

function hashSection(): string | null {
  if (typeof window === "undefined") return null;
  const hash = window.location.hash.replace(/^#/, "");
  if (!hash) return null;
  return SECTION_IDS.has(hash) ? hash : null;
}

export function ProjectShell({
  projects,
  slug,
  projectName,
  user,
  children,
}: {
  projects: Project[];
  slug: string;
  projectName: string;
  user: User;
  children: ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname() || "";
  const parsed = parseSection(pathname, slug);
  const [section, setSectionState] = useState(parsed.section);

  useEffect(() => {
    const fromHash = hashSection();
    setSectionState(fromHash ?? parsed.section);
  }, [parsed.section, pathname]);

  useEffect(() => {
    function onPop() {
      const fromHash = hashSection();
      setSectionState(fromHash ?? parseSection(window.location.pathname, slug).section);
    }
    window.addEventListener("popstate", onPop);
    window.addEventListener("hashchange", onPop);
    return () => {
      window.removeEventListener("popstate", onPop);
      window.removeEventListener("hashchange", onPop);
    };
  }, [slug]);

  const setSection = useCallback(
    (id: string) => {
      const onRunDetail = parseSection(window.location.pathname, slug).runDetail;
      if (onRunDetail) {
        router.push(sectionHref(slug, id));
        return;
      }
      setSectionState(id);
      // Same pathname, hash only — Next.js 14 treats a path change as a
      // navigation and would refetch. Hash updates do not.
      const next = `${window.location.pathname}${id ? `#${id}` : ""}`;
      window.history.pushState({ section: id }, "", next);
    },
    [router, slug],
  );

  const nav = useMemo(() => ({ slug, section, setSection }), [slug, section, setSection]);
  const title = parsed.runDetail ? "Run detail" : TITLES[section] || section || "Overview";

  return (
    <ProjectNavContext.Provider value={nav}>
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <TopBar user={user} trailing={<RefreshButton />} />
        <div className="mb-6">
          <h1 className="text-2xl font-semibold tracking-tight text-paper sm:text-3xl">{title}</h1>
          <p className="mt-1 font-mono text-sm text-mist">{projectName}</p>
        </div>
        <ProjectTabs projects={projects} activeSlug={slug} section={section} />
        <SectionNav slug={slug} section={section} onSelect={setSection} />
        {children}
      </main>
    </ProjectNavContext.Provider>
  );
}
