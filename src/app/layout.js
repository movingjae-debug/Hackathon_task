import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import NavTabs from "@/components/NavTabs";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "널스빌리지 콘텐츠 파이프라인",
  description: "널스빌리지 SNS 콘텐츠 파이프라인 대시보드",
};

export default function RootLayout({ children }) {
  return (
    <html
      lang="ko"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-900">
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto max-w-5xl px-4 py-4 sm:px-6">
            <h1 className="text-lg font-bold">널스빌리지 콘텐츠 파이프라인</h1>
            <p className="mt-0.5 text-sm text-slate-500">
              /generate · /review · /calendar · /strategy 결과물 대시보드
            </p>
          </div>
          <NavTabs />
        </header>
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
          {children}
        </main>
        <footer className="border-t border-slate-200 py-6 text-center text-xs text-slate-400">
          널스빌리지 콘텐츠팀 · 데이터 기준 2026-07-01
        </footer>
      </body>
    </html>
  );
}
