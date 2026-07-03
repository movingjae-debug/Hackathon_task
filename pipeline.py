#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
널스빌리지 SNS 콘텐츠 자동 생성 파이프라인
=========================================
Input : data/nursevillage_content_seeds.csv
Output: output/output_content_set.md

실행 예시
  python pipeline.py                        # 전체 시드 (claude CLI 모드)
  python pipeline.py --id 01,03,07          # 특정 시드만
  python pipeline.py --dry-run              # 프롬프트 확인만 (API 호출 없음)
  python pipeline.py --sdk                  # Anthropic SDK (ANTHROPIC_API_KEY 필요)
  python pipeline.py --from-json gen.json   # 사전 생성된 JSON 파일 로드 (Claude Code 직접 생성 모드)
  python pipeline.py --validate-only        # 기존 output_content_set.md 글자수 검증만
  python pipeline.py --export-prompts       # 프롬프트만 JSON으로 내보내기 (gen.json 생성용)
"""

import csv
import os
import sys
import json
import subprocess
import re
import argparse
import io
from pathlib import Path
from datetime import date

# 콘솔 UTF-8 출력 강제
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


# ── 경로 설정 ────────────────────────────────────────────────
def _base_dir() -> Path:
    """Unicode 경로 환경에서 스크립트 디렉터리를 안전하게 탐색"""
    try:
        candidate = Path(__file__).resolve().parent
        if candidate.exists():
            return candidate
    except Exception:
        pass
    try:
        return Path(sys.argv[0]).resolve().parent
    except Exception:
        return Path.cwd()

BASE_DIR   = _base_dir()
CSV_PATH   = BASE_DIR / "data" / "nursevillage_content_seeds.csv"
OUT_PATH   = BASE_DIR / "output" / "output_content_set.md"
DEC_PATH   = BASE_DIR / "decisions.md"
GEN_JSON   = BASE_DIR / "output" / "gen.json"

# ── 검증 기준 ────────────────────────────────────────────────
KAKAO_MAX        = 200
NL_MIN, NL_MAX   = 550, 650
CARD_MIN, CARD_MAX = 3, 5

# ── 결측 키워드 보완 ──────────────────────────────────────────
MISSING_KEYWORDS: dict[str, str] = {
    "12": "국시,합격,RN,나이팅게일 선서,번아웃",
}

# ── 현장 용어 사전 ─────────────────────────────────────────────
NURSING_TERMS = [
    "프리셉터", "태움", "라운딩", "인계", "바이탈", "듀티표",
    "나이트", "번아웃", "콜벨", "5R", "SBAR", "OCS", "EMR",
    "RN", "LPN", "신규RN", "경력RN", "간호학생", "국시", "실습",
    "나이팅게일 선서", "3교대", "재취업", "이직", "인력기준",
    "간호법", "업무범위", "처우개선", "투약오류", "아차사고",
    "면허", "수간호사", "간호부", "임상", "병동",
]

# ── 시스템 프롬프트 ────────────────────────────────────────────
SYSTEM_PROMPT = """당신은 간호사·간호학생 커리어 플랫폼 '널스빌리지'의 콘텐츠 마케터입니다.
임상 현장 용어(태움, 인계, 프리셉터, SBAR, 듀티표, 라운딩 등)를 자연스럽게 구사합니다.

