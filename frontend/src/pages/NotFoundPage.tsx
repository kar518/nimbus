import { Link } from "react-router-dom";
import { Empty } from "@/components/common/UI";
export function NotFoundPage() {
  return (
    <section className="panel">
      <Empty title="This page wandered off" description="The address does not match a Nimbus page.">
        <Link className="button primary" to="/">
          Back to overview
        </Link>
      </Empty>
    </section>
  );
}
