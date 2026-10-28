import { notFound } from "next/navigation";
import { ProjectWorkspace } from "@/components/ProjectWorkspace";
import { withAuth } from "@/lib/auth";
import { fetchProjectBundle } from "@/lib/server-api";

const SECTIONS = new Set(["", "runs", "agents", "efficiency", "settings"]);

export default async function ProjectWorkspacePage({
  params,
}: {
  params: { slug: string; tab?: string[] };
}) {
  const tab = params.tab || [];
  if (tab.length > 1) notFound();
  const section = tab[0] || "";
  if (!SECTIONS.has(section)) notFound();

  const bundle = await withAuth(() => fetchProjectBundle(params.slug));
  return <ProjectWorkspace {...bundle} />;
}
