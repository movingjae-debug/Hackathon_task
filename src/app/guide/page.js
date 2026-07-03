import MarkdownDoc from "@/components/MarkdownDoc";
import { readMarkdown } from "@/lib/content";

export const metadata = { title: "스킬 사용법 · 널스빌리지" };

export default function GuidePage() {
  const source = readMarkdown("skill_guide.md");
  return <MarkdownDoc source={source} />;
}
