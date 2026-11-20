# 원본 규칙의 문헌 검토 결과

원본 데이터셋의 규칙 49개(질환 32개, 약물 17개)를 문헌으로 검토한 결과입니다.
이 파일은 `python review_report.py`로 `data/rule_review.json`에서 생성합니다.

- 판정 집계: 상향 2개, 유지 37개, 적용 중지 1개, 하향 9개
- 근거수준 기준: HIGH = 무작위 시험과 그 메타분석, 허가사항·규제기관 규정, 지침의 강한 권고 / MEDIUM = 관찰 연구, 조건부 권고, 전문가 합의, 소규모 약동학 연구, 증례 보고, 종설
- 등급을 바꾸거나 적용을 중지한 규칙에는 반드시 근거 문헌이 있습니다. "적용 중지"는 문헌이 규칙 자체를 뒷받침하지 않아 엔진에서 적용하지 않는 규칙입니다(삭제하지 않고 남김).
- 문헌은 PubMed 초록과 검색 요약으로 확인했습니다. 문헌별 확인 범위는 `data/evidence_sources.json`의 `확인수준`에 있습니다.

## 질환–식품 규칙 (32개)

| 규칙 | 대상 | 원본 | 검토 | 판정 | 근거 문헌 | 검토 내용 |
|---|---|---|---|---|---|---|
| R001 | 고혈압 – 국물·찌개·탕·면 국물 | HIGH | HIGH | 유지 | E028 He FJ, Li J, MacGregor GA | 소금 감량 무작위 시험 메타분석에서 고혈압 환자 수축기 -5.39 mmHg. 근거는 나트륨 감량 전반에 대한 것이고 국물 음식을 따로 본 것은 아님 |
| R002 | 고혈압 – 장류·짠 소스가 많은 메뉴 | HIGH | HIGH | 유지 | E028 He FJ, Li J, MacGregor GA | R001과 같은 근거. 장류·소스의 실제 사용량은 메뉴명으로 알 수 없다는 원본의 예외 조건이 타당 |
| R003 | 고혈압 – 염장·절임 식품 | HIGH | HIGH | 유지 | E028 He FJ, Li J, MacGregor GA | R001과 같은 근거 |
| R004 | 고혈압 – 가공육·가공식품 | HIGH | HIGH | 유지 | E028 He FJ, Li J, MacGregor GA<br>E042 Lajous M, Bijon A, Fagherazzi G, et al | 나트륨 근거(E028)로 HIGH 유지. 가공육 자체는 코호트에서 고혈압 발생 HR 1.17(E042) |
| R005 | 고혈압 – 채소·과일 중심 반찬 | MEDIUM | **HIGH** | 상향 | E029 Appel LJ, Moore TJ, Obarzanek E, et al | DASH 무작위 급식 시험에서 과일·채소 식단이 수축기 2.8 mmHg 낮춤. 무작위 시험 근거이므로 HIGH. 효과 크기는 작음(11.4 mmHg는 저지방 유제품을 더한 복합 식단·고혈압 환자의 수치) |
| R006 | 당뇨병 – 가당 에이드·탄산·과일음료 | HIGH | HIGH | 유지 | E053 American Diabetes Association<br>E030 Malik VS, Popkin BM, Bray GA, et al | ADA 2025년판이 감미 음료 대신 물을 강하게 권고. 권고의 근거등급은 확인하지 못함. 관찰 연구에서는 발생 위험 26% 증가(E030) |
| R007 | 당뇨병 – 설탕·시럽이 많이 들어가는 커피/차 | HIGH | HIGH | 유지 | E053 American Diabetes Association | R006과 같은 권고(가당 커피·차도 감미 음료). 커피·차를 따로 다룬 근거는 확인하지 못함 |
| R008 | 당뇨병 – 디저트·당류 많은 간식 | HIGH | HIGH | 유지 | E055 World Health Organization<br>E053 American Diabetes Association | WHO가 유리당 섭취를 총 에너지의 10% 미만으로 줄일 것을 강하게 권고. ADA 2025년판도 감미 음료 대신 물을 강하게 권고. WHO 권고는 일반 인구 대상이고 근거의 질은 중등도 |
| R009 | 당뇨병 – 정제 곡물 중심 메뉴 | MEDIUM | MEDIUM | 유지 | E031 Hu EA, Pan A, Malik V, Sun Q | 흰쌀밥 하루 1회 증가당 당뇨병 발생 RR 1.11. 코호트 메타분석이므로 MEDIUM이 타당. '금지가 아니라 양이 중요'라는 원본 조건과도 맞음 |
| R010 | 당뇨병 – 탄수화물 중복 조합 | MEDIUM | MEDIUM | 유지 | E056 Evert AB, Dennison M, Gardner CD, et al | ADA 합의 보고서가 전체 탄수화물 섭취를 줄이는 것이 혈당 개선에 가장 근거가 많다고 기술. 탄수화물 중복 조합을 직접 본 시험은 아니므로 MEDIUM이 타당. 엔진은 메뉴 하나 단위로 판정하므로 이 규칙을 적용하지 않음 |
| R011 | 당뇨병 – 식이섬유 풍부한 식품 | HIGH | HIGH | 유지 | E032 Reynolds AN, Akerman AP, Mann J | 무작위 시험 42개 메타분석에서 식이섬유 증가가 HbA1c를 약 0.2%p 낮춤. 효과는 작고 이질성이 큼 |
| R012 | 이상지질혈증 – 기름진 적색육·고지방 육류 | HIGH | HIGH | 유지 | E008 Sacks FM, Lichtenstein AH, Wu JHY, et al | 포화지방을 불포화지방으로 대체한 무작위 시험 종합 |
| R013 | 이상지질혈증 – 가공육 | HIGH | **MEDIUM** | 하향 | E019 Micha R, Wallace SK, Mozaffarian D | 가공육의 근거는 관찰 연구 메타분석(관상동맥질환 RR 1.42)이고 혈중 지질을 직접 본 시험 근거는 찾지 못함 |
| R014 | 이상지질혈증 – 튀김류 | HIGH | **MEDIUM** | 하향 | E050 Qin P, Zhang M, Han M, et al | 튀김의 근거는 관찰 연구 메타분석(심혈관 사건 RR 1.28, 이질성 큼). 원본의 조건(조리유 종류에 따라 차이)과도 맞음 |
| R015 | 이상지질혈증 – 버터·크림·치즈가 많은 메뉴 | HIGH | HIGH | 유지 | E008 Sacks FM, Lichtenstein AH, Wu JHY, et al | R012와 같은 근거 |
| R016 | 이상지질혈증 – 제과·페이스트리 | MEDIUM | MEDIUM | 유지 | E033 Mozaffarian D, Katan MB, Ascherio A, Sta | 제과류의 트랜스지방 근거는 코호트 종합(에너지 2%당 관상동맥질환 RR 1.23). 수치는 2차 요약에서 확인 |
| R017 | 이상지질혈증 – 생선·식물성 단백질 | HIGH | HIGH | 유지 | E041 Blanco Mejia S, Messina M, Li SS, et al | 콩 단백질은 무작위 시험 메타분석에서 LDL 약 3~4% 감소. 효과가 작고 저자 이해상충이 있음. 생선에 대한 근거는 이 작업에서 확인하지 않음 |
| R018 | 이상지질혈증 – 통곡물·채소·콩류 | HIGH | HIGH | 유지 | E034 Brown L, Rosner B, Willett WW, Sacks FM | 대조 시험 67개 메타분석에서 수용성 식이섬유가 LDL을 낮춤. 실제 섭취 범위에서는 효과가 작음 |
| R019 | 골다공증 – 칼슘 공급 식품 | HIGH | HIGH | 유지 | E060 Iuliano S, Poon S, Robbins J, et al<br>E035 Bolland MJ, Leung W, Tai V, et al | 노인요양시설 군집 무작위 시험에서 유제품(우유·요거트·치즈) 추가 제공이 전체 골절 33%, 고관절 골절 46% 감소(E060). 그 이전의 체계적 문헌고찰은 식이 칼슘과 골절의 관련을 확인하지 못했음(E035). 근거는 유제품에 대한 것이고 같은 규칙의 미역·녹색채소에는 직접 적용되지 않음. 기저 섭취량이 낮은 시설 거주 노인 대상 결과 |
| R020 | 골다공증 – 비타민 D 공급 식품 | HIGH | **MEDIUM** | 적용 중지 | E052 Bolland MJ, Grey A, Avenell A | 비타민 D 보충은 무작위 시험 81개 메타분석에서 골절·낙상·골밀도에 효과가 없었음. 식품(고등어·연어·달걀·버섯)으로 섭취한 경우의 골절 예방 근거는 찾지 못함. 문헌이 권장 규칙을 뒷받침하지 않아 엔진에서 적용하지 않음. 생선 자체는 다른 규칙(R017)에서 권장 |
| R021 | 골다공증 – 과도한 음주 | MEDIUM | MEDIUM | 유지 | E036 Kanis JA, Johansson H, Johnell O, et al | 코호트 종합에서 하루 2단위 초과 시 골다공증성 골절 RR 1.38. '과도한 음주'로 한정한 원본 조건과 맞음 |
| R022 | 통풍 – 내장류 | HIGH | **MEDIUM** | 하향 | E009 Choi HK, Atkinson K, Karlson EW, Willett<br>E010 FitzGerald JD, Dalbeth N, Mikuls T, et a | 내장류를 따로 본 근거는 찾지 못함. 육류 전체는 코호트에서 RR 1.41이고, ACR 지침의 퓨린 제한은 조건부 권고(근거 확실성 낮음) |
| R023 | 통풍 – 붉은 고기 과다 | MEDIUM | MEDIUM | 유지 | E009 Choi HK, Atkinson K, Karlson EW, Willett | 코호트에서 육류 최고 5분위 RR 1.41 |
| R024 | 통풍 – 일부 해산물·멸치/정어리류 | MEDIUM | MEDIUM | 유지 | E009 Choi HK, Atkinson K, Karlson EW, Willett | 코호트에서 해산물 RR 1.51. 해산물 종류별 차이가 크다는 원본 조건이 타당 |
| R025 | 통풍 – 알코올 특히 맥주 | HIGH | **MEDIUM** | 하향 | E037 Choi HK, Atkinson K, Karlson EW, Willett<br>E010 FitzGerald JD, Dalbeth N, Mikuls T, et a | 코호트에서 맥주 하루 1회당 RR 1.49로 연관은 뚜렷하지만 관찰 연구이고, ACR 지침의 알코올 제한은 조건부 권고(근거 확실성 낮음) |
| R026 | 통풍 – 고과당·가당음료 | HIGH | **MEDIUM** | 하향 | E038 Choi HK, Curhan G<br>E010 FitzGerald JD, Dalbeth N, Mikuls T, et a | 코호트에서 가당 탄산음료 하루 2회 이상 RR 1.85. 관찰 연구이고 ACR 지침의 고과당시럽 제한은 근거 확실성 '매우 낮음' |
| R027 | 통풍 – 저지방 유제품 | MEDIUM | MEDIUM | 유지 | E009 Choi HK, Atkinson K, Karlson EW, Willett | 코호트에서 유제품 최고 5분위 RR 0.56 |
| R028 | 만성콩팥병(CKD) – 고나트륨 음식 | HIGH | HIGH | 유지 | E039 McMahon EJ, Campbell KL, Bauer JD, et al | CKD 환자 대상 무작위 시험 종합에서 소금 감량이 수축기 -8.75 mmHg. 단기 시험뿐이라 장기 결과 근거는 없음 |
| R029 | 만성콩팥병(CKD) – 고칼륨 식품/첨가물 | HIGH | **MEDIUM** | 하향 | E040 Ikizler TA, Burrowes JD, Byham-Gray LD,  | KDOQI 지침의 칼륨 권고는 고칼륨혈증이 교정되지 않을 때 식이 제한을 권하는 수준이고 권고 등급을 확인하지 못함. 원본의 '자동 제한 금지' 조건은 타당 |
| R030 | 만성콩팥병(CKD) – 과도한 고단백 식사 | HIGH | HIGH | 유지 | E040 Ikizler TA, Burrowes JD, Byham-Gray LD,  | KDOQI 지침이 CKD 3~5기 단백질 제한을 1A로 권고(2차 문헌으로 확인). 개별화가 필요하다는 원본 조건과 맞음 |
| R031 | 만성콩팥병(CKD) – 인(Phosphorus)·가공식품 첨가물 | MEDIUM | MEDIUM | 유지 | E051 Kalantar-Zadeh K, Gutekunst L, Mehrotra  | 인 첨가물의 흡수율이 높다는 종설 근거 |
| R032 | 심혈관질환 – 고당·고칼로리·포화/트랜스지방 메뉴 | HIGH | HIGH | 유지 | E008 Sacks FM, Lichtenstein AH, Wu JHY, et al<br>E050 Qin P, Zhang M, Han M, et al<br>E033 Mozaffarian D, Katan MB, Ascherio A, Sta | 포화지방은 무작위 시험 근거(E008)로 HIGH 유지. 같은 규칙의 튀김(E050)·트랜스지방(E033)은 관찰 연구 근거 |

