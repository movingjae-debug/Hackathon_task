import MarkdownDoc from "@/components/MarkdownDoc";
import { readMarkdown } from "@/lib/content";

export const metadata = { title: "발행 캘린더 · 널스빌리지" };

export default function CalendarPage() {
  const source = readMarkdown("content_calendar.md");
  return <MarkdownDoc source={source} />;
}
