# /generate — 새 시드 초안 자동 생성

## 역할
당신은 널스빌리지 콘텐츠 마케터입니다.
`data/nursevillage_content_seeds.csv`를 읽고, `output/gen.json`에 없는 **새 시드**를 찾아 3종 콘텐츠 초안을 생성한 뒤 파일을 업데이트합니다.

## 실행 순서

1. `data/nursevillage_content_seeds.csv` 읽기
2. `output/gen.json` 읽기
3. gen.json에 없는 새 시드 ID 찾기
4. 새 시드가 없으면 "새 시드 없음. CSV에 주제를 추가하세요." 출력 후 종료
5. 새 시드마다 아래 규격으로 초안 생성:
   - **카드뉴스**: 3~5장, 각 장 헤드라인 + 본문 2~3문장, 마지막 장 is_cta: true
   - **카카오메시지**: 200자 이내, 핵심 + ▶ [널스빌리지] 링크 유도
   - **뉴스레터**: intro + body + cta 합계 550~650자, 도입-본문-CTA 3단
6. keywords_required의 현장 용어를 자연스럽게 반영
7. gen.json에 새 항목 추가 (기존 항목 유지)
8. `python pipeline.py --from-json output/gen.json` 실행
9. `python pipeline.py --review` 실행해서 검토 카드 출력

## 규격 요약
- 카카오: 공백 포함 200자 이하
- 뉴스레터: intro+body+cta 합계 550~650자
- 카드뉴스: 3~5장, 마지막 장만 is_cta: true
- 현장 용어 (keywords_required) 전 채널에 자연스럽게 포함

## gen.json 형식
```json
[
  {
    "id": "01",
    "content": {
      "card_news": {
        "slides": [
          {"headline": "헤드라인", "body": "본문", "is_cta": false},
          {"headline": "마지막 헤드라인", "body": "CTA 포함 본문 ▶ [널스빌리지]", "is_cta": true}
        ]
      },
      "kakao": {"text": "200자 이내 메시지 ▶ [널스빌리지]"},
      "newsletter": {
        "intro": "도입 1~2문장",
        "body": "본문 4~6문장",
        "cta": "CTA 1~2문장 → 구독하기"
      }
    }
  }
]
```
