"""
원본 규칙의 문헌 검토 결과(data/rule_review.json)를 읽기 쉬운 표로 만든다.

실행:  python review_report.py      →  docs/rule_review.md 생성
"""
import os

import recommend as r

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "rule_review.md")


def short(source_ids):
    """근거 ID를 '저자 연도' 형태의 짧은 표기로 바꾼다."""
    out = []
    for i in [x for x in source_ids.split("|") if x]:
        cite = r.EVIDENCE[i]["citation"]
        out.append(f"{i} {cite.split('.')[0][:40]}")
    return "<br>".join(out) or "-"


def table(rows, name_of):
    lines = ["| 규칙 | 대상 | 원본 | 검토 | 판정 | 근거 문헌 | 검토 내용 |", "|---|---|---|---|---|---|---|"]
    for x in rows:
        mark = "**" if x["원본_근거수준"] != x["검토_근거수준"] else ""
        lines.append(f"| {x['id']} | {name_of[x['id']]} | {x['원본_근거수준']} | {mark}{x['검토_근거수준']}{mark} | "
                     f"{x['판정']} | {short(x['source_id'])} | {x['검토내용']} |")
    return "\n".join(lines)


def main():
    review = r._load("rule_review.json")
    d_name = {x["rule_id"]: f"{x['질환명']} – {x['식품군/특성']}" for x in r.DISEASE_RULES}
    g_name = {x["drug_rule_id"]: f"{x['약물군(대표성분)']} – {x['식품군/특성']}" for x in r.DRUG_RULES}
    allrows = review["disease_rules"] + review["drug_rules"]
    count = {}
    for x in allrows:
        count[x["판정"]] = count.get(x["판정"], 0) + 1
    md = f"""# 원본 규칙의 문헌 검토 결과

원본 데이터셋의 규칙 {len(allrows)}개(질환 {len(review['disease_rules'])}개, 약물 {len(review['drug_rules'])}개)를 문헌으로 검토한 결과입니다.
이 파일은 `python review_report.py`로 `data/rule_review.json`에서 생성합니다.

- 판정 집계: {", ".join(f"{k} {v}개" for k, v in sorted(count.items()))}
- 근거수준 기준: HIGH = 무작위 시험과 그 메타분석, 허가사항·규제기관 규정, 지침의 강한 권고 / MEDIUM = 관찰 연구, 조건부 권고, 전문가 합의, 소규모 약동학 연구, 증례 보고, 종설
- 등급을 바꾸거나 적용을 중지한 규칙에는 반드시 근거 문헌이 있습니다. "적용 중지"는 문헌이 규칙 자체를 뒷받침하지 않아 엔진에서 적용하지 않는 규칙입니다(삭제하지 않고 남김).
- 문헌은 PubMed 초록과 검색 요약으로 확인했습니다. 문헌별 확인 범위는 `data/evidence_sources.json`의 `확인수준`에 있습니다.

## 질환–식품 규칙 ({len(review['disease_rules'])}개)

{table(review['disease_rules'], d_name)}

## 약물–식품 규칙 ({len(review['drug_rules'])}개)

{table(review['drug_rules'], g_name)}

---

이 검토 결과는 학습·포트폴리오 목적의 참고 자료입니다. 의료기기가 아니며 진단·처방·복약 지도를 대신하지 않습니다.
문헌은 초록과 요약 수준에서 확인했고 의사·약사·영양사의 검수를 거치지 않았습니다. 실제 식사나 약 복용에 관한 결정은 담당 의료진과 상의해야 합니다.
"""
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    print(f"{OUT} 생성: " + ", ".join(f"{k} {v}" for k, v in sorted(count.items())))


if __name__ == "__main__":
    main()
