import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MarkdownDoc({ source }) {
  return (
    <article className="prose prose-slate max-w-none rounded-lg border border-slate-200 bg-white p-6 prose-headings:font-bold prose-table:text-sm prose-th:bg-slate-100">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{source}</ReactMarkdown>
    </article>
  );
}
