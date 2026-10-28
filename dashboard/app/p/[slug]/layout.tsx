import type { ReactNode } from "react";
import { ProjectShell } from "@/components/ProjectShell";
import { requireDashboardUser, withAuth } from "@/lib/auth";
import { fetchProject, fetchProjects } from "@/lib/server-api";

export default async function ProjectLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: { slug: string };
}) {
  const user = await requireDashboardUser();
  const { projects, project } = await withAuth(async () => {
    const [projects, project] = await Promise.all([fetchProjects(), fetchProject(params.slug)]);
    return { projects, project };
  });

  return (
    <ProjectShell projects={projects} slug={params.slug} projectName={project.name} user={user}>
      {children}
    </ProjectShell>
  );
}
