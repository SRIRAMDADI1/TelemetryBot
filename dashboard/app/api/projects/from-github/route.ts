import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { API_BASE, SESSION_COOKIE } from "@/lib/api";

export async function POST(request: Request) {
  const jar = await cookies();
  const token = jar.get(SESSION_COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ error: "Not signed in" }, { status: 401 });
  }
  const body = await request.json().catch(() => ({}));
  const res = await fetch(`${API_BASE}/v1/projects/from-github`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    return NextResponse.json(
      { error: typeof data.detail === "string" ? data.detail : "Import failed", detail: data.detail },
      { status: res.status }
    );
  }
  return NextResponse.json(data);
}
