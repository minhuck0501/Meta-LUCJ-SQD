# Decisions

## 2026-11-03 — D001: 설계와 작은 검증부터 진행

상태: 채택. 기존 연구 지침에 따라 large sweep과 meta 학습 전에 numerical validation을 수행한다. 대안인 notebook 전체 즉시 실행은 물리 조건 차이와 hardware 의존성 때문에 채택하지 않는다. 이번 단계에서는 notebook을 실행하지 않는다.

## D002: 초기 benchmark 유지

상태: 채택. N₂/6-31G, frozen core 2, active (10e,16o), 첫 거리 1.2 Å를 유지한다. Notebook의 1.0 Å/cc-pVDZ (10e,26o)는 별도 reference 사례다. 작은 H₂ 검증은 benchmark 대체가 아니다.

## D003: 에너지 상수 명명

상태: 채택. PySCF get_h1cas의 두 번째 반환값을 ecore로 명명한다. 핵 반발만으로 해석하거나 별도로 핵 반발을 다시 더하지 않는다. 설치된 PySCF h1e_for_cas source를 확인했으며 HF determinant 비교로 수치 검증할 예정이다.

## D004: CPU fixed-particle-number backend 우선

상태: 채택. 32-qubit dense statevector 하나는 complex128 기준 64 GiB다. 대신 ffsim의 fixed-particle-number 표현을 우선 검토한다. N₂ (5,5), 16 orbital state 하나는 약 291 MiB지만 전체 계산 peak memory는 별도 측정한다. GPU나 IBM runtime은 초기 필수 의존성으로 추가하지 않는다.

## D005: Meta 학습 순서

상태: 출발 제안. Baseline 생성 후 표현 분석과 단순 supervised 모델을 먼저 검토하고 필요시 SQD refinement를 결합한다. Direct SQD meta-loss는 비용과 잡음 때문에 보류한다. 이 선택은 성능이 입증된 결론이 아니며 validation 결과로 재평가한다.

## D006: 아직 동결하지 않은 항목

정확한 LUCJ operator/packing/final rotation, 최종 interaction topology, spin penalty, SQD batch/shot 예산, optimizer, 최종 geometry split, reference solver와 acceptance tolerance는 미정이다. Notebook 값을 무단 기본값으로 채택하지 않는다. 각 항목은 source 확인 및 작은 테스트 이후 config와 결정 기록에 추가한다.

## D007: 증거 범위

이번 단계의 증거는 로컬 PDF의 관련 방법·조건 텍스트, notebook 코드의 정적 검토, 설치된 PySCF/SQD source 및 signature 확인이다. 논문 재현이나 chemistry/LUCJ/SQD 수치 실험을 수행하지 않았다. Notebook에 저장된 결과를 새 실험 성과로 주장하지 않는다.

## 2026-11-03 — D008: Phase 1 실행 조건

상태: 검증용 채택. configs/phase1.json에 단일 지점 설정을 저장했다. CCSD 단순 double factorization + locality truncation, 1 repetition, t₁ 기반 final rotation을 사용한다. from_parameters 소스 기준 repetition별 orbital rotation n²개, AA interaction, AB interaction 순이며 마지막에 final rotation n²개가 온다. N₂에서는 256+15+4+256=531 parameters다. 이는 최종 benchmark ansatz 선택이 아니다.

Ideal fixed-particle-number sampling 10,000 shots, seed=12345, 200 samples/batch, 3 batches, 최대 2 SQD iterations다. Spin penalty와 spin symmetrization은 사용하지 않는다. 에너지/점유율 중지 tolerance는 각각 1e-8 Ha/1e-6이다. 투영 eigenvector residual 1e-6 미만을 실행 검증 기준으로 쓴다. 이는 reference 대비 정확도 acceptance가 아니다. Configuration recovery 구현을 호출하지만 이상적인 샘플은 모두 입자수 대칭을 만족하므로 noise recovery 성능을 검증하지 않는다.

