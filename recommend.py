"""
KioBridge 건강 추천 엔진 (규칙 기반 필터링 데모) — v2 (정밀 매칭)
=================================================================

사용자 프로필(질환·복용약·알레르기)을 입력하면, 메뉴 사전을 대상으로
  1) 하드 필터 : 알레르기 등 절대 제외
  2) 건강 필터 : 질환·약물-식품 상호작용 규칙에 걸리는 메뉴를 감점/가점
  3) 추천 + 이유 : 남은 메뉴를 점수순으로 정렬하고, 왜 주의/추천인지 설명

v2에서 개선한 점
----------------
* 질환 규칙을 '첫 규칙'이 아니라 **푸드코트 키워드 + food_tag 하이브리드로
  정확히 매칭**한다. 이제 국물 메뉴엔 나트륨 사유가, 음료엔 당 사유가 붙는다.
* RECOMMEND 규칙(채소·생선·통곡물 등)을 반영해 **가점**한다.
* CKD 등 CONDITIONAL_LIMIT 규칙은 검사·의료진 설정이 없으면 **자동 감점하지 않고
  보류**한다(16_복합질환_충돌의 '조건 미확인 시 자동 제한 보류' 원칙).

이 스크립트는 foodcourt_dataset(22시트) 중
15_메뉴사전 / 02_질환_식품규칙 / 08_약물_식품규칙 / 14_약물사전
을 JSON으로 변환한 data/*.json 을 근거로 동작한다.

* 의료기기가 아니며, 진단·처방을 하지 않는다. 식이 가이드라인 기반의
  '주의 안내'만 제공한다.
"""

