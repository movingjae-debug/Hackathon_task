"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/guide", label: "스킬 사용법" },
  { href: "/generate", label: "Generate 규격" },
  { href: "/review", label: "검토 카드" },
  { href: "/calendar", label: "발행 캘린더" },
  { href: "/strategy", label: "전략안" },
];

export default function NavTabs() {
  const pathname = usePathname();

  return (
    <nav className="mx-auto max-w-5xl overflow-x-auto px-4 sm:px-6">
      <ul className="flex gap-1 text-sm">
        {TABS.map((tab) => {
          const active = pathname.startsWith(tab.href);
          return (
            <li key={tab.href}>
              <Link
                href={tab.href}
                className={`inline-block whitespace-nowrap border-b-2 px-3 py-2.5 font-medium transition-colors ${
                  active
                    ? "border-emerald-600 text-emerald-700"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                }`}
              >
                {tab.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
