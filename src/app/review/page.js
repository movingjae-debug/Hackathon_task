import ReviewTable from "@/components/ReviewTable";
import { computeReview } from "@/lib/content";

export const metadata = { title: "검토 카드 · 널스빌리지" };

export default function ReviewPage() {
  const rows = computeReview();
  return <ReviewTable rows={rows} />;
}
