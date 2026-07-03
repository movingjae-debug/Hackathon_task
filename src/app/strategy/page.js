import MarkdownDoc from "@/components/MarkdownDoc";
import { readMarkdown } from "@/lib/content";

export const metadata = { title: "발행 전략안 · 널스빌리지" };

export default function StrategyPage() {
  const source = readMarkdown("strategy_proposals.md");
  return <MarkdownDoc source={source} />;
}
