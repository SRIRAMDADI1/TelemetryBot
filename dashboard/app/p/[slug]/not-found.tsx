import Link from "next/link";
import { BrandScreen } from "@/components/Brand";

export default function ProjectNotFound() {
  return (
    <BrandScreen
      title="Project not found"
      actions={
        <>
          <Link href="/" className="btn-primary">
            Back to Pulse
          </Link>
          <Link href="/connect" className="btn">
            Connect a repo
          </Link>
        </>
      }
    >
      <p>
        No monitoring tab matches this URL. It may have been removed, or you signed in as a different
        account.
      </p>
    </BrandScreen>
  );
}
