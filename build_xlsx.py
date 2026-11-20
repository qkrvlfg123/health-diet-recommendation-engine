"""
원본 데이터셋(foodcourt_dataset_v4_3.xlsx)에 문헌 검토 결과를 반영한 v4.4를 만든다.

v4_3 파일은 수정하지 않는다. v4_3을 읽어 아래를 반영한 뒤 foodcourt_dataset_v4_4.xlsx 로 저장한다.

  02_질환_식품규칙 : 검토한 근거수준·근거 문헌 ID 반영, 보완 규칙(R033~) 추가, food_tag·검토 판정 열 추가
  08_약물_식품규칙 : 검토한 근거수준·수정 사항 반영, 보완 규칙(DR018~) 추가, 검토 판정 열 추가
  14_약물사전      : 통풍약(RX017, RX018) 추가
  15_메뉴사전      : HIGH_PROTEIN 태그 추가
  23_문헌근거      : 근거 문헌 목록 (신규 시트)
  24_규칙검토      : 원본 규칙 49개의 검토 판정 (신규 시트)
  25_변경이력      : v4.3 → v4.4 변경 내역 (신규 시트)

반영할 내용은 엔진이 실제로 쓰는 값(recommend.py가 원본 + 보완 + 검토를 합친 결과)에서 가져오므로
xlsx와 엔진이 어긋나지 않는다. 저장 후 다시 읽어 엔진 값과 같은지 검증한다.

실행:  pip install openpyxl  &&  python build_xlsx.py
"""
import copy
import os

import openpyxl

import recommend as r

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "data", "foodcourt_dataset_v4_3.xlsx")
DST = os.path.join(HERE, "data", "foodcourt_dataset_v4_4.xlsx")

REVIEW = r._load("rule_review.json")
REVIEWED = {x["id"]: x for x in REVIEW["disease_rules"] + REVIEW["drug_rules"]}
SUPP = r._load("rules_supplement.json")


def header(ws):
    return [c.value for c in ws[1]]


def rows_by_key(ws, key_col=1):
    """첫 열 값 → 행 번호. 빈 행은 건너뛴다."""
    return {ws.cell(row=i, column=key_col).value: i for i in range(2, ws.max_row + 1)
            if ws.cell(row=i, column=key_col).value}


def first_empty_row(ws):
    i = 2
    while ws.cell(row=i, column=1).value:
        i += 1
    return i


def copy_style(src, dst):
    if src.has_style:
        dst.font, dst.fill, dst.border = copy.copy(src.font), copy.copy(src.fill), copy.copy(src.border)
        dst.alignment, dst.number_format = copy.copy(src.alignment), src.number_format


def add_column(ws, name):
    """헤더 오른쪽 끝에 열을 추가하고 열 번호를 돌려준다(이미 있으면 그 번호)."""
    head = header(ws)
    if name in head:
        return head.index(name) + 1
    col = len(head) + 1
    ws.cell(row=1, column=col, value=name)
    copy_style(ws.cell(row=1, column=1), ws.cell(row=1, column=col))
    return col


def write_row(ws, row, values, style_from_row=2):
    for j, v in enumerate(values, start=1):
        cell = ws.cell(row=row, column=j, value=v)
        copy_style(ws.cell(row=style_from_row, column=min(j, len(header(ws)))), cell)


def merge_ids(*parts):
    """근거 ID 문자열들을 합친다(원본 출처를 지우지 않고 뒤에 문헌 ID를 덧붙임, 중복 제거)."""
    out = []
    for p in parts:
        for i in str(p or "").split("|"):
            if i and i not in out:
                out.append(i)
    return "|".join(out)


def verdict(rule_id):
    x = REVIEWED.get(rule_id)
    if not x:
        return "v4.4 추가", ""
    label = x["판정"] if x["원본_근거수준"] == x["검토_근거수준"] else f"{x['판정']} ({x['원본_근거수준']}→{x['검토_근거수준']})"
    return label, x["검토내용"]


def new_sheet(wb, title, head, rows, widths, style_ws):
    ws = wb.create_sheet(title)
    for j, h in enumerate(head, start=1):
        c = ws.cell(row=1, column=j, value=h)
        copy_style(style_ws.cell(row=1, column=1), c)
    for i, row in enumerate(rows, start=2):
        for j, v in enumerate(row, start=1):
            c = ws.cell(row=i, column=j, value=v)
            copy_style(style_ws.cell(row=2, column=1), c)
    for j, w in enumerate(widths, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(j)].width = w
    ws.freeze_panes = "A2"
    return ws


