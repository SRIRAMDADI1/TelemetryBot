import Link from "next/link";
import { BrandScreen } from "@/components/Brand";

export default function NotFound() {
  return (
    <BrandScreen
      title="Not found"
      actions={
        <Link href="/" className="btn-primary">
          Back to Pulse
        </Link>
      }
    >
      <p>That project or page doesn’t exist, or you don’t have access to it.</p>
    </BrandScreen>
  );
}
