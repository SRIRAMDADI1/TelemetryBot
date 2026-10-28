import { redirect } from "next/navigation";
import { AuthError, type User } from "@/lib/api";
import { fetchMe } from "@/lib/server-api";

/** Load the signed-in user or send them to /login. Network errors propagate. */
export async function requireDashboardUser(): Promise<User> {
  const user = await fetchMe();
  if (!user) redirect("/login");
  return user;
}

export function handleAuthError(err: unknown): never {
  if (err instanceof AuthError) redirect("/login");
  throw err;
}

/** Run a data loader; expired sessions go to login, other errors bubble to error.tsx. */
export async function withAuth<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (err) {
    handleAuthError(err);
  }
}