import json
import os
from dataclasses import dataclass, field

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _load(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


MENU = _load("menu_dictionary.json")
DISEASE_RULES = _load("disease_food_rules.json")
DRUG_RULES = _load("drug_food_rules.json")
DRUG_DICT = _load("drug_dictionary.json")

LIMIT_WEIGHT = {"HIGH": -5, "MEDIUM": -3, "": -3}
RECOMMEND_WEIGHT = {"HIGH": 3, "MEDIUM": 2, "": 2}
DRUG_WEIGHT = {"HIGH": -6, "MEDIUM": -3, "": -3}

FOODTAG_HINTS = {
    "국물": "SOUP", "찌개": "SOUP", "탕": "SOUP", "면 국물": "SOUP",
    "나트륨": "HIGH_SODIUM_POSSIBLE", "고나트륨": "HIGH_SODIUM_POSSIBLE",
    "가공육": "PROCESSED", "가공식품": "PROCESSED",
    "튀김": "FRIED",
    "적색육": "RED_MEAT", "붉은 고기": "RED_MEAT",
    "포화": "SAT_FAT_POSSIBLE", "고지방": "SAT_FAT_POSSIBLE",
    "크림": "CREAM_OR_SAUCE", "치즈": "CHEESE",
    "가당음료": "SUGAR_SWEETENED_BEVERAGE", "에이드": "SUGAR_SWEETENED_BEVERAGE",
    "탄산": "SUGAR_SWEETENED_BEVERAGE", "과일음료": "SUGAR_SWEETENED_BEVERAGE",
    "당류": "ADDED_SUGAR", "설탕": "ADDED_SUGAR", "시럽": "ADDED_SUGAR",
    "정제 곡물": "REFINED_CARB", "정제탄수": "REFINED_CARB",
    "내장": "HIGH_PURINE", "해산물": "SEAFOOD", "해물": "SEAFOOD",
    "채소": "VEGETABLE", "샐러드": "VEGETABLE", "나물": "VEGETABLE",
    "생선": "SEAFOOD", "통곡물": "VEGETABLE",
}


@dataclass
class Profile:
    """가상·합성 프로필 (실제 개인정보 사용 금지)"""
    diseases: list = field(default_factory=list)
    drug_ids: list = field(default_factory=list)
    allergen_tags: list = field(default_factory=list)
    ckd_lab_confirmed: bool = False


def _tags(menu_row):
    return [t.strip() for t in menu_row.get("food_tag", "").split("|") if t.strip()]


def _menu_name(menu_row):
    return menu_row.get("메뉴명", "")


def _rule_matches_menu(rule, menu_row):
    """질환/식품 규칙이 이 메뉴에 실제로 걸리는지 판정.
    1순위: 푸드코트 키워드가 메뉴명에 포함되는가
    2순위: 규칙의 '식품군/특성'이 가리키는 food_tag가 메뉴 태그에 있는가
    """
    name = _menu_name(menu_row)
    tags = _tags(menu_row)

    for kw in rule.get("푸드코트 키워드 예시", "").split("|"):
        kw = kw.strip()
        if not kw:
            continue
        # 키워드가 메뉴명에 포함되면 매칭.
        # 역방향(메뉴명이 키워드에 포함)은 메뉴명이 2글자 이상일 때만 허용해
        # '약과'가 '어묵' 같은 키워드에 우연히 걸리는 오작동을 줄인다.
        if kw in name:
            return True, f"메뉴명 '{name}' ~ 키워드 '{kw}'"
        if len(name) >= 2 and name in kw:
            return True, f"메뉴명 '{name}' ~ 키워드 '{kw}'"

    spec = rule.get("식품군/특성", "") + rule.get("근거 기반 이유", "")
    for hint, tag in FOODTAG_HINTS.items():
        if hint in spec and tag in tags:
            return True, f"태그 '{tag}'"

    return False, ""


def evaluate_menu(menu_row, profile):
    reasons = []
    hard_excluded = False
    score = 10
    tags = _tags(menu_row)

    # 1) 하드 필터: 알레르기
    for allergen in profile.allergen_tags:
        if allergen in tags:
            hard_excluded = True
            reasons.append(("HARD_EXCLUDE",
                            f"알레르기({allergen}) 성분이 포함되어 후보에서 제외했어요."))

    # 2) 건강 필터: 질환-식품 규칙
    #    같은 질환에서 여러 규칙이 걸려도 감점은 질환당 1회(가장 무거운 것)로 캡.
    #    사유도 질환당 대표 1개만 남겨 과잉 경고를 막는다.
    for disease in profile.diseases:
        best_limit = None      # (weight, msg)
        best_reco = None       # (weight, msg)
        for rule in DISEASE_RULES:
            if rule.get("질환명") != disease:
                continue
            action = rule.get("action")

            if action == "CONDITIONAL_LIMIT":
                if not profile.ckd_lab_confirmed:
                    continue
                action = "LIMIT"

            matched, basis = _rule_matches_menu(rule, menu_row)
            if not matched:
                continue

            level = rule.get("근거수준", "")
            if action == "LIMIT":
                w = LIMIT_WEIGHT.get(level, -3)
                msg = f"[{disease}] {rule.get('서비스 문구 예시','주의가 필요한 메뉴예요.')}"
                if best_limit is None or w < best_limit[0]:
                    best_limit = (w, msg)
            elif action == "RECOMMEND":
                w = RECOMMEND_WEIGHT.get(level, 2)
                msg = f"[{disease}] {rule.get('서비스 문구 예시','도움이 되는 메뉴예요.')}"
                if best_reco is None or w > best_reco[0]:
                    best_reco = (w, msg)

        # LIMIT과 RECOMMEND가 동시에 걸리면 LIMIT을 우선(안전측)
        if best_limit:
            score += best_limit[0]
            reasons.append(("HEALTH_LIMIT", best_limit[1]))
        elif best_reco:
            score += best_reco[0]
            reasons.append(("HEALTH_RECOMMEND", best_reco[1]))

    # 3) 건강 필터: 약물-식품 규칙 (food_tag 정확 매칭, 약당 1회 캡)
    for drug_id in profile.drug_ids:
        drug = next((d for d in DRUG_DICT if d.get("drug_id") == drug_id), None)
        if not drug:
            continue
        best = None  # (weight, msg)
        for rule in DRUG_RULES:
            if rule.get("drug_id") != drug_id:
                continue
            rule_tags = [t.strip() for t in rule.get("food_tag", "").split("|") if t.strip()]
            if any(t in tags for t in rule_tags):
                level = rule.get("근거수준", "")
                w = DRUG_WEIGHT.get(level, -3)
                msg = (f"[{drug.get('약물군','복용약')}] "
                       f"{rule.get('서비스 문구 예시','약과 함께 주의가 필요해요.')}")
                if best is None or w < best[0]:
                    best = (w, msg)
        if best:
            score += best[0]
            reasons.append(("DRUG_INTERACTION", best[1]))

    return hard_excluded, score, reasons


def recommend(profile, top_n=5):
    scored, excluded = [], []
    for m in MENU:
        hard, score, reasons = evaluate_menu(m, profile)
        entry = {"menu": _menu_name(m), "menu_id": m.get("menu_id"),
                 "score": score, "reasons": reasons}
        (excluded if hard else scored).append(entry)
    scored.sort(key=lambda e: e["score"], reverse=True)
    return scored[:top_n], scored[top_n:], excluded


def print_report(profile):
    print("=" * 62)
    print("입력 프로필")
    print(f"  질환    : {', '.join(profile.diseases) or '-'}")
    drug_names = [next((d['약물군'] for d in DRUG_DICT if d['drug_id'] == x), x)
                  for x in profile.drug_ids]
    print(f"  복용약  : {', '.join(drug_names) or '-'}")
    print(f"  알레르기: {', '.join(profile.allergen_tags) or '-'}")
    if profile.ckd_lab_confirmed:
        print("  (CKD 검사 확인됨 -> 칼륨·단백질 제한 활성화)")
    print("=" * 62)

    top, rest, excluded = recommend(profile)

    print("\n[추천] 안심하고 고르기 좋은 순")
    for e in top:
        note = "  <- 걸리는 규칙 없음" if not e["reasons"] else ""
        print(f"  O {e['menu']}  (점수 {e['score']}){note}")
        for _, msg in e["reasons"]:
            print(f"      · {msg}")

    flagged = [e for e in (top + rest) if e["score"] < 10]
    if flagged:
        print("\n[주의] 건강 필터가 감점한 항목 (낮은 점수 순)")
        for e in sorted(flagged, key=lambda x: x["score"]):
            print(f"  ! {e['menu']}  (점수 {e['score']})")
            for _, msg in e["reasons"]:
                print(f"      · {msg}")

    if excluded:
        print("\n[제외] 하드 필터")
        for e in excluded:
            hard_msgs = [msg for k, msg in e["reasons"] if k == "HARD_EXCLUDE"]
            print(f"  X {e['menu']}: {hard_msgs[0] if hard_msgs else ''}")


if __name__ == "__main__":
    print("\n########## 케이스 1: 고혈압+당뇨 / 암로디핀 / 대두 알레르기 ##########")
    print_report(Profile(
        diseases=["고혈압", "당뇨병"],
        drug_ids=["RX002"],
        allergen_tags=["SOY"],
    ))

    print("\n\n########## 케이스 2: 통풍+이상지질혈증 / 와파린 ##########")
    print_report(Profile(
        diseases=["통풍", "이상지질혈증"],
        drug_ids=["RX001"],
    ))

    print("\n\n########## 케이스 3: 고혈압+CKD (검사 미확인 -> 칼륨 제한 보류) ##########")
    print_report(Profile(
        diseases=["고혈압", "만성콩팥병(CKD)"],
        ckd_lab_confirmed=False,
    ))
