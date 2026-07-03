"use client";

import { useMemo, useState } from "react";

const STATUS_META = {
  green: { icon: "🟢", label: "통과" },
  yellow: { icon: "🟡", label: "확인" },
  red: { icon: "🔴", label: "수정" },
};

const FILTERS = [
  { key: "all", label: "전체" },
  { key: "green", label: "🟢 통과" },
  { key: "yellow", label: "🟡 확인" },
  { key: "red", label: "🔴 수정" },
];

export default function ReviewTable({ rows }) {
  const [filter, setFilter] = useState("all");

  const counts = useMemo(() => {
    const c = { green: 0, yellow: 0, red: 0 };
    for (const row of rows) c[row.status]++;
    return c;
  }, [rows]);

  const filtered = filter === "all" ? rows : rows.filter((r) => r.status === filter);

  return (
    <section className="flex flex-col gap-4">
      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="text-base font-bold">콘텐츠 검토 카드</h2>
        <p className="mt-1 text-sm text-slate-500">
          gen.json + seeds.csv 데이터를 기준으로 규격(카카오 200자·뉴스레터
          550~650자·카드뉴스 3~5장)을 실시간으로 검증합니다.
        </p>

        <div className="mt-4 flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`rounded-full border px-3 py-1.5 text-sm font-medium transition-colors ${
                filter === f.key
                  ? "border-emerald-600 bg-emerald-50 text-emerald-700"
                  : "border-slate-200 text-slate-600 hover:bg-slate-50"
              }`}
            >
              {f.label}
              {f.key !== "all" && (
                <span className="ml-1 text-slate-400">({counts[f.key]})</span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-left text-slate-500">
              <th className="px-4 py-2.5 font-medium">상태</th>
              <th className="px-4 py-2.5 font-medium">ID</th>
              <th className="px-4 py-2.5 font-medium">주제</th>
              <th className="px-4 py-2.5 font-medium">타깃 / 톤</th>
              <th className="px-4 py-2.5 font-medium">카카오 미리보기</th>
              <th className="px-4 py-2.5 font-medium">확인 사항</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((row) => (
              <tr key={row.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-3 text-lg">{STATUS_META[row.status].icon}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-500">#{row.id}</td>
                <td className="px-4 py-3">{row.topic}</td>
                <td className="px-4 py-3 whitespace-nowrap text-slate-500">
                  {row.target} · {row.tone}
                </td>
                <td className="px-4 py-3 text-slate-600">&ldquo;{row.kakaoPreview}&rdquo;</td>
                <td className="px-4 py-3">
                  {row.issues.length ? (
                    <ul className="list-inside list-disc text-amber-700">
                      {row.issues.map((issue, i) => (
                        <li key={i}>{issue}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-slate-400">—</span>
                  )}
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                  해당 상태의 시드가 없습니다.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