PySCF 설치는 OpenMP 미지원 경고를 출력했다. thread 요청은 1로 고정하고 BLAS 환경도 1로 제한한다. Multi-thread 성능에 관한 결론을 내리지 않는다. 초기 실행의 SCF diagnostic API 호출 오류를 수정했으며 실패 report는 삭제하지 않았다.

## D009: H₂ sampling 검증의 범위

Locality-truncated 1-layer LUCJ 샘플이 H₂ exact energy를 반드시 복원한다는 테스트 가정은 실제 실행에서 성립하지 않았다. 물리적 성능 가정을 수치 correctness 조건과 혼동한 테스트를 수정했다. 전체 determinant support를 명시적으로 공급하는 별도 SQD 테스트에서 FCI 일치를 확인하고, LUCJ 샘플 테스트에서는 variational bound와 residual을 검사한다. 샘플링이 중요한 배치를 누락하면 SQD가 정확하지 않을 수 있다는 한계를 보존한다.


## D010: Phase 1 결과와 다음 단계

N₂ 단일 지점 최소 pipeline과 H₂ 검증 5개는 통과했다. 측정된 SQD–FCI 오차가 189.95 mHa이므로 에너지 품질을 달성했다고 선언하지 않는다. Phase 2 sweep은 보류하고 같은 지점에서 압축 초기화와 sampling support를 조사한다. FCI energy convergence flag와 eigenvector residual을 구분하며 현재 reference를 미세한 성능 차이의 certified 기준으로 사용하지 않는다. 상세 증거는 experiments/PHASE1_RESULTS.md와 원본 report에 저장했다.

## 2026-11-03 — D011: 단일 지점 압축 초기화 비교

N₂ 1.2 Å, 6-31G, (10e,16o), core 2, layer 1, interaction topology와 final t₁ rotation은 유지한다. 단순 truncation과 single-stage compressed double factorization을 비교한다. Compressed objective는 0.5*||t₂_reconstructed−t₂_CCSD||²이고 regularization=0이다. AA/AB interaction의 합집합으로 압축한 후 각각의 locality mask를 적용한다. 설치된 ffsim 고수준 constructor와 작은 H₂ 상태가 일치하는지 테스트했다. Library constructor가 버리는 OptimizeResult를 보존하기 위해 같은 library의 하위 API를 사용한다.

Seeds는 12345, 23456, 34567이고 shots는 10,000과 50,000이다. 이는 training/test split이 아닌 단일 지점 진단이다. 같은 seed 번호를 방법 간 사용하지만 common random numbers의 통계적 최적 coupling을 주장하지 않는다. 각 방법·예산별 sample arrays와 batch별 에너지·projected residual을 저장한다. FCI tolerance는 1e-9에서 1e-11 Ha로 강화하고 residual을 다시 계산한다.

예비 실행 initialization_20261103T065403에서 compressed optimizer가 1,000회 한도에 도달했고 일부 SQD projected residual이 1e-6을 넘었다. 결과를 삭제하지 않고 검증 미완료로 취급한다. 후속 실행에서는 압축 maxiter=10,000, SQD solver tol=1e-13 및 max_cycle=200으로 강화한다. 모든 방법에 동일하게 적용하며 projected residual 검증 한도 1e-6은 완화하지 않는다. Phase 1의 기존 설정 파일은 변경하지 않고 별도 비교 설정의 override로 기록한다. Optimizer success와 gradient norm은 함께 보고하며 에너지 정확도 달성과 동일시하지 않는다.

## D012: 10,000회 압축 예산의 해석

강화 실행 initialization_20261103T065552에서도 압축 optimizer는 10,000회 한도에 도달했다. Loss는 줄었으나 gradient norm과 success flag상 수렴을 입증하지 못했다. 반복 한도를 계속 늘리거나 tolerance를 완화하여 성공으로 표시하지 않는다. 동일한 예산의 중간 해에 대한 SQD 진단 결과로 보고하고 전체 report를 validation_incomplete로 유지한다. 이 결과만으로 Phase 2 또는 Meta 학습에 진입하지 않는다. 다음 후보는 문헌의 multi-stage compression이며 별도 설정과 비교가 필요하다.

## 2026-11-03 — D013: Multi-stage compression 진단

