# Research Plan

작성일: 2026-11-03. 상태: Phase 0 초안. 수치적 성능은 아직 검증하지 않았다.

## 목표와 가설

N₂ potential energy curve에서 geometry-conditioned LUCJ 초기화가 독립 최적화와 sequential warm start에 비해 동일한 SQD 정확도에 도달하는 총 비용을 줄이는지 검증한다. 학습 자료 생성 비용도 포함한다. 파라미터의 매끄러움이나 회귀 정확도는 최종 성공 기준이 아니다.

## 문헌에서 출발하는 부분

- LUCJ 초기화 논문의 §2–3: CCSD t-amplitudes의 double factorization, locality truncation, compressed double factorization. 압축 목적함수는 t₂ 재구성 오차이며 SQD 에너지 자체가 아니다. §4와 Fig. 1은 N₂/6-31G (10e,16o)를 포함한다.
- Meta-VQE 논문의 §II, Eq. (1) 및 Fig. 1: Hamiltonian 매개변수를 circuit에 encoding하고 여러 training point의 기대 에너지를 공동 최적화한다. opt-meta-VQE는 학습 결과에서 개별 VQE를 시작한다.
- SQD 논문: quantum samples와 고전 부분공간 대각화, 점유율 기반 configuration recovery를 결합한다. 본 연구의 작은 CPU benchmark는 해당 대규모 하드웨어 결과의 재현이나 quantum advantage 검증이 아니다.

이들을 geometry-conditioned LUCJ/SQD에 결합해 비용을 검증하는 것은 본 프로젝트의 제안이다. Meta-VQE의 결과가 SQD 목적함수로 자동 이전된다고 가정하지 않는다. 세부 문헌 비교와 notebook 검토는 METHODOLOGY.md에 기록한다.

## 단계와 통과 조건

| 단계 | 산출물 | 다음 단계 진입 조건 |
| --- | --- | --- |
| 0 설계 | 방법론, benchmark protocol, 결정 기록 | 미정 사항과 검증 순서 명시 |
| 1a 작은 검증 | 결정론적 chemistry/state/sampling/subspace 테스트 | 에너지 상수, tensor convention, bit order 검증 |
| 1b 단일 구조 | N₂ 1.2 Å 설정·결과·시간·메모리 | SCF/CCSD 수렴, 자원 측정, 기준 에너지 신뢰성 확인 |
| 2 작은 sweep | 소수 구조의 수렴·샘플링 진단 | 실패를 포함한 재현 가능한 기록 |
| 3 독립 최적화 | 고정 예산 independent refinement 결과 | 독립 평가·실패·비용 기록 |
| 4 Warm start | 양방향 sequential 결과 | 동일한 목적함수·예산·평가 조건, 전송 규칙 명시 |
| 5 표현 분석 | gauge/주기성/유효 차원 분석 | 변환의 물리적 불변성 확인 |
| 6 Meta pilot | 단순 모델의 validation 결과 | test를 사용하지 않은 모델 선택 |
| 7 최종 비교 | held-out 정확도·비용·불확실성 | 독립 seed 및 학습 overhead 포함 |

## 첫 번째 실험

먼저 작은 H₂/STO-3G 문제에서 library 연동과 convention을 검증한다. 이는 N₂ benchmark를 대체하는 설정 변경이 아니라 수치 unit/integration validation이다. 이후 N₂/6-31G, R=1.2 Å, frozen core=2, active (10e,16o)에서 chemistry를 검증한다. 큰 FCI나 반복 SQD 최적화는 자원 점검 후 수행한다.

16 orbital, (5,5)의 고정 입자수 공간은 19,079,424 determinants다. complex128 state vector 하나만 약 291 MiB이고, 연산 workspace·여러 state 복사본·FCI Davidson vector는 별도다. 전체 32-qubit dense statevector는 64 GiB이므로 초기 backend로 사용하지 않는다. 이는 초기 자원 추정이며, 이후 실측 시간·메모리는 docs/experiments/의 실행별 보고서에 기록한다.

## 학습 접근의 우선순위

우선 baselines에서 확보한 소수 구조의 파라미터로 affine 또는 저차 모델을 검토한다. 단순 supervised regression은 저렴하지만 비유일성과 label 생성 비용에 취약하다. 직접 SQD 학습은 목표에 가깝지만 잡음과 반복 대각화 비용이 크다. 따라서 supervised pilot 후 필요할 때 제한된 SQD refinement를 붙이는 hybrid를 출발 후보로 삼는다. 최종 선택은 validation SQD 성능과 비용에 따른다. 신경망, tensor-network surrogate, direct stochastic meta optimization은 초기 필수 구현에서 제외한다.

## 주요 위험

기준 에너지 불확실성, SCF/CCSD breakdown, orbital gauge, 파라미터 비유일성, alignment를 통한 test leakage, 불공정한 예산, noisy objective에 대한 과적합, 학습 비용 미회수. 실패하면 설정·원인·소비 비용을 보존한다.
