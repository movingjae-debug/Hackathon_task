function SeedCard({ seed, content }) {
  const slides = content?.card_news?.slides ?? [];
  const kakaoText = content?.kakao?.text ?? "";
  const nl = content?.newsletter ?? {};
  const nlLen = (nl.intro?.length ?? 0) + (nl.body?.length ?? 0) + (nl.cta?.length ?? 0);

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-6">
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-slate-100 pb-3">
        <h3 className="text-base font-bold">
          <span className="mr-2 font-mono text-xs text-slate-400">#{seed.id}</span>
          {seed.topic}
        </h3>
        <span className="text-xs text-slate-500">
          {seed.target} · {seed.tone} ·{" "}
          {seed.evergreen ? "Evergreen" : seed.refEvent}
        </span>
      </header>

      <div className="mt-4 grid gap-6 lg:grid-cols-3">
        <div>
          <h4 className="text-sm font-semibold text-slate-700">
            🎴 카드뉴스 ({slides.length}장)
          </h4>
          <ol className="mt-2 flex flex-col gap-3">
            {slides.map((slide, i) => (
              <li
                key={i}
                className={`rounded-md border p-3 text-sm ${
                  slide.is_cta
                    ? "border-emerald-300 bg-emerald-50"
                    : "border-slate-200"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400">
                    {i + 1}장
                  </span>
                  {slide.is_cta && (
                    <span className="rounded bg-emerald-600 px-1.5 py-0.5 text-[10px] font-bold text-white">
                      CTA
                    </span>
                  )}
                </div>
                <p className="mt-1 font-medium">{slide.headline}</p>
                <p className="mt-1 text-slate-600">{slide.body}</p>
              </li>
            ))}
          </ol>
        </div>

        <div>
          <h4 className="text-sm font-semibold text-slate-700">
            💬 카카오메시지 ({kakaoText.length}자)
          </h4>
          <div className="mt-2 whitespace-pre-line rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
            {kakaoText}
          </div>
        </div>

        <div>
          <h4 className="text-sm font-semibold text-slate-700">
            📰 뉴스레터 ({nlLen}자)
          </h4>
          <div className="mt-2 flex flex-col gap-2 text-sm">
            <p>
              <span className="font-semibold text-slate-500">[도입] </span>
              {nl.intro}
            </p>
            <p>
              <span className="font-semibold text-slate-500">[본문] </span>
              {nl.body}
            </p>
            <p>
              <span className="font-semibold text-slate-500">[CTA] </span>
              {nl.cta}
            </p>
          </div>
        </div>
      </div>
    </article>
  );
}

export default function GenerateResults({ seeds, genMap }) {
  const items = seeds
    .filter((seed) => genMap[seed.id])
    .map((seed) => ({ seed, content: genMap[seed.id] }));

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="text-base font-bold">생성된 콘텐츠 3종 세트</h2>
        <p className="mt-1 text-sm text-slate-500">
          {items.length}개 시드 · 카드뉴스 · 카카오 · 뉴스레터 자동 생성 결과
        </p>
      </section>

      {items.map(({ seed, content }) => (
        <SeedCard key={seed.id} seed={seed} content={content} />
      ))}
    </div>
  );
}
