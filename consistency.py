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
    ("감기약", "RX014"), ("위장약", "RX015"),
]
# 사전에는 나오지만 약물사전(14_약물사전)에 항목이 없는 약
DRUG_NOT_IN_DICT = ["통풍약"]

# 알고 있는 누락과 그 이유. 테스트는 "여기 적힌 것 외의 누락이 없을 것"을 검사한다.
# 규칙이나 태그를 억지로 늘려 맞추지 않고, 데이터에 대응 규칙이 없다는 사실을 그대로 기록한다.
KNOWN_DISEASE_GAPS = {
    ("초밥", "고혈압"): "사전 비고가 '간장'. 간장은 찍어 먹는 선택 사항이라 메뉴 태그(SAUCE)가 없음",
    ("후라이드치킨", "당뇨병"): "당뇨 규칙(R006~R011)에 튀김류 규칙이 없음",
    ("맥주", "이상지질혈증"): "이상지질혈증 규칙(R012~R018)에 알코올 규칙이 없음",
    ("미역국", "통풍"): "통풍 규칙(R022~R027)에 해조류 규칙이 없음",
    ("치즈버거세트", "이상지질혈증"): "SAT_FAT_POSSIBLE 태그에 대응하는 규칙이 없음(R012는 육류, R013은 가공육 키워드 한정)",
}
KNOWN_DRUG_GAPS = {
    ("삼겹살구이", "RX006"): "DR007(고단백)의 태그 HIGH_PROTEIN이 메뉴사전에 없고 키워드('고기')도 메뉴명에 없음",
    ("비빔밥", "RX001"): "사전 비고가 '나물 비타민K'. 비빔밥에는 VITAMIN_K_HIGH 태그가 없음(나물 종류가 정해지지 않음)",
    ("맥주", "RX008"): "당뇨약 규칙(DR009)에 알코올 항목이 없음",
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