Single-stage 실패에 대한 다음 실험은 같은 N₂ 1.2 Å에서 4→3→2→1항 compression이다. 각 단계에서 최적화된 factorization을 다음 단계 초기값으로 전달하며 public ffsim double_factorized_t2_compressed를 사용한다. 이는 문헌의 점진적 truncation 접근이며 새로운 압축 알고리즘은 아니다. 작은 H₂에서 ffsim multi_stage_start/step constructor와 최종 상태의 일치를 확인했다. 중간 단계별 success/message/loss/gradient/iteration/evaluation을 모두 보존한다. 최종 단계만 수렴해도 중간 실패를 숨기지 않으며 전체 검증 상태에 반영한다.

각 단계 최대 10,000회, 동일 ftol=1e-12 및 gtol=1e-7을 유지한다. 이는 single-stage보다 최대 총 예산이 크므로 equal-compute 우월성을 주장하지 않는다. Seeds, shots, batch, solver tolerance 및 최종 topology는 이전 비교와 같다. 설정은 results/initialization_20261103T071730/source_snapshot/configs/multistage_comparison.json에 분리했다.

기존 refined FCI를 재사용하되 물리 설정, HF total, 이전에 저장한 h1/eri/ecore와의 일치(절대 tolerance 1e-10), reference convergence/residual을 확인한다. 재사용한 기준 계산 비용은 새 실행 시간에 포함하지 않고 provenance를 기록한다. 원본 결과가 없거나 조건이 다르면 실행을 실패시킨다. 원본 reference 파일 경로는 로컬 실험 재현용이며 새 checkout에서는 reference 계산을 먼저 수행해야 한다.


## D014: Multi-stage 결과와 진입 판단

실행 initialization_20261103T071730은 4개 단계 모두 maxiter에 도달했고 validation_incomplete다. SQD solver 검증은 통과했지만 압축 수렴 검증은 통과하지 못했다. 50,000 shots의 SQD 오차는 평균 49.58 mHa로 이전 single-stage의 44.97 mHa보다 개선되지 않았다. Phase 2는 보류한다. 반복 한도 추가 증가보다 gradient/scale/trajectory와 norm을 진단한 후 원인에 맞는 변경을 결정한다. 상세 증거와 비용은 experiments/MULTISTAGE_RESULTS.md에 보존한다.

## 2026-11-03 — D015: Norm 증가 진단과 regularization

Gradient central-difference 검사와 optimizer trajectory를 기록했다. Gradient 오류의 증거를 발견하지 못했고, 대신 J norm 증가를 관측했다. 문헌 및 ffsim의 norm regularization λ=0.001을 별도 pilot config로 추가했다. 이는 목적함수 변경이며 기존 실험을 대체하지 않는다. λ는 이 단일 지점의 진단 후보이고 최종 benchmark 최적값이 아니다. 기존 gtol=1e-7을 유지한 채 gradient ∞ norm 7.79e-8로 5,290회에 종료했다. SQD 정확도는 여전히 약 44–55 mHa이며 에너지 개선을 주장하지 않는다. 상세 근거는 experiments/COMPRESSION_FIX_RESULTS.md에 있다.

## D016: Phase 2 진입 판단 갱신

D014 이후 gradient 검증, coefficient norm 진단 및 regularized objective의 gradient 수렴을 확인했다. 따라서 고정 pilot 설정으로 소수 geometry의 진단용 Phase 2를 진행할 수 있다. 목표 정확도 달성이나 최종 benchmark 준비 완료로 판정한 것은 아니다. 초기화 미수렴·자원 부족·reference 불확실성을 숨기지 않고 geometry별 실패를 기록한다. 큰 sweep과 meta training은 계속 보류한다. 이번 실행에서는 아직 Phase 2를 실행하지 않았다.

## 2026-11-03 — D017: Phase 2 소규모 진단 sweep

