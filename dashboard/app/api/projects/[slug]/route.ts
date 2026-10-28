import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { API_BASE, SESSION_COOKIE } from "@/lib/api";

export async function DELETE(
  _request: Request,
  { params }: { params: { slug: string } }
) {
  const jar = await cookies();
  const token = jar.get(SESSION_COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ error: "Not signed in" }, { status: 401 });
  }

  const slug = params.slug;
  const res = await fetch(`${API_BASE}/v1/projects/${encodeURIComponent(slug)}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    return NextResponse.json(
      {
        error:
          typeof data.detail === "string"
            ? data.detail
            : "Could not disconnect project",
        detail: data.detail,
      },
      { status: res.status }
    );
  }
  return NextResponse.json(data);
}