출력 규칙:
1. 반드시 JSON 형식만 출력하세요 - 앞뒤에 다른 텍스트·마크다운 없이 { } 로만 감싸세요.
2. kakao.text 는 공백 포함 200자 이하입니다.
3. newsletter.intro + body + cta 합계는 공백 포함 550~650자입니다.
4. card_news.slides 는 3~5개이며 마지막 슬라이드에만 is_cta: true 를 설정하세요.
5. 모든 문장은 한국어로 작성하세요.
"""


# ══════════════════════════════════════════════════════════════
# 1. 데이터 로드 & 정제
# ══════════════════════════════════════════════════════════════

def load_seeds(csv_path: Path) -> list[dict]:
    """CSV 읽기 + 결측 키워드 보완 + Evergreen 플래그"""
    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV 없음: {csv_path}\n"
            f"data/ 폴더에 nursevillage_content_seeds.csv 를 넣어주세요."
        )
    seeds = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid     = row["id"].strip().zfill(2)
            raw_kw  = row["keywords_required"].strip()
            decision_note = ""
            if not raw_kw:
                raw_kw = MISSING_KEYWORDS.get(sid, "")
                if raw_kw:
                    decision_note = (
                        f"ID {sid} keywords_required 결측 → "
                        f"동일 타깃·ref_event 앵커로 역산: {raw_kw}"
                    )
            ref = row.get("ref_event", "").strip()
            seeds.append({
                "id":           sid,
                "topic":        row["topic"].strip(),
                "tone":         row["tone"].strip(),
                "target":       row["target_audience"].strip(),
                "keywords":     [k.strip() for k in raw_kw.split(",") if k.strip()],
                "platform_hint":row.get("platform_hint", "").strip(),
                "ref_event":    ref,
                "evergreen":    not bool(ref),
                "_decision":    decision_note,
            })
    return seeds


# ══════════════════════════════════════════════════════════════
# 2. 프롬프트 생성
# ══════════════════════════════════════════════════════════════

TONE_GUIDES = {
    "공감형": "따뜻하고 감정을 공유하는 어조. 독자의 경험에 공감하며 시작하세요.",
    "정보형": "명확하고 실용적인 어조. 단계·수치·체크리스트를 적극 활용하세요.",
    "유머형": "가볍고 유쾌한 어조. 웃픈 상황·밈감 표현·이모지를 활용하세요.",
}
TARGET_GUIDES = {
    "신규RN":  "임상 1년차 이하 간호사. 프리셉터, 투약 오류, 3교대 적응 관심.",
    "간호학생": "간호학과 재학생·국시 준비생. 실습·국시·RN/LPN 이해 관심.",
    "경력RN":  "임상 경력 5년+ 간호사. 번아웃·이직·간호법·후배 지도 관심.",
}
SUBTITLE_MAP = {
    "11": "부제: '처음 병동 가서 얼어붙은 그 순간들' - 간호학생 현재 시점으로 작성.",
    "17": "부제: '10년 선배가 돌아본 나의 흑역사' - 경력RN 회고 과거 시점으로 작성.",
}

def build_user_prompt(seed: dict) -> str:
    evergreen_note = (
        "⚠️ ref_event 없음 - Evergreen 콘텐츠. 날짜/시기 한정 표현 금지, CTA는 구독·저장 유도."
        if seed["evergreen"]
        else f"ref_event '{seed['ref_event']}' 를 콘텐츠에 자연스럽게 반영하세요."
    )
    subtitle = SUBTITLE_MAP.get(seed["id"], "")
    return f"""주제: {seed["topic"]}
타깃: {seed["target"]} - {TARGET_GUIDES.get(seed["target"], "")}
톤: {seed["tone"]} - {TONE_GUIDES.get(seed["tone"], "")}
필수 키워드 (자연스럽게 반드시 포함): {", ".join(seed["keywords"])}
{evergreen_note}
{subtitle}

아래 JSON 구조로만 응답하세요 (앞뒤 설명 없이 JSON만):

