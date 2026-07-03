import fs from "node:fs";
import path from "node:path";

const CONTENT_DIR = path.join(process.cwd(), "content");

export function readMarkdown(filename) {
  return fs.readFileSync(path.join(CONTENT_DIR, filename), "utf-8");
}

function parseCsvLine(line) {
  const cells = [];
  let cur = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (inQuotes) {
      if (c === '"') {
        if (line[i + 1] === '"') {
          cur += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        cur += c;
      }
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ",") {
      cells.push(cur);
      cur = "";
    } else {
      cur += c;
    }
  }
  cells.push(cur);
  return cells;
}

export function readSeeds() {
  const raw = fs.readFileSync(path.join(CONTENT_DIR, "seeds.csv"), "utf-8");
  const lines = raw.split(/\r?\n/).filter((l) => l.trim().length > 0);
  const header = parseCsvLine(lines[0]);
  return lines.slice(1).map((line) => {
    const cells = parseCsvLine(line);
    const row = {};
    header.forEach((h, i) => {
      row[h.trim()] = (cells[i] ?? "").trim();
    });
    return {
      id: row.id.padStart(2, "0"),
      topic: row.topic,
      tone: row.tone,
      target: row.target_audience,
      keywords: row.keywords_required
        ? row.keywords_required.split(",").map((k) => k.trim()).filter(Boolean)
        : [],
      platformHint: row.platform_hint,
      refEvent: row.ref_event,
      evergreen: !row.ref_event,
    };
  });
}

export function readGenContent() {
  const raw = fs.readFileSync(path.join(CONTENT_DIR, "gen.json"), "utf-8");
  const data = JSON.parse(raw);
  const map = {};
  for (const item of data) {
    map[String(item.id).padStart(2, "0")] = item.content;
  }
  return map;
}

const KAKAO_MAX = 200;
const NL_MIN = 550;
const NL_MAX = 650;
const CARD_MIN = 3;
const CARD_MAX = 5;

function validateHard(content) {
  const issues = [];
  const kakaoText = content?.kakao?.text ?? "";
  if (kakaoText.length > KAKAO_MAX) {
    issues.push(`카카오 ${kakaoText.length}자 > 최대 ${KAKAO_MAX}자`);
  }
  const nl = content?.newsletter ?? {};
  const nlLen = (nl.intro ?? "").length + (nl.body ?? "").length + (nl.cta ?? "").length;
  if (nlLen < NL_MIN || nlLen > NL_MAX) {
    issues.push(`뉴스레터 ${nlLen}자 (목표 ${NL_MIN}~${NL_MAX}자)`);
  }
  const slides = content?.card_news?.slides ?? [];
  if (slides.length < CARD_MIN || slides.length > CARD_MAX) {
    issues.push(`카드뉴스 ${slides.length}장 (필요 ${CARD_MIN}~${CARD_MAX}장)`);
  }
  if (slides.length && !slides[slides.length - 1]?.is_cta) {
    issues.push("마지막 카드에 is_cta:true 누락");
  }
  return issues;
}

function trafficLight(content, seed) {
  const hardIssues = validateHard(content);
  const softIssues = [];

  const allText = JSON.stringify(content);
  const matched = seed.keywords.filter((kw) => kw && allText.includes(kw));
  if (seed.keywords.length && matched.length < 2) {
    softIssues.push(`필수 용어 ${matched.length}/${seed.keywords.length}개만 반영`);
  }

  const kakaoLen = (content?.kakao?.text ?? "").length;
  if (kakaoLen >= 180 && kakaoLen <= KAKAO_MAX) {
    softIssues.push(`카카오 ${kakaoLen}자 (링크 추가 시 초과 위험)`);
  }

  if (hardIssues.length) return { status: "red", issues: hardIssues };
  if (softIssues.length) return { status: "yellow", issues: softIssues };
  return { status: "green", issues: [] };
}

export function computeReview() {
  const seeds = readSeeds();
  const genMap = readGenContent();

  return seeds
    .filter((seed) => genMap[seed.id])
    .map((seed) => {
      const content = genMap[seed.id];
      const { status, issues } = trafficLight(content, seed);
      const kakaoText = content?.kakao?.text ?? "";
      const kakaoPreview =
        kakaoText.slice(0, 26).replace(/\n/g, " ") + (kakaoText.length > 26 ? "…" : "");

      return {
        id: seed.id,
        topic: seed.topic,
        target: seed.target,
        tone: seed.tone,
        refEvent: seed.evergreen ? "Evergreen" : seed.refEvent,
        status,
        issues,
        kakaoPreview,
      };
    })
    .sort((a, b) => a.id.localeCompare(b.id));
}
