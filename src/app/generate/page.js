import MarkdownDoc from "@/components/MarkdownDoc";
import { readMarkdown, readSeeds, readGenContent } from "@/lib/content";

export const metadata = { title: "Generate 규격 · 널스빌리지" };

export default function GeneratePage() {
  const source = readMarkdown("generate.md");
  const seeds = readSeeds();
  const genMap = readGenContent();

  return (
    <div className="flex flex-col gap-8">
      <MarkdownDoc source={source} />

      <section className="rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="text-base font-bold">현재 시드 목록 (CSV)</h2>
        <p className="mt-1 text-sm text-slate-500">
          {seeds.length}개 시드 · {Object.keys(genMap).length}개 생성 완료
        </p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="py-2 pr-3 font-medium">ID</th>
                <th className="py-2 pr-3 font-medium">주제</th>
                <th className="py-2 pr-3 font-medium">타깃</th>
                <th className="py-2 pr-3 font-medium">톤</th>
                <th className="py-2 pr-3 font-medium">채널 힌트</th>
                <th className="py-2 pr-3 font-medium">시의성</th>
                <th className="py-2 font-medium">생성 상태</th>
              </tr>
            </thead>
            <tbody>
              {seeds.map((seed) => (
                <tr key={seed.id} className="border-b border-slate-100">
                  <td className="py-2 pr-3 font-mono text-xs text-slate-500">
                    #{seed.id}
                  </td>
                  <td className="py-2 pr-3">{seed.topic}</td>
                  <td className="py-2 pr-3 whitespace-nowrap">{seed.target}</td>
                  <td className="py-2 pr-3 whitespace-nowrap">{seed.tone}</td>
                  <td className="py-2 pr-3 whitespace-nowrap">{seed.platformHint}</td>
                  <td className="py-2 pr-3 whitespace-nowrap text-slate-500">
                    {seed.evergreen ? "Evergreen" : seed.refEvent}
                  </td>
                  <td className="py-2">
                    {genMap[seed.id] ? (
                      <span className="text-emerald-600">생성됨</span>
                    ) : (
                      <span className="text-amber-600">대기</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