N₂의 1.0, 1.2, 1.6 Å 세 지점을 사용한다. 압축·평형 근방·늘어난 결합의 소규모 진단이며 전체 dissociation curve나 train/test split이 아니다. 6-31G, core 2, (10e,16o), layer 1, λ=0.001, optimizer tolerances와 10,000회 한도는 고정한다. 50,000 shots 및 기존 seed 3개를 사용하고 truncated control을 함께 실행한다. Geometry마다 독립 chemistry/CCSD 초기화이며 warm start나 meta 학습은 수행하지 않는다. 새 geometry는 FCI tol=1e-11, 최대 100 cycles로 기준을 계산한다. 1.2 Å만 기존 reference를 적분 일치 검사 후 재사용한다. 실패·미수렴도 저장하며 다음 geometry로 진행한다. 실행당 600초 timeout은 자원 보호 한도이고 수렴 기준을 바꾸지 않는다. 기존 측정 기준 각 새 reference는 약 90초/5 GiB 규모이나 거리별 비용은 달라질 수 있다.


## D018: Phase 2 pilot 결과

1.0/1.2/1.6 Å 모두 SCF·CCSD·regularized compression·FCI·SQD projected residual 검사를 통과했다. 압축 초기화의 평균 SQD 오차는 각각 35.48/44.25/65.44 mHa다. 이 세 지점 진단은 완료했고, 더 넓은 geometry 범위나 목표 정확도 달성을 주장하지 않는다. Phase 3에서 독립 SQD refinement baseline의 정확도-비용 관계를 검증하는 것이 다음 과제다. 근거는 experiments/PHASE2_RESULTS.md와 phase2_summary.json에 저장했다.

## 2026-11-03 — D019: Phase 3 단일 지점 SQD refinement pilot

N₂ 1.2 Å에서 regularized CCSD 초기값으로 시작해 531개 LUCJ parameters 전체를 SQD 에너지 기준으로 조정한다. 기대값 VQE나 t₂ fitting으로 목적함수를 대체하지 않는다. SPSA의 두 방향 차분 gradient 추정과 감소하는 a/c schedule을 사용한다. 참고: Spall, An Overview of the Simultaneous Perturbation Method for Efficient Optimization (1998), https://www.jhuapl.edu/spsa/pdf-spsa/spall_an_overview.pdf . L2 step cap=0.1은 본 pilot의 안정화 선택이며 표준 SPSA의 수렴 보장을 이 유한 샘플 objective에 적용하지 않는다.

훈련 seed 12345를 고정해 유한 샘플 empirical objective를 정의한다. 12회 업데이트, 초기값 1회와 각 회 plus/minus/candidate 3회로 37회 훈련 평가다. Candidate 중 훈련 energy가 가장 낮은 값을 선택한다. 별도 probe seeds 23456/34567/45670으로 초기 잡음을 확인하고, 최종 initial/refined는 56789/67890/78901에서 비교한다. 모든 평가 50,000 shots, 기존 batch 및 solver 조건을 유지한다. 최종 seed 결과로 후보를 다시 선택하지 않는다. Optimizer direction RNG는 seed 45678로 분리한다.

잡음 probe와 별도 평가도 전체 비용에 포함한다. 예산·gain은 첫 pilot의 사전 고정값이며 최적값으로 주장하지 않는다. 이 실험은 수렴 또는 강한 baseline의 확립이 아니라 refinement 가능성과 noise/cost 진단이다. Optimizer 상태는 budget_exhausted로 기록하고 여러 optimizer seed, 추가 geometry, accuracy-matched 비교는 후속 검증 대상이다.

## D020: Phase 3 단일 지점 pilot 결과

12회 SPSA 갱신 예산의 단일 trajectory를 실행했다. Held-out sampling seeds 3개의 초기/최종 평균 오차는 46.07→37.73 mHa로 감소했고 3개 모두 개선됐다. 46 objective evaluations와 276 batch diagonalizations, 약 140.65초를 기록했다. Run 검사는 통과했으나 optimizer_status는 budget_exhausted이며 수렴으로 주장하지 않는다. 전체 Phase 3는 아직 완료하지 않았다. 복수 optimizer seeds, 예산별 성능과 다른 geometry 검증 후 strong independent baseline 여부를 판단한다. 상세 증거는 experiments/PHASE3_PILOT_RESULTS.md에 있다.
