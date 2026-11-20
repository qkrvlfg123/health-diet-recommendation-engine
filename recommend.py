"""
KioBridge 건강 추천 엔진 (규칙 기반 필터링 데모) — v3

사용자 프로필(질환·복용약·알레르기)을 입력하면 메뉴 사전의 각 메뉴를 네 등급으로 나눈다.

  제외   : 알레르기 성분 포함 (후보에서 완전히 제외)
  주의   : 질환·약물 규칙 중 제한(LIMIT) 규칙에 해당
  권장   : 제한 규칙에 해당하지 않고, 권장(RECOMMEND) 규칙에 해당
  판단 보류 : 권장 규칙에 해당하지만, 확인되지 않은 조건부 제한 규칙도 함께 걸려 있음
  규칙 없음 : 입력한 질환·약 기준으로 해당하는 규칙이 없음 (건강에 좋다는 뜻이 아님)

v3에서 고친 점 (v2의 오류)
--------------------------
1. 규칙-태그 연결을 글자 포함 검사에서 명시적 매핑으로 바꿨다.
   v2는 규칙 설명문에 '탕'이라는 글자가 있으면 국물(SOUP) 태그와 연결했는데,
   '설탕' 규칙에도 '탕'이 들어 있어 모든 국물 메뉴에 "시럽이나 설탕을 빼고 주문할까요?"가 붙었다.
   이제 data/rule_tag_map.json 에 규칙 ID별로 태그를 직접 적는다.
2. 규칙에 걸리지 않은 메뉴를 "안심하고 고르기 좋은 메뉴"로 표시하지 않는다.
   v2는 걸린 규칙이 없으면 기본 점수 그대로 최상위에 올라, 고혈압·당뇨 프로필에
   삼겹살·곱창·후라이드치킨이 1~5위로 추천됐다. 규칙이 없다는 것은 판단 근거가 없다는 뜻이다.
3. 약물 규칙도 메뉴명 키워드로 매칭한다(크랜베리주스-와파린 등이 누락되던 문제).
4. 약물 규칙의 CONTROL(복용 시간 조절)은 감점하지 않고 안내만 한다. 제한이 아니기 때문이다.
5. 권장 규칙과 제한 규칙이 함께 걸리면 둘 다 보여 준다(v2는 권장 사유를 버렸다).
6. 조건부 제한 규칙이 보류된 메뉴는 권장하지 않는다.
   v2는 고혈압+CKD(검사 미확인) 프로필에 칼륨이 많은 시금치나물을 채소 권장 규칙만으로 추천했다.
   제한을 자동으로 걸지 않는 것과 적극적으로 권하는 것은 다르므로 '판단 보류'로 따로 표시한다.

근거 데이터: foodcourt_dataset(22시트) 중 15_메뉴사전 / 02_질환_식품규칙 / 08_약물_식품규칙 / 14_약물사전을
JSON으로 변환한 data/*.json.

의료기기가 아니며 진단·처방을 하지 않는다. 공개 식이 가이드라인 기반의 주의 안내만 제공한다.
"""