def build():
    wb = openpyxl.load_workbook(SRC)
    log = []

    # ---------------------------------------------------------------- 02_질환_식품규칙
    ws = wb["02_질환_식품규칙"]
    head = header(ws)
    col = {h: i + 1 for i, h in enumerate(head)}
    c_tag, c_verdict, c_note = add_column(ws, "food_tag"), add_column(ws, "검토 판정(v4.4)"), add_column(ws, "검토 내용(v4.4)")
    existing = rows_by_key(ws)
    for rule in r.DISEASE_RULES:
        rid = rule["rule_id"]
        tags = "|".join(dict.fromkeys(r.DISEASE_RULE_TAGS.get(rid, [])
                                      + [t for t in rule.get("food_tag", "").split("|") if t]))
        v, note = verdict(rid)
        if rid in existing:
            i = existing[rid]
            old = ws.cell(row=i, column=col["근거수준"]).value
            if old != rule["근거수준"]:
                log.append(("02_질환_식품규칙", rid, "근거수준", old, rule["근거수준"], note))
                ws.cell(row=i, column=col["근거수준"], value=rule["근거수준"])
            ws.cell(row=i, column=col["source_id"],
                    value=merge_ids(ws.cell(row=i, column=col["source_id"]).value, REVIEWED[rid]["source_id"]))
            if rule.get("_inactive"):
                log.append(("02_질환_식품규칙", rid, "적용", "적용", "적용 중지", note))
        else:
            i = first_empty_row(ws)
            write_row(ws, i, [rule.get(h, "") for h in head])
            log.append(("02_질환_식품규칙", rid, "(규칙 추가)", "", f"{rule['질환명']} – {rule['식품군/특성']} ({rule['근거수준']})", rule["근거 기반 이유"]))
        for c, val in ((c_tag, tags), (c_verdict, v), (c_note, note)):
            copy_style(ws.cell(row=i, column=1), ws.cell(row=i, column=c, value=val))

    # ---------------------------------------------------------------- 08_약물_식품규칙
    ws = wb["08_약물_식품규칙"]
    head = header(ws)
    col = {h: i + 1 for i, h in enumerate(head)}
    c_verdict, c_note = add_column(ws, "검토 판정(v4.4)"), add_column(ws, "검토 내용(v4.4)")
    existing = rows_by_key(ws)
    for rule in r.DRUG_RULES:
        rid = rule["drug_rule_id"]
        eff = dict(rule)
        extra = r.DRUG_RULE_EXTRA_TAGS.get(rid, [])     # 엔진이 추가로 인정하는 메뉴 태그도 데이터셋에 적는다
        eff["food_tag"] = "|".join(dict.fromkeys([t for t in rule.get("food_tag", "").split("|") if t] + extra))
        v, note = verdict(rid)
        if rid in existing:
            i = existing[rid]
            why = SUPP["drug_rules_override"].get(rid, {}).get("_변경이유", note)
            # 원본 출처(DS…)는 남기고 문헌 ID(E…)를 덧붙인다
            eff["source_id"] = merge_ids(ws.cell(row=i, column=col["source_id"]).value,
                                         REVIEWED[rid]["source_id"], rule.get("source_id"))
            for h in head:
                old, new = ws.cell(row=i, column=col[h]).value, eff.get(h, "")
                if (old or "") != (new or ""):
                    log.append(("08_약물_식품규칙", rid, h, old, new, why if h != "근거수준" else note))
                    ws.cell(row=i, column=col[h], value=new)
        else:
            i = first_empty_row(ws)
            write_row(ws, i, [eff.get(h, "") for h in head])
            log.append(("08_약물_식품규칙", rid, "(규칙 추가)", "", f"{eff['약물군(대표성분)']} – {eff['식품군/특성']} ({eff['근거수준']})", eff["근거 기반 이유"]))
        for c, val in ((c_verdict, v), (c_note, note)):
            copy_style(ws.cell(row=i, column=1), ws.cell(row=i, column=c, value=val))

    # ---------------------------------------------------------------- 14_약물사전
    ws = wb["14_약물사전"]
    head, existing = header(ws), rows_by_key(ws)
    for d in r.DRUG_DICT:
        if d["drug_id"] not in existing:
            write_row(ws, first_empty_row(ws), [d.get(h, "") for h in head])
            log.append(("14_약물사전", d["drug_id"], "(약물군 추가)", "", d["약물군"], d.get("비고", "")))

    # ---------------------------------------------------------------- 15_메뉴사전
    ws = wb["15_메뉴사전"]
    head, existing = header(ws), rows_by_key(ws)
    c = head.index("food_tag") + 1
    for m in r.MENU:
        i = existing[m["menu_id"]]
        old = ws.cell(row=i, column=c).value
        if old != m["food_tag"]:
            ws.cell(row=i, column=c, value=m["food_tag"])
            log.append(("15_메뉴사전", m["menu_id"], "food_tag", old, m["food_tag"],
                        "파킨슨약–고단백 식사 규칙(DR007)이 동작하도록 육류가 주재료인 메뉴에 HIGH_PROTEIN 추가(작성자 판단)"))

    # ---------------------------------------------------------------- 신규 시트
    style = wb["08_약물_식품규칙"]
    ev = r._load("evidence_sources.json")["sources"]
    new_sheet(wb, "23_문헌근거", ["source_id", "문헌", "PMID", "URL", "연구설계", "핵심 내용", "확인 수준"],
              [[e["id"], e["citation"], e["pmid"], e["url"], e["연구설계"], e["핵심내용"], e["확인수준"]] for e in ev],
              [10, 70, 12, 45, 32, 80, 50], style)
    names = {x["rule_id"]: f"{x['질환명']} – {x['식품군/특성']}" for x in r.DISEASE_RULES}
    names.update({x["drug_rule_id"]: f"{x['약물군(대표성분)']} – {x['식품군/특성']}" for x in r.DRUG_RULES})
    new_sheet(wb, "24_규칙검토", ["rule_id", "대상", "원본 근거수준", "검토 근거수준", "판정", "근거 문헌", "검토 내용"],
              [[x["id"], names[x["id"]], x["원본_근거수준"], x["검토_근거수준"], x["판정"], x["source_id"], x["검토내용"]]
               for x in REVIEW["disease_rules"] + REVIEW["drug_rules"]],
              [10, 45, 14, 14, 16, 22, 100], style)
    for it in SUPP["rules_not_created"]:
        log.append(("(규칙 미작성)", it["대상"], it["결정"], "", "", it["이유"]))
    new_sheet(wb, "25_변경이력", ["시트", "대상 ID", "항목", "v4.3 값", "v4.4 값", "변경 이유"],
              [list(x) for x in log], [20, 30, 22, 45, 60, 100], style)

    wb.save(DST)
    return log


