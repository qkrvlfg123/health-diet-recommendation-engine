"""
엔진 회귀 테스트

실행:  python tests/test_engine.py      (추가 설치 없이 실행)
       pytest tests/                    (pytest가 있으면)

v2에서 실제로 발생했던 오류가 다시 생기지 않는지, 그리고 메뉴사전과 엔진이 어긋나지 않는지를 검사한다.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import consistency as c
import recommend as r

MENU = {r.menu_name(m): m for m in r.MENU}


def ev(name, **profile):
    return r.evaluate_menu(MENU[name], r.Profile(**profile))


def sources(e):
    return {x["source"] for x in e["reasons"]}


# ---------------------------------------------------------------- v2 오류의 재발 방지

def test_soup_does_not_get_sugar_message():
    """v2 버그: 규칙 설명의 '설탕'에 들어 있는 '탕' 때문에 모든 국물 메뉴에 설탕·시럽 문구가 붙었다."""
    for name in ["김치찌개", "설렁탕/곰탕", "라면", "냉면(물)", "짬뽕", "미역국"]:
        e = ev(name, diseases=["당뇨병"])
        assert "R007" not in sources(e), name
        assert not any("시럽" in x["msg"] for x in e["reasons"]), name


def test_soup_gets_sodium_rule_for_hypertension():
    for name in ["김치찌개", "설렁탕/곰탕", "라면", "냉면(물)", "짬뽕", "미역국"]:
        assert "R001" in sources(ev(name, diseases=["고혈압"])), name


def test_unmatched_menu_is_not_recommended():
    """v2 버그: 걸린 규칙이 없는 메뉴가 '안심하고 고르기 좋은 순' 최상위에 올랐다."""
    res = r.recommend(r.Profile(diseases=["고혈압", "당뇨병"], drug_ids=["RX002"], allergen_tags=["SOY"]))
    recommended = {e["menu"] for e in res["RECOMMENDED"]}
    for name in ["삼겹살구이", "곱창/막창", "후라이드치킨", "제육덮밥", "초밥"]:
        assert name not in recommended, name
    # 권장 등급은 반드시 권장 규칙에 근거해야 한다
    for e in res["RECOMMENDED"]:
        assert any(x["kind"] == "RECOMMEND" for x in e["reasons"]), e["menu"]
        assert not any(x["kind"] in ("LIMIT", "DRUG_LIMIT") for x in e["reasons"]), e["menu"]


def test_single_char_keyword_matches_only_word_ending():
    assert r.keyword_hit("국|탕", "미역국") == "국"
    assert r.keyword_hit("국|탕", "설렁탕/곰탕") == "탕"
    assert r.keyword_hit("국", "국수") is None        # '국'으로 시작하는 다른 음식
    assert r.keyword_hit("탕", "설탕시럽") is None
    assert r.keyword_hit("케이크", "치즈케이크") == "케이크"


# ---------------------------------------------------------------- 핵심 동작

def test_allergy_is_hard_exclusion():
    e = ev("된장찌개", allergen_tags=["SOY"])
    assert e["tier"] == "EXCLUDED"


def test_grapefruit_with_amlodipine_and_diabetes_double_penalty():
    e = ev("자몽에이드", diseases=["당뇨병"], drug_ids=["RX002"])
    assert {"R006", "DR003"} <= sources(e)
    assert e["score"] == r.BASE_SCORE - 5 - 6


def test_warfarin_rules_match():
    assert "DR001" in sources(ev("시금치나물", drug_ids=["RX001"]))
    # v2에서는 태그 이름 불일치로 누락되던 조합
    assert "DR002" in sources(ev("크랜베리주스", drug_ids=["RX001"]))


def test_control_rule_is_advice_not_penalty():
    """CONTROL(복용 시간 조절) 규칙은 제한이 아니므로 감점하지 않고 등급도 '주의'로 올리지 않는다."""
    e = ev("미역국", drug_ids=["RX007"])       # 갑상선약 + 미역(요오드)
    timing = [x for x in e["reasons"] if x["kind"] == "DRUG_TIMING"]
    assert timing and e["score"] == r.BASE_SCORE and e["tier"] == "NO_RULE"


def test_ckd_conditional_rules_deferred_without_lab():
    """CKD 칼륨 제한은 검사·의료진 확인이 있을 때만 적용한다(16_복합질환_충돌)."""
    off = ev("시금치나물", diseases=["만성콩팥병(CKD)"], ckd_lab_confirmed=False)
    on = ev("시금치나물", diseases=["만성콩팥병(CKD)"], ckd_lab_confirmed=True)
    assert "R029" not in sources(off) and "R029" in off["deferred"]
    assert "R029" in sources(on)


def test_deferred_conditional_rule_blocks_recommendation():
    """v2 버그: 고혈압+CKD(검사 미확인)에 칼륨이 많은 시금치나물을 채소 권장 규칙만으로 추천했다."""
    e = ev("시금치나물", diseases=["고혈압", "만성콩팥병(CKD)"], ckd_lab_confirmed=False)
    assert e["tier"] == "HOLD" and "R029" in e["deferred"]
    # CKD가 없으면 그대로 권장
    assert ev("시금치나물", diseases=["고혈압"])["tier"] == "RECOMMENDED"
    # 검사로 확인되면 제한 규칙이 적용되어 주의 등급
    assert ev("시금치나물", diseases=["고혈압", "만성콩팥병(CKD)"], ckd_lab_confirmed=True)["tier"] == "CAUTION"


def test_one_limit_per_disease():
    """같은 질환에서 여러 제한 규칙이 걸려도 감점과 사유는 1개만 반영한다."""
    e = ev("라면", diseases=["고혈압"])        # R001(국물), R004(가공식품) 둘 다 해당
    assert len([x for x in e["reasons"] if x["kind"] == "LIMIT"]) == 1
    assert e["score"] == r.BASE_SCORE - 5


def test_limit_and_recommend_both_shown():
    e = ev("비빔밥", diseases=["고혈압"])      # 양념(R002) 제한 + 채소(R005) 권장
    kinds = [x["kind"] for x in e["reasons"]]
    assert "LIMIT" in kinds and "RECOMMEND" in kinds and e["tier"] == "CAUTION"


# ---------------------------------------------------------------- 데이터 정합성

def test_rule_tag_map_refers_to_existing_rules_and_tags():
    rule_ids = {x["rule_id"] for x in r.DISEASE_RULES}
    drug_rule_ids = {x["drug_rule_id"] for x in r.DRUG_RULES}
    menu_tag_set = {t for m in r.MENU for t in r.menu_tags(m)}
    for rid, tags in r.DISEASE_RULE_TAGS.items():
        assert rid in rule_ids, rid
        for t in tags:
            assert t in menu_tag_set, (rid, t)
    for rid, tags in r.DRUG_RULE_EXTRA_TAGS.items():
        assert rid in drug_rule_ids, rid
        for t in tags:
            assert t in menu_tag_set, (rid, t)


def test_dictionary_and_engine_agree_except_known_gaps():
    """메뉴사전이 '관련 있다'고 적은 (메뉴, 질환/약) 쌍은 엔진에서도 규칙이 걸려야 한다.
    걸리지 않는 쌍은 이유와 함께 KNOWN_*_GAPS에 기록된 것만 허용한다."""
    res = c.check()
    assert set(res["disease_gaps"]) == set(c.KNOWN_DISEASE_GAPS), res["disease_gaps"]
    assert set(res["drug_gaps"]) == set(c.KNOWN_DRUG_GAPS), res["drug_gaps"]


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as err:
            failed += 1
            print(f"FAIL  {name}: {err}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