## 약물–식품 규칙 (17개)

| 규칙 | 대상 | 원본 | 검토 | 판정 | 근거 문헌 | 검토 내용 |
|---|---|---|---|---|---|---|
| DR001 | 항응고제(와파린) – 비타민K 많은 녹색채소 | HIGH | **MEDIUM** | 하향 | E043 Violi F, Lip GY, Pignatelli P, Pastori D | 체계적 문헌고찰에서 근거가 엇갈렸고 비타민 K 제한은 타당한 전략이 아니라고 결론. '금지가 아니라 일정량 유지'라는 원본 문구는 문헌과 일치하므로 문구는 그대로 두고 근거수준만 조정 |
| DR002 | 항응고제(와파린) – 혈액 묽게 하는 건강식품·주스 | HIGH | **MEDIUM** | 하향 | E004 Food and herbal interactions with oral a<br>E005 Interaction between warfarin and cranber | v3.1에서 검토. 크랜베리주스는 무작위 시험에서 영향이 없었고 우려는 증례 보고에 근거. 같은 규칙의 홍삼·오메가3는 검토하지 않음 |
| DR003 | 혈압약(칼슘채널차단제/암로디핀) – 자몽·시트러스 | HIGH | **MEDIUM** | 하향 | E001 Vincent J, Harris SI, Foulds G, et al<br>E002 Josefsson M, Zackrisson AL, Ahlner J<br>E003 Bailey DG, Dresser G, Arnold JMO | v3.1에서 검토. 암로디핀은 교차시험에서 자몽의 영향이 없거나 작았음. 키워드의 포도주스·레몬에이드 제거 |
| DR004 | 혈압약(이뇨제·ARB) – 고칼륨 식품 | MEDIUM | MEDIUM | 유지 | E014 ACE inhibitors and ARBs: Managing potass<br>E015 Tools for Practice #163: Blood pressure  | v3.1에서 검토. 칼륨이 오르는 것은 ARB이고 티아지드는 반대. 문구와 조건을 ARB로 한정 |
| DR005 | 고지혈증약(스타틴) – 자몽·시트러스 | HIGH | HIGH | 유지 | E016 U<br>E003 Bailey DG, Dresser G, Arnold JMO | v3.2에서 검토. FDA가 심바스타틴·아토르바스타틴을 명시. 문구를 성분으로 한정 |
| DR006 | 항우울제(MAO억제제)·일부 파킨슨약 – 티라민 많은 발효·숙성·훈제식품 | HIGH | HIGH | 유지 | E057 NARDIL (phenelzine sulfate) tablets — US<br>E054 Gillman PK | 미국 허가사항이 티라민이 많은 식품 섭취 시 고혈압 위기를 경고(E057). 최근 종설(E054)은 숙성 치즈 상당수가 티라민이 적어 위험이 과대평가됐다고 보므로, 실제 위험은 식품의 티라민 함량과 섭취량에 따라 다름 |
| DR007 | 파킨슨약(레보도파) – 고단백 식사(약효 소진 시) | MEDIUM | MEDIUM | 유지 | E013 Cereda E, Barichella M, Pedrolli C, Pezz | 체계적 문헌고찰에서 단백질 재분배 식이가 운동 기능을 개선. 연구 이질성이 커서 MEDIUM이 타당. 제한이 아니라 시간 조절이라는 원본 조건과 일치 |
| DR008 | 갑상선약(레보티록신) – 칼슘·철분·대두·탄닌 | MEDIUM | MEDIUM | 유지 | E022 Benvenga S, Bartolone L, Pappalardo MA, <br>E023 Singh N, Singh PN, Hershman JM | v3.2에서 검토. 커피·칼슘의 흡수 저하는 소규모 연구로 확인 |
| DR009 | 당뇨약(메트포르민 등) – 혈당강하 겹치는 건강식품·고당 | MEDIUM | MEDIUM | 유지 | E049 Shishtar E, Sievenpiper JL, Djedovic V,  | 인삼은 무작위 시험 메타분석에서 공복혈당을 0.31 mmol/L 낮춤(작은 효과). 당뇨약과 병용 시 저혈당을 본 근거는 아님. 규칙의 태그 ADDED_SUGAR는 상호작용이 아니므로 제거(아래 수정 사항) |
| DR010 | 항생제(테트라사이클린·퀴놀론) – 유제품·칼슘 | MEDIUM | MEDIUM | 유지 | E044 Neuvonen PJ, Kivistö KT, Lehto P | 교차시험에서 우유·요거트가 시프로플록사신 흡수를 30~36% 낮춤. 대상자 7명의 소규모 연구라 MEDIUM 유지. 테트라사이클린계는 이 작업에서 확인하지 않음 |
| DR011 | 골다공증약(비스포스포네이트) – 칼슘·철분·미네랄·유제품 | MEDIUM | **HIGH** | 상향 | E021 Gertz BJ, Holland SD, Kline WF, et al | 알렌드로네이트는 임상시험에서 커피·주스와 복용 시 흡수 약 60% 감소. 복용 시간 안내(CONTROL)라 점수에는 영향 없음 |
| DR012 | 천식약(테오필린) – 카페인·고지방 | MEDIUM | MEDIUM | 유지 | E045 Jonkman JH, Sollie FA, Sauter R, Steinij | 교차시험(8명)에서 카페인이 테오필린 청소율을 29% 낮춤. 소규모 약동학 연구 |
| DR013 | 소염진통제(NSAIDs/이부프로펜·아스피린) – 알코올·자극적 음식 | HIGH | HIGH | 유지 | E046 U<br>E047 Kaufman DW, Kelly JP, Wiholm BE, et al | FDA가 일반의약품 진통제에 알코올 경고를 의무화(위장관 출혈). 환자-대조군 연구에서도 음주량에 따라 출혈 위험 증가 |
| DR014 | 해열진통제(아세트아미노펜/타이레놀) – 알코올 | HIGH | HIGH | 유지 | E046 U | FDA가 아세트아미노펜에 알코올 경고를 의무화(간독성). 경고 대상은 하루 3잔 이상 마시는 사람 |
| DR015 | 감기약(항히스타민 함유) – 알코올 | HIGH | HIGH | 유지 | E058 U | FDA 일반의약품 표시 기준이 항히스타민제에 '알코올 음료를 피할 것' 표시를 요구. 진정 작용이 큰 1세대 항히스타민제에 특히 해당 |
| DR016 | 위장약(H2억제제/시메티딘·라니티딘) – 카페인·알코올 | MEDIUM | MEDIUM | 유지 | E048 Effects of ranitidine on blood alcohol l | H2 차단제가 혈중 알코올 농도를 올린다는 소규모 연구가 있으나 임상적 의미는 논란. 원본 문구('위 염증 악화')는 약물 상호작용이 아니라 위장 질환의 일반 권고에 가까움 |
| DR017 | 골다공증약/제산제 등 – 고섬유·특정 미네랄 동시섭취 | MEDIUM | MEDIUM | 유지 | E059 Weaver CM, Heaney RP, Martin BR, Fitzsim | 밀기울과 함께 먹으면 칼슘 흡수율이 약 30% 감소(0.375 → 0.258). 통밀빵은 영향이 없어 '고섬유 식품' 전체가 아니라 피트산이 농축된 밀기울에 한정된 효과. 철분에 대한 근거는 확인하지 않음 |