def verify():
    """저장한 v4.4를 다시 읽어 엔진이 쓰는 값과 같은지 확인한다."""
    wb = openpyxl.load_workbook(DST)
    ws = wb["02_질환_식품규칙"]
    col = {h: i + 1 for i, h in enumerate(header(ws))}
    rows = rows_by_key(ws)
    for rule in r.DISEASE_RULES:
        i = rows[rule["rule_id"]]
        assert ws.cell(row=i, column=col["근거수준"]).value == rule["근거수준"], rule["rule_id"]
        assert ws.cell(row=i, column=col["action"]).value == rule["action"], rule["rule_id"]
    ws = wb["08_약물_식품규칙"]
    col = {h: i + 1 for i, h in enumerate(header(ws))}
    rows = rows_by_key(ws)
    for rule in r.DRUG_RULES:
        i = rows[rule["drug_rule_id"]]
        for h in ("근거수준", "action", "서비스 문구 예시", "푸드코트 키워드 예시"):
            assert (ws.cell(row=i, column=col[h]).value or "") == (rule.get(h) or ""), (rule["drug_rule_id"], h)
    assert set(rows_by_key(wb["14_약물사전"])) == {d["drug_id"] for d in r.DRUG_DICT}
    ws = wb["15_메뉴사전"]
    c = header(ws).index("food_tag") + 1
    rows = rows_by_key(ws)
    for m in r.MENU:
        assert ws.cell(row=rows[m["menu_id"]], column=c).value == m["food_tag"], m["menu_id"]
    # 원본 시트가 그대로 남아 있는지 (시트 수: 22 + 신규 3)
    assert len(wb.sheetnames) == 25, wb.sheetnames
    return len(r.DISEASE_RULES), len(r.DRUG_RULES), len(r.DRUG_DICT), len(r.MENU)


if __name__ == "__main__":
    changes = build()
    n = verify()
    print(f"{os.path.basename(DST)} 저장: 변경 {len(changes)}건")
    print(f"검증 통과: 질환 규칙 {n[0]}개, 약물 규칙 {n[1]}개, 약물군 {n[2]}개, 메뉴 {n[3]}개가 엔진 값과 일치")
