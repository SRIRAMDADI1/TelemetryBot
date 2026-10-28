import Link from "next/link";
import { redirect } from "next/navigation";
import { ConnectReposClient } from "@/components/ConnectReposClient";
import { TopBar } from "@/components/Shell";
import { AuthError, fetchProviders } from "@/lib/api";
import { fetchGitHubRepos, fetchMe, fetchProjects } from "@/lib/server-api";

export const dynamic = "force-dynamic";

export default async function ConnectPage({
  searchParams,
}: {
  searchParams?: { error?: string };
}) {
  let user;
  try {
    user = await fetchMe();
  } catch {
    redirect("/login");
  }
  if (!user) redirect("/login");

  let projects = [];
  try {
    projects = await fetchProjects();
  } catch (err) {
    if (err instanceof AuthError) redirect("/login");
    throw err;
  }

  let githubReal = false;
  try {
    const providers = await fetchProviders();
    githubReal = providers.github_real;
  } catch {
    githubReal = false;
  }

  let repos: Awaited<ReturnType<typeof fetchGitHubRepos>>["repos"] = [];
  let reposError: string | null = searchParams?.error || null;
  if (user.github_connected) {
    try {
      const data = await fetchGitHubRepos();
      repos = data.repos;
    } catch (err) {
      reposError = err instanceof Error ? err.message : "Failed to load repos";
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <TopBar
        user={user}
        trailing={
          <Link href="/" className="btn">
            Dashboard
          </Link>
        }
      />
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-paper sm:text-3xl">Connect a repo</h1>
        <p className="mt-1 text-sm text-mist">
          Pick a GitHub repository to open a Pulse tab. Wiring the SDK happens in that repo afterward.
        </p>
      </div>
      <ConnectReposClient
        user={user}
        projects={projects}
        initialRepos={repos}
        reposError={reposError}
        githubReal={githubReal}
      />
    </main>
  );
}