import json
import os
import re
from dataclasses import dataclass, field

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _load(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


MENU = _load("menu_dictionary.json")
DISEASE_RULES = _load("disease_food_rules.json")
DRUG_RULES = _load("drug_food_rules.json")
DRUG_DICT = _load("drug_dictionary.json")
_TAG_MAP = _load("rule_tag_map.json")
DISEASE_RULE_TAGS = _TAG_MAP["disease_rules"]
DRUG_RULE_EXTRA_TAGS = _TAG_MAP["drug_rules_extra"]


def _apply_supplement():
    """문헌 근거로 추가·수정한 내용(data/rules_supplement.json)을 원본 데이터 위에 덧씌운다.
    원본 파일은 수정하지 않으므로 어떤 규칙이 원본이고 어떤 규칙이 보완인지 추적할 수 있다."""
    supp = _load("rules_supplement.json")
    DISEASE_RULES.extend(supp.get("disease_rules_add", []))
    DRUG_DICT.extend(supp.get("drug_dictionary_add", []))
    DRUG_RULES.extend(supp.get("drug_rules_add", []))
    overrides = supp.get("drug_rules_override", {})
    for rule in DRUG_RULES:
        for key, value in overrides.get(rule["drug_rule_id"], {}).items():
            if not key.startswith("_"):      # "_변경이유" 같은 설명 필드는 규칙에 넣지 않는다
                rule[key] = value
    extra_tags = supp.get("menu_tags_add", {})
    for m in MENU:
        add = [t for t in extra_tags.get(m.get("menu_id"), []) if t not in m.get("food_tag", "").split("|")]
        if add:
            m["food_tag"] = "|".join([m.get("food_tag", "")] + add)
    # 원본 규칙의 문헌 검토 결과(data/rule_review.json): 검토한 근거수준을 덧씌운다.
    # 원본 값은 rule_review.json 의 '원본_근거수준'과 원본 규칙 파일에 그대로 남아 있다.
    review = _load("rule_review.json")
    reviewed = {x["id"]: x for x in review["disease_rules"] + review["drug_rules"]}
    for rule in DISEASE_RULES:
        if rule["rule_id"] in reviewed:
            rule["근거수준"] = reviewed[rule["rule_id"]]["검토_근거수준"]
            # 문헌이 규칙 자체를 뒷받침하지 않아 '적용 중지'로 판정된 규칙 (삭제하지 않고 표시만 한다)
            rule["_inactive"] = reviewed[rule["rule_id"]].get("적용") is False
    for rule in DRUG_RULES:
        if rule["drug_rule_id"] in reviewed:
            rule["근거수준"] = reviewed[rule["drug_rule_id"]]["검토_근거수준"]
    supp["_review"] = reviewed
    return supp


SUPPLEMENT = _apply_supplement()
EVIDENCE = {e["id"]: e for e in _load("evidence_sources.json")["sources"]}

BASE_SCORE = 10
# 점수는 등급 안에서의 정렬과 설명을 위한 데모용 값이다(임상적으로 보정된 값이 아님).
LIMIT_WEIGHT = {"HIGH": -5, "MEDIUM": -3}
RECOMMEND_WEIGHT = {"HIGH": 3, "MEDIUM": 2}
DRUG_WEIGHT = {"HIGH": -6, "MEDIUM": -3}

# '규칙 없음' 등급 메뉴에 덧붙이는 일반 특성 표시. 프로필과 무관하게 메뉴 자체의 특성을 알려 준다.
GENERAL_NOTE = {
    "FRIED": "튀김",
    "SAT_FAT": "고지방",
    "SAT_FAT_POSSIBLE": "고지방 가능",
    "PROCESSED": "가공식품",
    "ALCOHOL": "주류",
    "ADDED_SUGAR": "당류 첨가",
    "SUGAR_SWEETENED_BEVERAGE": "가당음료",
    "HIGH_SODIUM_POSSIBLE": "나트륨 높을 수 있음",
}


@dataclass
class Profile:
    """가상·합성 프로필 (실제 개인정보 사용 금지)"""
    diseases: list = field(default_factory=list)
    drug_ids: list = field(default_factory=list)
    allergen_tags: list = field(default_factory=list)
    ckd_lab_confirmed: bool = False   # CKD 조건부 규칙(칼륨·단백질·인)을 적용할 근거가 있는지


def menu_tags(menu_row):
    return [t.strip() for t in menu_row.get("food_tag", "").split("|") if t.strip()]


def menu_name(menu_row):
    return menu_row.get("메뉴명", "")


def keyword_hit(keyword_field, name):
    """규칙의 키워드 예시 중 메뉴명에 해당하는 키워드를 돌려준다(없으면 None).

    - 두 글자 이상 키워드: 메뉴명에 포함되면 매칭 ('케이크' in '치즈케이크')
    - 한 글자 키워드('국', '탕', '죽' 등): 메뉴명 단어의 끝 글자일 때만 매칭.
      포함 검사로 하면 '국'이 '국수'에, '탕'이 '설탕'에 걸린다.
    """
    parts = [p for p in re.split(r"[/()\s]+", name) if p]
    for kw in keyword_field.split("|"):
        kw = kw.strip()
        if not kw:
            continue
        if len(kw) == 1:
            if any(p.endswith(kw) for p in parts):
                return kw
        elif kw in name:
            return kw
    return None


def match_rule(rule_id, keyword_field, rule_tags, menu_row):
    """규칙이 메뉴에 해당하는지 판정. (매칭 여부, 근거 문자열, 키워드 매칭 여부)를 돌려준다."""
    kw = keyword_hit(keyword_field, menu_name(menu_row))
    if kw:
        return True, f"메뉴명 키워드 '{kw}'", True
    hit = [t for t in rule_tags if t in menu_tags(menu_row)]
    if hit:
        return True, f"태그 {hit[0]}", False
    return False, "", False


def _pick(candidates):
    """한 질환(또는 약)에서 여러 규칙이 걸렸을 때 대표 1개를 고른다.
    영향이 큰 규칙 우선, 같으면 메뉴명 키워드로 걸린(더 구체적인) 규칙 우선."""
    return sorted(candidates, key=lambda c: (-abs(c["weight"]), not c["by_keyword"]))[0]


def evaluate_menu(menu_row, profile):
    """메뉴 하나를 평가해 등급·점수·사유를 돌려준다."""
    tags = menu_tags(menu_row)
    reasons = []
    deferred = []   # 조건이 확인되지 않아 적용을 보류한 규칙 ID
    score = BASE_SCORE

    # 1) 하드 필터: 알레르기
    for allergen in profile.allergen_tags:
        if allergen in tags:
            reasons.append(dict(kind="EXCLUDE", source=allergen, weight=0, basis=f"태그 {allergen}",
                                msg=f"알레르기({allergen}) 성분이 포함되어 후보에서 제외했어요."))

    # 2) 질환-식품 규칙: 질환마다 제한 1개 + 권장 1개까지만 반영(같은 질환의 과잉 경고 방지)
    for disease in profile.diseases:
        limits, recos = [], []
        for rule in DISEASE_RULES:
            if rule.get("질환명") != disease or rule.get("_inactive"):
                continue
            action = rule.get("action")
            matched, basis, by_kw = match_rule(
                rule["rule_id"], rule.get("푸드코트 키워드 예시", ""),
                DISEASE_RULE_TAGS.get(rule["rule_id"], [])
                + [t.strip() for t in rule.get("food_tag", "").split("|") if t.strip()],   # 보완 규칙은 태그를 직접 가짐
                menu_row)
            if not matched:
                continue
            if action == "CONDITIONAL_LIMIT":
                # 검사·의료진 설정이 없으면 자동으로 제한하지 않는다(16_복합질환_충돌의 원칙)
                if not profile.ckd_lab_confirmed:
                    deferred.append(rule["rule_id"])
                    continue
                action = "LIMIT"
            level = rule.get("근거수준", "")
            entry = dict(source=rule["rule_id"], basis=basis, by_keyword=by_kw,
                         msg=f"[{disease}] {rule.get('서비스 문구 예시', '')}")
            if action == "LIMIT":
                limits.append(dict(entry, kind="LIMIT", weight=LIMIT_WEIGHT.get(level, -3)))
            elif action == "RECOMMEND":
                recos.append(dict(entry, kind="RECOMMEND", weight=RECOMMEND_WEIGHT.get(level, 2)))
        for group in (limits, recos):
            if group:
                best = _pick(group)
                score += best["weight"]
                reasons.append(best)

    # 3) 약물-식품 규칙: 약마다 대표 1개
    for drug_id in profile.drug_ids:
        drug = next((d for d in DRUG_DICT if d.get("drug_id") == drug_id), None)
        if not drug:
            continue
        hits = []
        for rule in DRUG_RULES:
            if rule.get("drug_id") != drug_id:
                continue
            rule_tags = [t.strip() for t in rule.get("food_tag", "").split("|") if t.strip()]
            rule_tags += DRUG_RULE_EXTRA_TAGS.get(rule["drug_rule_id"], [])
            matched, basis, by_kw = match_rule(
                rule["drug_rule_id"], rule.get("푸드코트 키워드 예시", ""), rule_tags, menu_row)
            if not matched:
                continue
            entry = dict(source=rule["drug_rule_id"], basis=basis, by_keyword=by_kw,
                         msg=f"[{drug.get('약물군', '복용약')}] {rule.get('서비스 문구 예시', '')}")
            if rule.get("action") == "CONTROL":
                # 먹지 말라는 규칙이 아니라 복용 시간 간격을 두라는 안내 → 감점하지 않는다
                hits.append(dict(entry, kind="DRUG_TIMING", weight=0))
            else:
                hits.append(dict(entry, kind="DRUG_LIMIT", weight=DRUG_WEIGHT.get(rule.get("근거수준", ""), -3)))
        if hits:
            best = _pick(hits)
            score += best["weight"]
            reasons.append(best)

    kinds = {r["kind"] for r in reasons}
    if "EXCLUDE" in kinds:
        tier = "EXCLUDED"
    elif kinds & {"LIMIT", "DRUG_LIMIT"}:
        tier = "CAUTION"
    elif "RECOMMEND" in kinds:
        # 확인되지 않은 조건부 제한이 걸려 있으면 권장하지 않고 보류한다
        tier = "HOLD" if deferred else "RECOMMENDED"
    else:
        tier = "NO_RULE"
    return dict(menu=menu_name(menu_row), menu_id=menu_row.get("menu_id"), tier=tier, score=score,
                reasons=reasons, deferred=deferred,
                general_notes=[GENERAL_NOTE[t] for t in tags if t in GENERAL_NOTE])


def recommend(profile):
    """전체 메뉴를 평가해 등급별 목록으로 돌려준다."""
    result = {"RECOMMENDED": [], "HOLD": [], "NO_RULE": [], "CAUTION": [], "EXCLUDED": []}
    for m in MENU:
        e = evaluate_menu(m, profile)
        result[e["tier"]].append(e)
    result["RECOMMENDED"].sort(key=lambda e: -e["score"])
    result["CAUTION"].sort(key=lambda e: e["score"])
    # 규칙 없음: 일반 특성 표시가 없는 메뉴를 앞에 둔다
    result["NO_RULE"].sort(key=lambda e: len(e["general_notes"]))
    return result


def print_report(profile):
    print("=" * 62)
    print("입력 프로필")
    print(f"  질환    : {', '.join(profile.diseases) or '-'}")
    drug_names = [next((d["약물군"] for d in DRUG_DICT if d["drug_id"] == x), x) for x in profile.drug_ids]
    print(f"  복용약  : {', '.join(drug_names) or '-'}")
    print(f"  알레르기: {', '.join(profile.allergen_tags) or '-'}")
    if profile.ckd_lab_confirmed:
        print("  (CKD 검사 확인됨 -> 칼륨·단백질·인 조건부 규칙 적용)")
    print("=" * 62)

    res = recommend(profile)

    print("\n[권장] 권장 규칙에 해당하고 제한 규칙에는 해당하지 않는 메뉴")
    if not res["RECOMMENDED"]:
        print("  (해당 메뉴 없음)")
    for e in res["RECOMMENDED"]:
        print(f"  O {e['menu']}  (점수 {e['score']})")
        for r in e["reasons"]:
            print(f"      · {r['msg']}  <{r['source']}, {r['basis']}>")

    if res["HOLD"]:
        print("\n[판단 보류] 권장 규칙에 해당하지만 확인이 필요한 조건부 규칙이 함께 걸린 메뉴")
        for e in res["HOLD"]:
            print(f"  ? {e['menu']}  (확인 필요: {', '.join(e['deferred'])})")
            for r in e["reasons"]:
                print(f"      · {r['msg']}  <{r['source']}, {r['basis']}>")

    print("\n[주의] 제한 규칙에 해당하는 메뉴 (영향이 큰 순)")
    if not res["CAUTION"]:
        print("  (해당 메뉴 없음)")
    for e in res["CAUTION"]:
        print(f"  ! {e['menu']}  (점수 {e['score']})")
        for r in e["reasons"]:
            mark = "+" if r["kind"] == "RECOMMEND" else "·"
            print(f"      {mark} {r['msg']}  <{r['source']}, {r['basis']}>")

    print("\n[규칙 없음] 입력한 질환·약 기준으로 해당하는 규칙이 없는 메뉴")
    print("  ※ 판단 근거가 없다는 뜻이며, 건강에 좋다는 뜻이 아닙니다.")
    for e in res["NO_RULE"]:
        note = f"  ({', '.join(e['general_notes'])})" if e["general_notes"] else ""
        print(f"  - {e['menu']}{note}")
        for r in e["reasons"]:   # 복용 시간 안내만 있는 경우
            print(f"      · {r['msg']}  <{r['source']}, {r['basis']}>")

    if res["EXCLUDED"]:
        print("\n[제외] 알레르기")
        for e in res["EXCLUDED"]:
            msg = next(r["msg"] for r in e["reasons"] if r["kind"] == "EXCLUDE")
            print(f"  X {e['menu']}: {msg}")

    deferred = sorted({rid for tier in res.values() for e in tier for rid in e["deferred"]})
    if deferred:
        print(f"\n[보류] 조건부 규칙 {', '.join(deferred)} 은 검사·의료진 확인이 없어 적용하지 않았습니다.")


if __name__ == "__main__":
    print("\n########## 케이스 1: 고혈압+당뇨 / 암로디핀 / 대두 알레르기 ##########")
    print_report(Profile(diseases=["고혈압", "당뇨병"], drug_ids=["RX002"], allergen_tags=["SOY"]))

    print("\n\n########## 케이스 2: 통풍+이상지질혈증 / 와파린 ##########")
    print_report(Profile(diseases=["통풍", "이상지질혈증"], drug_ids=["RX001"]))

    print("\n\n########## 케이스 3: 고혈압+CKD (검사 미확인 -> 조건부 규칙 보류) ##########")
    print_report(Profile(diseases=["고혈압", "만성콩팥병(CKD)"], ckd_lab_confirmed=False))