{{
  "card_news": {{
    "slides": [
      {{"headline": "1장 헤드라인", "body": "본문 2~3문장", "is_cta": false}},
      {{"headline": "2장 헤드라인", "body": "본문 2~3문장", "is_cta": false}},
      {{"headline": "마지막 장 헤드라인", "body": "CTA 포함 2~3문장 ▶ 널스빌리지 링크 유도", "is_cta": true}}
    ]
  }},
  "kakao": {{
    "text": "200자 이내. 핵심 한 줄 + 링크 유도. ▶ [널스빌리지] 포함"
  }},
  "newsletter": {{
    "intro": "도입 1~2문장",
    "body": "본문 4~6문장. 현장 용어 자연스럽게 포함.",
    "cta": "CTA 1~2문장. 널스빌리지 구독 유도."
  }}
}}"""


# ══════════════════════════════════════════════════════════════
# 3. Claude 호출 (CLI / SDK)
# ══════════════════════════════════════════════════════════════

def _extract_json(raw: str) -> dict:
    """응답에서 JSON 블록 추출·파싱"""
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise ValueError(f"JSON을 찾을 수 없음. 응답: {raw[:300]}")
    return json.loads(m.group())


def call_claude_cli(prompt: str, system: str) -> str:
    """claude CLI 서브프로세스 호출 (비대화형)"""
    full = f"[SYSTEM]\n{system}\n\n[USER]\n{prompt}"
    cmds = [
        ["claude", "--print", "-p", full],
        ["claude", "-p", full],
    ]
    for cmd in cmds:
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True,
                encoding="utf-8", timeout=180,
            )
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    raise RuntimeError(
        "claude CLI 호출 실패.\n"
        "해결책 A: --sdk 옵션으로 Anthropic SDK 사용 (ANTHROPIC_API_KEY 필요)\n"
        "해결책 B: --from-json 옵션으로 사전 생성 JSON 로드\n"
        "해결책 C: --export-prompts 로 프롬프트 추출 후 Claude Code 대화에서 직접 생성"
    )


def call_anthropic_sdk(prompt: str, system: str) -> str:
    """Anthropic Python SDK 사용"""
    try:
        import anthropic
    except ImportError:
        raise ImportError("pip install anthropic 을 먼저 실행하세요.")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY 환경변수가 없습니다.")
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def generate_content(seed: dict, use_sdk: bool = False) -> dict:
    prompt = build_user_prompt(seed)
    raw = call_anthropic_sdk(prompt, SYSTEM_PROMPT) if use_sdk else call_claude_cli(prompt, SYSTEM_PROMPT)
    return _extract_json(raw)


# ══════════════════════════════════════════════════════════════
# 4. 글자수 검증
# ══════════════════════════════════════════════════════════════

def count_chars(text: str) -> int:
    return len(text)


def validate_content(content: dict) -> list[str]:
    """규격 위반 항목 반환 (빈 리스트 = 통과)"""
    issues = []

    kakao_text = content.get("kakao", {}).get("text", "")
    kn = count_chars(kakao_text)
    if kn > KAKAO_MAX:
        issues.append(f"카카오 {kn}자 > 최대 {KAKAO_MAX}자")

    nl = content.get("newsletter", {})
    nl_text = nl.get("intro", "") + nl.get("body", "") + nl.get("cta", "")
    nn = count_chars(nl_text)
    if not (NL_MIN <= nn <= NL_MAX):
        issues.append(f"뉴스레터 {nn}자 (목표 {NL_MIN}~{NL_MAX}자)")

    slides = content.get("card_news", {}).get("slides", [])
    ns = len(slides)
    if not (CARD_MIN <= ns <= CARD_MAX):
        issues.append(f"카드뉴스 {ns}장 (필요 {CARD_MIN}~{CARD_MAX}장)")
    if slides and not slides[-1].get("is_cta"):
        issues.append("마지막 카드에 is_cta:true 누락")

    return issues


# ══════════════════════════════════════════════════════════════
# 5. 현장 용어 태그 추출
# ══════════════════════════════════════════════════════════════

def extract_terms(content: dict, seed_keywords: list[str]) -> list[str]:
    all_text = json.dumps(content, ensure_ascii=False)
    found = set()
    for term in NURSING_TERMS:
        if term in all_text:
            found.add(term)
    for kw in seed_keywords:
        if kw:
            found.add(kw)
    return sorted(found)


# ══════════════════════════════════════════════════════════════
# 6. 마크다운 포맷
# ══════════════════════════════════════════════════════════════

def format_seed_md(seed: dict, content: dict, terms: list[str], issues: list[str]) -> str:
    lines: list[str] = []
    heading = f"### 시드 #{seed['id']}: {seed['topic']}"
    lines.append(heading)
    ref_label = "Evergreen" if seed["evergreen"] else seed["ref_event"]
    lines.append(f"**타깃**: {seed['target']} | **톤**: {seed['tone']} | **시의성**: {ref_label}")

    if issues:
        lines.append(f"\n> ⚠️ 검증 경고: {' | '.join(issues)}")
    lines.append("")

    # 카드뉴스
    slides = content.get("card_news", {}).get("slides", [])
    lines.append(f"#### 🎴 카드뉴스 ({len(slides)}장)")
    for i, slide in enumerate(slides, 1):
        cta = " (CTA)" if slide.get("is_cta") else ""
        lines.append(f"\n**{i}장{cta}: {slide.get('headline','')}**")
        lines.append(slide.get("body", ""))
    lines.append("")

    # 카카오메시지
    kakao_text = content.get("kakao", {}).get("text", "")
    kn = count_chars(kakao_text)
    lines.append(f"#### 💬 카카오메시지 ({kn}자)")
    lines.append("```")
    lines.append(kakao_text)
    lines.append("```")
    lines.append("")

    # 뉴스레터
    nl = content.get("newsletter", {})
    intro, body, cta = nl.get("intro", ""), nl.get("body", ""), nl.get("cta", "")
    nn = count_chars(intro + body + cta)
    lines.append(f"#### 📰 뉴스레터 ({nn}자)")
    lines.append(f"**[도입]** {intro}")
    lines.append(f"\n**[본문]** {body}")
    lines.append(f"\n**[CTA]** {cta}")
    lines.append("")

    # 용어 태그
    lines.append("#### 🏷️ 사용된 현장 용어")
    lines.append(" ".join(f"#{t}" for t in terms))
    lines.append("")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# 7. 기존 MD 검증 (--validate-only)
# ══════════════════════════════════════════════════════════════

def validate_existing_md(md_path: Path) -> dict:
    """output_content_set.md 파싱 글자수 검증 → 결과 딕셔너리 반환"""
    text = md_path.read_text(encoding="utf-8")
    blocks = re.split(r"\n---\n", text)

    kakao_re  = re.compile(r"(?:💬 )?카카오메시지 \((\d+)자\)")
    nl_re     = re.compile(r"(?:📰 )?뉴스레터 \((?:약 )?(\d+)자\)")
    card_re   = re.compile(r"(?:🎴 )?카드뉴스 \((\d+)장\)")
    sid_re    = re.compile(r"시드 #(\d+):")

    report = {"total": 0, "ok": 0, "warn": 0, "details": []}
    W = 60
    print(f"\n{'='*W}")
    print(f"  글자수 검증 리포트 — {md_path.name}")
    print(f"{'='*W}")

    for block in blocks:
        sid_m = sid_re.search(block)
        if not sid_m:
            continue
        sid = sid_m.group(1)
        report["total"] += 1
        block_issues = []

        k_m = kakao_re.search(block)
        if k_m:
            kn = int(k_m.group(1))
            if kn > KAKAO_MAX:
                block_issues.append(f"카카오 {kn}자 초과 (>{KAKAO_MAX})")
        else:
            block_issues.append("카카오 글자수 정보 없음")

        n_m = nl_re.search(block)
        if n_m:
            nn = int(n_m.group(1))
            if not (NL_MIN <= nn <= NL_MAX):
                block_issues.append(f"뉴스레터 {nn}자 (목표 {NL_MIN}~{NL_MAX})")
        else:
            block_issues.append("뉴스레터 글자수 정보 없음")

        c_m = card_re.search(block)
        if c_m:
            cn = int(c_m.group(1))
            if not (CARD_MIN <= cn <= CARD_MAX):
                block_issues.append(f"카드뉴스 {cn}장 (필요 {CARD_MIN}~{CARD_MAX})")
        else:
            block_issues.append("카드뉴스 장수 정보 없음")

        status = "✅" if not block_issues else "⚠️ "
        flag   = "ok" if not block_issues else "warn"
        report[flag] += 1
        detail = f"  {status} #{sid}: {', '.join(block_issues) if block_issues else '통과'}"
        print(detail)
        report["details"].append({"id": sid, "flag": flag, "issues": block_issues})

    print(f"\n  합계: {report['total']}건 | 통과: {report['ok']}건 | 경고: {report['warn']}건")
    print(f"{'='*W}\n")
    return report


# ══════════════════════════════════════════════════════════════
# 8. 프롬프트 내보내기 (--export-prompts)
#    → 출력된 JSON을 Claude Code 대화에 붙여서 응답받고
#      gen.json 으로 저장 후 --from-json 으로 다시 실행
# ══════════════════════════════════════════════════════════════

def export_prompts(seeds: list[dict], out_path: Path) -> None:
    payload = []
    for seed in seeds:
        payload.append({
            "id":     seed["id"],
            "topic":  seed["topic"],
            "system": SYSTEM_PROMPT,
            "prompt": build_user_prompt(seed),
        })
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[export] {len(payload)}개 프롬프트 → {out_path}")
    print("다음 단계: Claude Code 대화에서 각 프롬프트를 실행해 응답을 수집하고")
    print(f"           gen.json 파일에 {{id: ..., content: {{card_news:…, kakao:…, newsletter:…}}}} 형식으로 저장 후")
    print("           python pipeline.py --from-json gen.json 으로 재실행하세요.")


# ══════════════════════════════════════════════════════════════
# 9. JSON에서 콘텐츠 로드 (--from-json)
#    gen.json 형식: [{id, content: {card_news, kakao, newsletter}}, …]
# ══════════════════════════════════════════════════════════════

def load_content_from_json(json_path: Path) -> dict[str, dict]:
    """id → content 딕셔너리 반환"""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    mapping = {}
    for item in data:
        sid = str(item["id"]).zfill(2)
        mapping[sid] = item["content"]
    return mapping


# ══════════════════════════════════════════════════════════════
# 10. 검토 카드 (--review)
#     신호등 + 카카오 첫 줄 → 10초 안에 무엇을 고쳐야 할지 파악
# ══════════════════════════════════════════════════════════════

REVIEW_PATH = BASE_DIR / "output" / "review_summary.md"

def _traffic_light(content: dict, seed: dict) -> tuple[str, list[str]]:
    """🟢/🟡/🔴 + 이유 반환"""
    hard_issues  = validate_content(content)   # 규격 위반
    soft_issues  = []

    # 소프트 경고: 필수 키워드가 2개 미만
    all_text = json.dumps(content, ensure_ascii=False)
    matched  = [kw for kw in seed["keywords"] if kw and kw in all_text]
    if seed["keywords"] and len(matched) < 2:
        soft_issues.append(f"필수 용어 {len(matched)}/{len(seed['keywords'])}개만 반영")

    # 소프트 경고: 카카오 180자 이상 (링크 포함 시 200자 초과 위험)
    kakao_len = len(content.get("kakao", {}).get("text", ""))
    if 180 <= kakao_len <= KAKAO_MAX:
        soft_issues.append(f"카카오 {kakao_len}자 (링크 추가 시 초과 위험)")

    if hard_issues:
        return "🔴", hard_issues
    if soft_issues:
        return "🟡", soft_issues
    return "🟢", []


def review_content(json_path: Path, csv_path: Path) -> None:
    """검토 카드 출력 + review_summary.md 저장"""
    if not json_path.exists():
        print(f"[오류] gen.json 없음: {json_path}")
        print("먼저 python pipeline.py --from-json output/gen.json 을 실행하세요.")
        sys.exit(1)

    seeds    = {s["id"]: s for s in load_seeds(csv_path)}
    json_map = load_content_from_json(json_path)

    W = 68
    today = date.today().isoformat()
    rows   = []   # (light, sid, topic_short, kakao_preview, reasons)

    for sid in sorted(json_map.keys()):
        content = json_map[sid]
        seed    = seeds.get(sid, {"id": sid, "topic": "?", "keywords": [], "evergreen": True, "_decision": ""})
        light, reasons = _traffic_light(content, seed)

        kakao_text    = content.get("kakao", {}).get("text", "")
        kakao_preview = kakao_text[:22].replace("\n", " ")
        if len(kakao_text) > 22:
            kakao_preview += "..."

        topic_short = seed["topic"][:17]
        if len(seed["topic"]) > 17:
            topic_short += "…"

        rows.append((light, sid, topic_short, kakao_preview, reasons))

    # ── 터미널 출력 ──────────────────────────────────────────
    print(f"\n{'='*W}")
    print(f"  널스빌리지 콘텐츠 검토 카드 — {today}")
    print(f"{'='*W}")

    green = yellow = red = 0
    for light, sid, topic, preview, reasons in rows:
        reason_str = f"  [{', '.join(reasons)}]" if reasons else ""
        line = f"  {light} #{sid} {topic:<18}  카카오: \"{preview}\"{reason_str}"
        print(line)
        if light == "🟢": green  += 1
        elif light == "🟡": yellow += 1
        else:               red    += 1

    print(f"{'─'*W}")
    print(f"  🟢 통과 {green}건   🟡 확인 {yellow}건   🔴 수정 {red}건")
    if yellow + red > 0:
        print(f"  → 🟡·🔴 {yellow+red}건만 열어보세요")
    else:
        print("  → 전체 통과! 바로 발행 준비하세요 ✨")
    print(f"{'='*W}\n")

    # ── review_summary.md 저장 ───────────────────────────────
    md_lines = [
        f"# 콘텐츠 검토 카드 — {today}\n",
        f"> 🟢 통과 {green}건 | 🟡 확인 {yellow}건 | 🔴 수정 {red}건\n",
        "| 상태 | ID | 주제 | 카카오 미리보기 | 확인 사항 |",
        "|------|-----|------|----------------|----------|",
    ]
    for light, sid, topic, preview, reasons in rows:
        reason_cell = ", ".join(reasons) if reasons else "—"
        md_lines.append(f"| {light} | #{sid} | {topic} | {preview} | {reason_cell} |")

    md_lines += [
        "",
        "## 🔴 수정 필요 항목" if red else "",
        "## 🟡 확인 필요 항목" if yellow else "",
    ]
    for light, sid, topic, preview, reasons in rows:
        if light in ("🔴", "🟡"):
            md_lines.append(f"\n### #{sid} {topic}")
            for r in reasons:
                md_lines.append(f"- {r}")

    REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_PATH.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"[저장] {REVIEW_PATH}")


# ══════════════════════════════════════════════════════════════
# 11. decisions.md 기록
# ══════════════════════════════════════════════════════════════

def append_decisions(entries: list[str]) -> None:
    if not entries:
        return
    existing = DEC_PATH.read_text(encoding="utf-8") if DEC_PATH.exists() else "# 의사결정 로그\n"
    today = date.today().isoformat()
    block = f"\n## {today} 파이프라인 실행\n" + "\n".join(f"- {e}" for e in entries) + "\n"
    DEC_PATH.write_text(existing + block, encoding="utf-8")
    print(f"[decisions.md] {len(entries)}개 결정 기록")


# ══════════════════════════════════════════════════════════════
# 11. 메인
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="널스빌리지 SNS 콘텐츠 자동 생성 파이프라인")
    parser.add_argument("--id",            help="처리할 시드 ID (쉼표 구분): 01,03,07")
    parser.add_argument("--dry-run",       action="store_true", help="프롬프트 출력만 (API 호출 없음)")
    parser.add_argument("--sdk",           action="store_true", help="Anthropic SDK (ANTHROPIC_API_KEY 필요)")
    parser.add_argument("--from-json",     metavar="JSON",      help="사전 생성 JSON 파일 로드")
    parser.add_argument("--export-prompts",action="store_true", help="프롬프트를 JSON으로 내보내기")
    parser.add_argument("--validate-only", action="store_true", help="기존 MD 파일 글자수 검증만")
    parser.add_argument("--review",        action="store_true", help="신호등 검토 카드 출력 (10초 검토용)")
    parser.add_argument("--csv",           default=str(CSV_PATH), help=f"입력 CSV (기본: {CSV_PATH})")
    parser.add_argument("--output",        default=str(OUT_PATH), help=f"출력 MD (기본: {OUT_PATH})")
    args = parser.parse_args()

    out_path = Path(args.output)
    csv_path = Path(args.csv)

    # ── 검토 카드 ────────────────────────────────────────────
    if args.review:
        review_content(GEN_JSON, csv_path)
        return

    # ── 검증 전용 ────────────────────────────────────────────
    if args.validate_only:
        if not out_path.exists():
            print(f"[오류] {out_path} 파일이 없습니다.")
            sys.exit(1)
        validate_existing_md(out_path)
        return

    # ── 시드 로드 ────────────────────────────────────────────
    seeds = load_seeds(csv_path)
    if args.id:
        target_ids = {i.strip().zfill(2) for i in args.id.split(",")}
        seeds = [s for s in seeds if s["id"] in target_ids]
        if not seeds:
            print(f"[오류] 해당 ID를 찾을 수 없음: {args.id}")
            sys.exit(1)

    # ── 프롬프트 내보내기 ────────────────────────────────────
    if args.export_prompts:
        export_prompts(seeds, GEN_JSON)
        return

    # ── 모드 결정 ─────────────────────────────────────────────
    from_json_path = Path(args.from_json) if args.from_json else None
    mode = ("json" if from_json_path else
            "sdk"  if args.sdk else
            "cli")

    print(f"[파이프라인 시작] {len(seeds)}개 시드 | 모드: {mode} | dry-run: {args.dry_run}")
    print(f"  CSV : {csv_path}")
    print(f"  출력: {out_path}\n")

    # ── Dry-run ──────────────────────────────────────────────
    if args.dry_run:
        for s in seeds:
            print(f"\n{'='*60}\n시드 #{s['id']}: {s['topic']}\n{'='*60}")
            print(build_user_prompt(s))
        return

    # ── JSON 로드 ────────────────────────────────────────────
    json_map: dict[str, dict] = {}
    if from_json_path:
        if not from_json_path.exists():
            print(f"[오류] JSON 파일 없음: {from_json_path}")
            sys.exit(1)
        json_map = load_content_from_json(from_json_path)
        print(f"[json] {len(json_map)}개 콘텐츠 로드됨\n")

    # ── 생성 루프 ─────────────────────────────────────────────
    output_sections: list[str] = []
    decisions: list[str] = []
    ok_count = err_count = warn_count = 0

    for seed in seeds:
        sid = seed["id"]
        label = f"[{sid}] {seed['topic'][:28]}"
        print(f"{label:35s}", end="", flush=True)

        if seed["_decision"]:
            decisions.append(seed["_decision"])

        try:
            if mode == "json":
                if sid not in json_map:
                    raise KeyError(f"JSON에 ID {sid} 없음")
                content = json_map[sid]
            elif mode == "sdk":
                content = generate_content(seed, use_sdk=True)
            else:
                content = generate_content(seed, use_sdk=False)

            issues  = validate_content(content)
            terms   = extract_terms(content, seed["keywords"])
            section = format_seed_md(seed, content, terms, issues)
            output_sections.append(section)

            if issues:
                warn_count += 1
                print(f"⚠️  {' | '.join(issues)}", flush=True)
            else:
                ok_count += 1
                print("✅", flush=True)

        except Exception as exc:
            err_count += 1
            print(f"❌ {exc}", flush=True)
            output_sections.append(
                f"### 시드 #{sid}: {seed['topic']}\n\n> ❌ 생성 오류: {exc}\n"
            )

    # ── 출력 파일 ─────────────────────────────────────────────
    today = date.today().isoformat()
    header = (
        f"# 널스빌리지 SNS 콘텐츠 3종 세트 — {today}\n\n"
        f"> 생성: {len(output_sections)}건 | ✅ {ok_count} | ⚠️ {warn_count} | ❌ {err_count} | "
        f"CSV: {csv_path.name} | 모드: {mode}\n\n---\n\n"
    )
    body = "\n---\n\n".join(output_sections)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(header + body, encoding="utf-8")
    print(f"\n[완료] {out_path} 저장됨")

    # ── 최종 검증 ─────────────────────────────────────────────
    validate_existing_md(out_path)

    # ── decisions.md ─────────────────────────────────────────
    append_decisions(decisions)


if __name__ == "__main__":
    main()
