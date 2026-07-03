import GenerateResults from "@/components/GenerateResults";
import { readSeeds, readGenContent } from "@/lib/content";

export const metadata = { title: "생성 결과 · 널스빌리지" };

export default function GeneratePage() {
  const seeds = readSeeds();
  const genMap = readGenContent();
  return <GenerateResults seeds={seeds} genMap={genMap} />;
}
