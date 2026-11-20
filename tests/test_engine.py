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
    # 당뇨 가당음료 HIGH(-5) + 암로디핀–자몽 MEDIUM(-3).
    # 암로디핀은 자몽의 영향이 작다는 교차시험 결과(E001)에 따라 원본의 HIGH에서 MEDIUM으로 조정했다.
    assert e["score"] == r.BASE_SCORE - 5 - 3


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


# ---------------------------------------------------------------- 문헌 근거 보완 규칙

def test_supplement_rules_fill_former_gaps():
    """v3에서 '대응 규칙 없음'으로 남겼던 조합이 보완 규칙으로 잡히는지."""
    assert "R033" in sources(ev("후라이드치킨", diseases=["당뇨병"]))          # 튀김–당뇨 (E006)
    assert "R034" in sources(ev("맥주", diseases=["이상지질혈증"]))            # 알코올–중성지방 (E007)
    assert "R035" in sources(ev("치즈버거세트", diseases=["이상지질혈증"]))    # 포화지방 (E008)
    assert "DR018" in sources(ev("맥주", drug_ids=["RX008"]))                  # 알코올–당뇨약 (E011)
    assert "DR019" in sources(ev("맥주", drug_ids=["RX017"]))                  # 알코올–통풍 (E010)
    assert "DR020" in sources(ev("자몽에이드", drug_ids=["RX017"]))            # 자몽–콜히친 (E012)


def test_v32_rules_from_literature():
    assert "R036" in sources(ev("맥주", diseases=["고혈압"]))                  # 알코올–혈압 (E017)
    assert "R037" in sources(ev("김치찌개", diseases=["심혈관질환"]))          # 나트륨–심혈관 (E020)
    e = ev("시금치나물", diseases=["심혈관질환"])                              # 채소 권장 (E027)
    assert "R039" in sources(e) and e["tier"] == "RECOMMENDED"
    assert "DR022" in sources(ev("아메리카노", drug_ids=["RX009"]))            # 시프로플록사신–카페인 (E024)
    assert "DR023" in sources(ev("맥주", drug_ids=["RX005"]))                  # MAO억제제–생맥주 (E025, E026)


def test_bisphosphonate_coffee_is_timing_advice():
    """골다공증약–커피는 흡수 문제라 복용 시간 안내(E021). 감점하지 않는다."""
    e = ev("아메리카노", drug_ids=["RX010"])
    assert [x["kind"] for x in e["reasons"]] == ["DRUG_TIMING"] and e["score"] == r.BASE_SCORE


def test_colchicine_grapefruit_does_not_apply_to_urate_lowering_drugs():
    """자몽 상호작용은 콜히친에만 해당하므로 약물군을 분리했다(E012)."""
    assert "DR020" in sources(ev("자몽에이드", drug_ids=["RX017"]))
    assert not ev("자몽에이드", drug_ids=["RX018"])["reasons"]
    # 알코올 제한은 두 약물군 모두 해당
    assert "DR019" in sources(ev("맥주", drug_ids=["RX017"])) and "DR024" in sources(ev("맥주", drug_ids=["RX018"]))


def test_evidence_level_follows_study_design():
    """근거수준은 연구설계로만 정한다: 관찰 연구·증례·전문가 합의는 HIGH가 될 수 없다."""
    weak = ("코호트", "관찰", "증례", "종설", "약동학", "전문가 합의", "근거등급 E", "조건부")
    s = r.SUPPLEMENT
    for rule in s["disease_rules_add"] + s["drug_rules_add"]:
        first = rule["source_id"].split("|")[0]
        design = r.EVIDENCE[first]["연구설계"]
        if any(w in design for w in weak):
            assert rule["근거수준"] == "MEDIUM", (rule.get("rule_id") or rule.get("drug_rule_id"), design)


def test_levodopa_protein_is_timing_advice():
    """파킨슨약–고단백 식사는 제한이 아니라 복용 시간 조절(E013). 감점하지 않는다."""
    e = ev("삼겹살구이", drug_ids=["RX006"])
    assert [x["kind"] for x in e["reasons"]] == ["DRUG_TIMING"] and e["score"] == r.BASE_SCORE


def test_no_rule_created_without_evidence():
    """미역국–통풍: 문헌 검토 결과 근거가 없어 규칙을 만들지 않았다(E009)."""
    assert not any(x["kind"] == "LIMIT" for x in ev("미역국", diseases=["통풍"])["reasons"])


def test_grape_is_not_grapefruit():
    """원본 DR003 키워드의 '포도주스'·'레몬에이드'는 자몽이 아니므로 제거했다."""
    rule = next(x for x in r.DRUG_RULES if x["drug_rule_id"] == "DR003")
    assert "포도" not in rule["푸드코트 키워드 예시"] and "레몬" not in rule["푸드코트 키워드 예시"]
    assert r.keyword_hit(rule["푸드코트 키워드 예시"], "포도주스") is None


def test_every_supplement_item_cites_existing_evidence():
    """보완한 규칙·수정 사항은 모두 evidence_sources.json의 문헌을 가리켜야 한다."""
    s = r.SUPPLEMENT
    items = s["disease_rules_add"] + s["drug_rules_add"] + list(s["drug_rules_override"].values())
    for it in items:
        ids = [i for i in it["source_id"].split("|") if i.startswith("E")]
        assert ids, it
        for i in ids:
            assert i in r.EVIDENCE, i
    for it in s["rules_not_created"]:
        assert it["이유"] and all(i in r.EVIDENCE for i in it["source_id"].split("|") if i)


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
