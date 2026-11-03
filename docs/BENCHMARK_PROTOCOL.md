# Benchmark Protocol

작성일: 2026-11-03. 사전 설계 초안. 최종 grid, 예산, acceptance threshold는 pilot 후 동결한다.

## 물리 조건

N₂/6-31G, frozen-core 2, active (10e,16o), charge 0, singlet, 거리 단위 Å, 에너지 단위 Ha. 첫 점은 1.2 Å. 초기 범위 0.8–2.2 Å, 확장 후보 3.0 Å. 동일한 orbital 선택, Hamiltonian 상수, ansatz topology를 비교 방법에 적용한다. 참조 notebook의 cc-pVDZ 설정과 섞지 않는다.

## Reference

작은 문제에서는 충분히 수렴한 FCI를 사용한다. N₂ target의 FCI는 공간 크기와 peak memory를 점검한 뒤 결정한다. 불가능하면 수렴을 조사한 selected-CI 등으로 reference uncertainty를 보고하고 exact라고 부르지 않는다. CCSD 에너지를 검증 없이 ground truth로 사용하지 않는다. reference 오차가 비교하려는 방법 간 차이를 가리면 결론을 보류한다.

## 비교군

- 독립 초기화: 구조별 CCSD 기반 초기화 후 동일 optimizer로 refinement. 단순 truncation과 compressed initialization은 구별해 명시한다.
- Sequential: 인접 구조 결과에서 refinement. 증가·감소 방향을 각각 측정하고 방문한 구조 및 누적 비용을 기록한다.
- Meta zero-shot: train에서 학습한 모델의 출력을 바로 평가.
- Meta refined: 같은 출력에서 baseline과 동일한 refinement 절차 적용.

CCSD 또는 압축 초기화 실패 시 미리 정한 fallback만 사용하고 실패와 fallback 비용을 기록한다. test 결과를 보고 유리한 fallback을 선택하지 않는다.

## Split 및 randomness

Pilot geometry는 최종 test로 재사용하지 않는다. Train/validation/interpolation-test의 구체적 목록은 pilot 후 config에 저장하고 hash와 함께 동결한다. Interpolation test는 train 범위 내부, extrapolation은 외부로 별도 보고한다. 모델 복잡도, 정렬 규칙, optimizer 설정은 train/validation만으로 선택한다.

개발 seed는 12345다. 최종 평가 seed 목록은 pilot 이후 별도 지정하고 고정한다. sampling, recovery, optimizer, model fitting의 RNG stream을 분리한다. 동일 seed 번호만으로 common-random-number coupling이 보장된다고 가정하지 않는다. 최종 sample 평가는 optimizer 내부 평가와 독립적으로 수행한다.

## 공정한 자원 조건

동일 shots, batch 수, samples per batch, subspace cap, recovery 조건, solver tolerance와 optimizer budget을 사용한다. 목적함수 호출 수와 실제 diagonalization 횟수를 모두 센다. 고정 예산에서의 정확도와 목표 정확도까지의 비용을 함께 보고한다. 목표에 도달하지 못한 실행을 통계에서 제거하지 않는다.

Sequential 방법이 중간 구조를 요구하면 그 비용을 포함한다. 학습에 쓴 구조가 target과 겹칠 때 재사용 조건을 명시하고 서로 다른 사용 시나리오를 섞지 않는다.

## 비용과 측정

Meta total = label 생성 + 모델 학습/선택 + target prediction + refinement + sampling/SQD. Baseline도 chemistry, CCSD, 초기화, sampling, refinement, diagonalization을 분리 기록한다. 공유 전처리는 공통 비용과 방법별 추가 비용을 함께 제시한다.

동일 장비와 thread 설정에서 wall time과 process peak RSS를 측정한다. Python allocator만의 memory 측정으로 native library 메모리를 대체하지 않는다. Warm-up과 파일 I/O 포함 범위를 명시한다. Break-even은 측정된 누적 비용으로 평가하고 절감이 없으면 존재하지 않는다고 보고한다.

## 저장할 정보

각 실행은 run ID, UTC timestamp, config/hash, git revision와 dirty 여부, Python/의존성 버전, OS/architecture, thread 설정, 전체 seed 목록을 갖는다. geometry, basis, orbital ordering, electron 수, ecore, 적분 convention, ansatz parameter packing을 보존한다.

결과에는 총 에너지, reference와 uncertainty, signed/absolute error, sample 수, unique 수, retained probability mass, batch별 dimension, iteration별 에너지와 residual, optimizer history, 시간·peak memory를 포함한다. 상태는 success, nonconverged, failed, interrupted로 구분하고 exception과 checkpoint를 저장한다.

## 보고 기준

복수 seed의 평균·표준편차와 개별 결과, 실패율, 정확도-비용 곡선을 보고한다. 에너지 차이가 stochastic variability와 reference uncertainty보다 작은 경우 우열을 단정하지 않는다. 초기 모델의 회귀 오차와 state/distribution 진단은 보조 지표다. 주된 결론은 held-out SQD 정확도와 학습 overhead를 포함한 비용에 근거한다.
