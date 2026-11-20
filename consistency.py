"""
메뉴사전과 엔진 결과의 일치 검사

메뉴사전(15_메뉴사전)에는 메뉴마다 '관련 질환 규칙'과 '관련 약물 규칙' 열이 있다.
데이터셋을 설계할 때 사람이 "이 메뉴는 이 질환·약과 관련 있다"고 적어 둔 값이다.
엔진이 실제로 그 질환·약에 대해 규칙을 적용하는지를 전수 비교한다.

  누락(gap)  : 사전에는 관련 있다고 적혀 있는데 엔진에서는 아무 규칙도 걸리지 않음
  추가(extra): 사전에는 없는데 엔진에서는 제한 규칙이 걸림 (규칙 본문에 근거가 있으면 정상)

v2에서는 이런 검사가 없어서, 사전과 엔진이 어긋나 있어도 알 수 없었다.

실행:  python consistency.py
"""
import re

import recommend as r

# 메뉴사전의 질환 표기 → 규칙 파일의 질환명
DISEASE_ALIAS = {"CKD": "만성콩팥병(CKD)"}

# 메뉴사전의 약물 표기(자유 서술)에서 찾을 단어 → drug_id. 앞에 있는 항목이 먼저 검사된다.
DRUG_ALIAS = [
    ("와파린", "RX001"), ("혈압약(CCB)", "RX002"), ("혈압약(이뇨제", "RX003"), ("고지혈증약", "RX004"),
    ("항우울제", "RX005"), ("파킨슨약", "RX006"), ("갑상선약", "RX007"), ("당뇨약", "RX008"),
    ("항생제", "RX009"), ("골다공증약", "RX010"), ("천식약", "RX011"), ("진통제", "RX012"),
    ("감기약", "RX014"), ("위장약", "RX015"), ("통풍약", "RX018"),
]
# 사전에는 나오지만 약물사전(14_약물사전)에 항목이 없는 약
DRUG_NOT_IN_DICT = []

# 알고 있는 누락과 그 이유. 테스트는 "여기 적힌 것 외의 누락이 없을 것"을 검사한다.
# v3에서 8건이던 누락 중 5건은 문헌 근거로 규칙·태그를 보완해 해소했다(data/rules_supplement.json).
# 아래는 문헌을 검토한 뒤 "규칙을 만들지 않는다"고 결정한 것들이다(rules_supplement.json의 rules_not_created).
KNOWN_DISEASE_GAPS = {
    ("초밥", "고혈압"): "규칙(R002)은 있음. 간장이 선택 사항이라 메뉴 단위 태그로 판정할 수 없음 → 옵션 단위 데이터 필요",
    ("미역국", "통풍"): "규칙을 만들지 않음. 퓨린이 많은 채소는 통풍 위험과 관련이 없었고(E009), 해조류를 다룬 근거를 찾지 못함",
}
_GOUT_DRUG = "약물 상호작용이 아니라 통풍 질환의 식이 권고임(E010). 질환 규칙 R022~R024가 담당하므로 약물 규칙을 만들지 않음"
KNOWN_DRUG_GAPS = {
    ("비빔밥", "RX001"): "규칙(DR001)은 있음. 나물 종류가 선택 사항이라 메뉴 단위 태그로 판정할 수 없음 → 옵션 단위 데이터 필요",
    ("설렁탕/곰탕", "RX018"): _GOUT_DRUG,
    ("삼겹살구이", "RX018"): _GOUT_DRUG,
    ("곱창/막창", "RX018"): _GOUT_DRUG,
    ("짬뽕", "RX018"): _GOUT_DRUG,
    ("미역국", "RX018"): _GOUT_DRUG,
}


def dictionary_diseases(menu_row):
    out = []
    for raw in menu_row.get("관련 질환 규칙", "").split("|"):
        raw = raw.strip()
        if not raw or raw.startswith("(") or raw == "-":
            continue                      # "(채소권장)", "(무가당)" 같은 메모는 질환이 아님
        name = re.sub(r"\(.*?\)", "", raw).strip()
        out.append(DISEASE_ALIAS.get(name, name))
    return out


def dictionary_drugs(menu_row):
    text = menu_row.get("관련 약물 규칙", "")
    ids, unknown = [], []
    for word, drug_id in DRUG_ALIAS:
        if word in text and drug_id not in ids:
            ids.append(drug_id)
    for word in DRUG_NOT_IN_DICT:
        if word in text:
            unknown.append(word)
    return ids, unknown


def check():
    disease_names = {x["질환명"] for x in r.DISEASE_RULES}
    disease_gaps, disease_extra, drug_gaps, not_in_dict = [], [], [], []
    n_disease = n_drug = 0

    for m in r.MENU:
        name = r.menu_name(m)
        listed = [d for d in dictionary_diseases(m) if d in disease_names]
        # 질환: 사전 → 엔진
        for d in listed:
            n_disease += 1
            e = r.evaluate_menu(m, r.Profile(diseases=[d], ckd_lab_confirmed=True))
            if not any(x["kind"] == "LIMIT" for x in e["reasons"]):
                disease_gaps.append((name, d))
        # 질환: 엔진 → 사전
        for d in sorted(disease_names - set(listed)):
            e = r.evaluate_menu(m, r.Profile(diseases=[d], ckd_lab_confirmed=True))
            for x in e["reasons"]:
                if x["kind"] == "LIMIT":
                    disease_extra.append((name, d, x["source"], x["basis"]))
        # 약물: 사전 → 엔진
        ids, unknown = dictionary_drugs(m)
        for w in unknown:
            not_in_dict.append((name, w))
        for drug_id in ids:
            n_drug += 1
            e = r.evaluate_menu(m, r.Profile(drug_ids=[drug_id]))
            if not any(x["kind"] in ("DRUG_LIMIT", "DRUG_TIMING") for x in e["reasons"]):
                drug_gaps.append((name, drug_id))

    return dict(n_disease=n_disease, n_drug=n_drug, disease_gaps=disease_gaps, disease_extra=disease_extra,
                drug_gaps=drug_gaps, not_in_dict=not_in_dict)


def main():
    c = check()
    print(f"[질환] 메뉴사전의 (메뉴, 질환) 쌍 {c['n_disease']}개 중 엔진에서 제한 규칙이 걸리지 않는 쌍: {len(c['disease_gaps'])}개")
    for name, d in c["disease_gaps"]:
        print(f"  - {name} / {d}: {KNOWN_DISEASE_GAPS.get((name, d), '(미분류)')}")
    print(f"\n[질환] 사전에는 없지만 엔진에서 제한 규칙이 걸리는 쌍: {len(c['disease_extra'])}개")
    for name, d, rid, basis in c["disease_extra"]:
        print(f"  - {name} / {d}: {rid} ({basis})")
    print(f"\n[약물] 메뉴사전의 (메뉴, 약) 쌍 {c['n_drug']}개 중 엔진에서 규칙이 걸리지 않는 쌍: {len(c['drug_gaps'])}개")
    names = {d["drug_id"]: d["약물군"] for d in r.DRUG_DICT}
    for name, drug_id in c["drug_gaps"]:
        print(f"  - {name} / {drug_id} {names.get(drug_id, '')}: {KNOWN_DRUG_GAPS.get((name, drug_id)) or '(미분류)'}")
    print(f"\n[약물] 메뉴사전에는 나오지만 약물사전에 항목이 없는 약: {len(c['not_in_dict'])}건")
    for name, w in c["not_in_dict"]:
        print(f"  - {name} / {w}")


if __name__ == "__main__":
    main()
