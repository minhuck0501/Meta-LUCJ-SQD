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

## 2026-11-03 — D021: Phase 3 반복 및 예산 진단

단일 geometry 1.2 Å를 유지하고 optimizer/training seeds를 함께 바꾼 두 개의 12회 독립 반복을 추가한다. 이는 optimizer RNG와 finite-sample objective의 변화를 합친 반복 변동성이며 두 요인을 분리한 실험은 아니다. 최초 trajectory는 RNG/current/best checkpoint를 검사해 12→24회로 연장한다. Physics/effective config, optimizer gains와 initial parameter 일치를 확인한다. 신규 seed 89012/90123/101234로 initial/12회/24회 결과를 평가하며 결과로 후보를 재선택하지 않는다. 같은 최초 optimizer에 대해서만 예산 곡선을 확인하므로 모든 seed에서 24회 효과를 입증하지 않는다. 기존 초기 진단/평가 비용과 연장 비용을 별도로 기록한다. 설정은 configs/phase3_repetitions.json에 저장하며 geometry 확대 전 단일 지점 baseline의 변동성을 확인한다.

## D022: Phase 3 반복 결과 해석 기준

최종 seed별 평균·표준편차와 optimizer 반복별 평균을 분리해 보고한다. 세 평가 seed를 공유하는 optimizer 반복 결과를 9개의 완전히 독립된 관측치로 합치지 않는다. 최초 12회 checkpoint와 연장 24회를 같은 신규 평가 seed에서 비교하되, 해당 결과로 gain이나 candidate를 재선택하지 않는다. 예산 증가에도 결과가 같으면 그대로 보고한다. 기존 pilot과 추가 실행의 실제 비용을 모두 제시하고, checkpoint 재사용을 공짜 실행으로 계산하지 않는다. Budget exhaustion을 optimizer convergence로 바꾸지 않는다.


## D023: Phase 3 반복 및 예산 결과

새 평가 seeds에서 초기 평균 오차 44.56 mHa가 세 경로에서 각각 36.62/27.42/30.25 mHa로 감소했다. 경로 1은 12→24회 연장에도 best candidate가 바뀌지 않아 추가 개선이 없었다. 모든 run 검사는 통과했으나 budget_exhausted이며 수렴을 주장하지 않는다. 신규 실행 시간 합계 약 452.22초, 선행 pilot 포함 실제 평가 187회다. 다음은 다른 geometry에서 같은 독립 refinement 설정을 진단하는 것으로, 전체 Phase 3 및 Phase 4 진입은 아직 완료하지 않았다. 상세 근거는 experiments/PHASE3_REPETITIONS.md에 기록했다.

## 2026-11-04 — D024: 다른 geometry의 독립 refinement

N₂ 1.0/1.6 Å에 고정한 12회 SPSA pilot 설정을 독립 적용한다. Optimizer/training seed=45678/12345, evaluation seeds=89012/90123/101234, 50,000 shots 등은 1.2 Å 비교와 맞춘다. 새 geometry마다 우선 한 optimizer trajectory에서 sampling seed 3개의 변동을 측정한다. 독립 optimizer 반복 3개를 완료한 1.2 Å와 같은 재현성 근거로 해석하지 않는다. Geometry 간 warm start나 parameter transfer는 수행하지 않는다.

Phase 2 reference의 physical config와 HF total 일치를 검사하고 같은 chemistry 구현으로 적분을 재생성한다. Phase 2에는 새 geometry의 integral archive가 없었으므로 과거 적분과의 직접 비교가 아닌 동일 정의의 재구성임을 provenance에 명시한다. FCI 값은 Phase 2의 convergence/residual 검증 결과를 재사용하며 재계산 비용을 이번 시간에 포함하지 않는다. Point별 설정·재생성 적분·log와 child report를 저장한다.


## D025: 다른 geometry의 refinement 결과

1.0 Å의 별도 평가 평균 오차는 35.41→23.47 mHa, 1.6 Å는 62.91→54.52 mHa로 감소했다. 각 거리의 3 sampling seeds 모두 개선됐고 수치 검사를 통과했다. 각 한 optimizer trajectory, 12회 budget exhaustion이며 목표 정확도나 수렴은 미입증이다. Child wall time 합 약 277.72초, 전체 objective 92회다. 근거는 experiments/PHASE3_GEOMETRIES.md와 phase3_geometries_summary.json에 있다. 새 거리의 optimizer 반복과 예산 검증은 남아 있으며 아직 Phase 4로 진입하지 않는다.

## 2026-11-04 — D026: Fixed-budget pilot 및 Phase 4

사용자 승인에 따라 수십 mHa 오차를 pilot의 현재 수준으로 허용하고 고정 예산 비교를 진행한다. 목표 정확도 달성이나 optimizer 수렴을 의미하지 않는다. Phase 4에서는 1.0→1.2→1.6 및 역방향에서 이전 지점 best를 새 구조의 초기값으로 쓴다. 각 target은 같은 SPSA 12회, 50,000 shots, training/direction/evaluation seeds와 solver budget을 사용한다. Chain endpoint는 기존 독립 실행을 재사용하되 생성 비용을 누적 비용에 포함한다. 이전 best 선택은 training energy만 사용한다.

## D027: Warm-start orbital sign convention

Cross-geometry AO overlap에서 active MO 대각 overlap 부호 D를 계산하고 회전을 U→DUD, final rotation도 같은 방식으로 변환하며 J는 유지한다. Γ(D)는 occupation basis의 부호 연산이며 J와 commute한다. Closed-shell HF는 두 spin의 동일 occupation으로 Γ(D) 위상이 상쇄되므로 변환된 ansatz state=Γ(D) 원래 state다. H₂의 state equality와 동일 gauge로 변환한 Hamiltonian energy invariance를 수치 검증했다. 실제 다른 geometry의 Hamiltonian은 다르므로 에너지 보존을 요구하지 않는다.

이는 sign-only index-preserving transfer다. Permutation, degenerate orbital subspace rotation, Procrustes는 수행하지 않는다. 대각 overlap과 최대 offdiagonal overlap을 기록해 한계를 드러내며 결과에 따라 전송 방식을 사후 선택하지 않는다. 새 실행은 MO coefficients를 저장한다. 과거 endpoint는 저장된 MO가 없어 같은 로컬 환경에서 재구성한다는 한계를 기록한다. Source chemistry 재구성 비용과 endpoint 비용도 보고한다. Phase 5의 전체 alignment 분석을 완료한 것으로 간주하지 않는다.


## D028: Phase 4 결과와 단계 표기

양방향 sign-only pilot의 네 target 모두 실행·잔차 검사를 통과했으나 independent보다 평균 오차가 컸다. 증가 방향의 1.2/1.6 Å는 43.70/83.50 mHa, 감소 방향의 1.2/1.0 Å는 44.64/54.25 mHa다. 오비탈 diagonal overlap이 거의 0인 구간이 있어 전송 규칙의 한계를 확인했다. 모든 warm start의 실패나 단일 원인으로 일반화하지 않는다. 이번 pilot은 완료했으며 Phase 5에서 correspondence와 gauge를 분석해야 한다. 상세 근거는 experiments/PHASE4_RESULTS.md에 있다.

README와 RESEARCH_PLAN의 단계 번호를 사용자와 합의한 최초 Phase 0–7로 통일했다. Phase 3=independent, 4=warm start, 5=표현 분석, 6=Meta, 7=전체 benchmark이며 과학적 계산 설정은 이 번호 정리로 변경하지 않았다.

## 2026-11-04 — D029: Phase 5 표현 및 전송 진단

세 geometry의 독립 best를 사용해 인접 양방향 4쌍을 분석한다. Active MO cross-overlap의 SVD와 maximum-weight orbital assignment를 진단하며 assignment 자체를 파라미터 재배열에 사용하지 않는다. 같은 source best에 sign-only 및 polar 전송을 각각 적용하고 refinement 없이 target의 sampling/SQD 성능을 평가한다. 이는 chain history 효과를 분리한 zero-refinement 진단이며 Phase 4 chain 결과를 대체하지 않는다.

Polar 제안은 O=C_source† S_cross C_target, G=polar(O†)로 unitary를 만들고 final orbital rotation만 G F_source로 바꾼다. 따라서 원래 ansatz 내부 locality를 바꾸지 않고 Γ(G)|ψ_source>를 정확하게 표현한다. 작은 비자명 상태에서 output rotation identity를 검증한다. Cross-geometry O는 일반적으로 unitary가 아니므로 이 projection은 물리적 동일성의 보장이 아닌 approximate transport 선택이다. Full occupied/virtual mixing을 허용하며 target optimized state는 G 계산에 사용하지 않는다. Target best와의 fidelity/확률 TV는 평가용 보조지표다.

AB diagonal Jastrow 원소에 2π를 더한 상태의 불변성을 검사하고 raw parameter 비유일성을 직접 확인한다. 다른 좌표에 동일 주기성을 무단 적용하지 않는다. 세 geometry의 centered parameter SVD도 기록하되 rank≤2는 세 표본의 수학적 한계이므로 learnable low-dimensional structure 증거로 간주하지 않는다. 이번 geometry/seed는 development pilot이고 최종 test 분할이 아니다.

## D030: Phase 5 block-polar 후속 진단

첫 분석에서 full polar는 3/4 방향 SQD 오차가 낮았으나 target independent state fidelity는 낮아졌고 역방향 한 곳은 에너지도 개선되지 않았다. 따라서 occupied/virtual mixing 영향을 분리하기 위해 두 block의 polar를 각각 구하는 후속 exploratory transport를 추가한다. 이는 첫 결과를 보고 제안한 후속 진단이므로 사전 등록한 최종 비교로 부르지 않는다. 두 block rotation은 HF occupation을 유지하며 같은 output-rotation 구현으로 적용한다. 설정을 세 방법으로 갱신하고 이번 후속 실행에서는 --methods block_polar만 계산해 기존 결과를 재사용한다. 최종 Meta 규칙이나 효과를 이 pilot에서 사후 선택해 일반화하지 않는다.


## D031: Phase 5 진단 결과

오비탈 assignment 후 overlap은 개선되지만 cross-geometry O는 unitary가 아니었다. Jastrow 한 좌표의 2π 이동에서 상태 차이 6.21e-16으로 비유일성을 확인했다. 세 표본의 rank≤2를 learnability 증거로 해석하지 않는다. 추가 refinement 없는 block-polar 전달은 네 방향에서 sign-only보다 낮은 평균 SQD 오차(31.55/57.02/45.97/28.50 mHa)를 보였다. Full polar는 역방향 하나에서 오차가 증가했다. Target approximate best와 fidelity도 SQD energy 순서를 대체하지 못했다. 12개 테스트와 모든 SQD residual 검사를 통과했다. 다음은 고정 block-polar 규칙으로 warm-start baseline 재검증 및 Meta용 공통 표현 설계다. 상세 증거는 experiments/PHASE5_RESULTS.md에 있다.

## 2026-11-04 — D032: Block-polar warm-start 재검증

Phase 5의 탐색 결과에 따라 block-polar 규칙을 모든 방향에 고정해 Phase 4와 같은 양방향/12회/SPSA gains/seeds/shots에서 재평가한다. Sign-only 원본 결과는 보존한다. Target별 결과를 보고 규칙을 선택하지 않는다. 평가 데이터는 개발 pilot이며 최종 일반화 test는 아니다. Endpoint 생성 비용과 신규 실행 비용을 분리하고 same-accuracy speedup으로 주장하지 않는다. Meta 학습은 이 실행에 포함하지 않는다.

## D033: Meta pilot용 공통 표현 후보

공통 anchor는 최초 단일 지점인 1.2 Å로 사전 고정한다. 향후 Meta split에서 이 anchor는 training geometry에 포함해야 하며 held-out optimized state에서 기준을 만들지 않는다. Source operator를 block-polar로 anchor 좌표에 옮긴 뒤 내부 orbital rotation의 column phase만 최대 절대 성분이 실수 양수가 되도록 고정한다. Column diagonal phases는 J와 commute하므로 layer state를 바꾸지 않는다. Column permutation과 축퇴공간의 모든 내부 gauge까지 canonicalize한 것은 아니다. Final rotation의 임의 column phase는 고정하지 않는다.

Unitary matrices는 real/imag entries, 허용된 J 계수는 cos/sin으로 encode한다. Decode 시 matrix polar projection과 atan2를 사용한다. Singular predicted matrices 또는 0인 angle pair는 오류로 처리한다. Matrix-entry 방식은 로그 branch를 피하지만 feature 공간은 중복이며 회귀 오차가 상태 오차를 보장하지 않는다. 현재 1-layer 16 orbital에서는 1062 features로 raw 531 parameters보다 많다. 복잡한 모델의 근거로 삼지 않는다.

Encode/decode 및 역방향 anchor rotation 후 원래 N₂ state가 복원되는지 검증한다. 동일 좌표로 되돌리는 이 불변성 검사는 실제 다른 geometry의 physical state가 동일함을 뜻하지 않는다. 이번 작업은 표현 후보와 roundtrip 검증이며 Meta fit이나 held-out 일반화 실험은 아니다.

## D034: Common-frame operator convention 및 검증

공통 frame의 표현은 final output rotation만 합성하는 전송과 구분한다. Block unitary G에 대해 모든 내부 U를 GU, final F를 GFG†로 바꿔 operator를 conjugate한다. G가 occupied/virtual partition을 보존하므로 HF는 global phase까지 유지되며 real RHF block rotations에서는 두 spin 위상이 상쇄된다. 역변환은 G†로 수행한다. Nontrivial state에서 covariance와 inverse를 검증했고 N₂ 세 구조의 encode/decode/inverse-frame state L2 error는 약 1.1e-14 이하였다.

최초 output-only embedding draft archive는 보존하지만 현재 representation은 위 전체 operator-frame convention으로 고정한다. Feature 1062개는 raw 531개보다 많고 redundancy가 있으며, 내부 permutation/degeneracy, anchor 경로 의존성 및 final global phase 문제를 전부 해결한 유일 표현은 아니다. 이 후보로 작은 Meta pilot을 검토할 수 있지만 현재 결과는 학습/일반화 증거가 아니다.

표현 검증 및 테스트가 warm-start 재평가와 일부 겹쳐 실행됐다. 따라서 wall times는 실행 기록으로 보고하며 미세한 runtime 차이나 speedup의 근거로 사용하지 않는다.


## D035: Block warm-start 및 공통 표현 결과

양방향 네 target 모두 수치 검사를 통과했다. 증가 방향의 1.2/1.6 Å 평균 오차는 30.96/50.31 mHa로 independent보다 낮았지만, 감소 방향의 1.2/1.0 Å는 41.15/36.19 mHa로 높았다. Sign-only보다는 네 target 모두 평균 오차가 낮았다. Direction dependence와 기존 개발 데이터 재사용 한계를 유지하며 일반적 우위나 speedup을 주장하지 않는다. 고정 공통 표현은 세 구조의 inverse-frame roundtrip state error 약 1.13e-14 이하를 통과했다. 전체 테스트 14개다. 근거는 experiments/BLOCK_WARMSTART_RESULTS.md 및 META_REPRESENTATION.md에 있다. Phase 6의 작은 모델을 검토할 수 있으나 아직 fitting/미관측 geometry 검증은 수행하지 않았다.

## 2026-11-04 — D036: Phase 6 affine initialization pilot

Training은 기존 1.0/1.2/1.6 Å common-frame features다. Anchor 1.2 Å를 training에 포함한다. Validation 1.1 Å와 pilot test 1.4 Å는 기존 label/feature 데이터에 포함되지 않는다. Affine ridge의 slope penalty=1e-6을 사전 고정하고 geometry center/scale은 training에서만 추정한다. Validation 결과로 모델/gain을 조정하지 않고 두 point를 같은 frozen 모델로 평가한다. 이는 최종 project test가 아닌 첫 development pilot이다.

Target에서는 예측 feature decode 및 anchor→target block-frame 변환 후 추가 refinement 없이 SQD를 평가한다. 독립 regularized CCSD 초기화와 training source 1.0→1.1, 1.2→1.4의 single-hop block-polar warm initialization을 비교한다. 이 warm 비교는 Phase 4의 전체 sequential refinement chain과 다르며 그 대체가 아니다. Methods 모두 50,000 shots, seeds 112233/223344/334455와 같은 batch/solver 조건을 사용한다. 새 FCI reference를 계산하고 convergence/residual을 보고한다.

Label archive 생성의 기존 end-to-end 비용, feature 준비, model fitting, target prediction/transport, initialization 및 SQD 비용을 구분한다. 이 zero-refinement pilot으로 전체 최적화 비용 절감이나 강한 warm-start 대비 효율성을 입증하지 않는다. Feature MSE보다 SQD energy를 우선하고 부정적 결과도 보존한다.


## D037: Phase 6 첫 Meta 결과

Frozen affine common-frame 모델의 미학습 point 평가에서 1.1 Å는 independent/warm/meta 평균 오차 48.03/27.55/38.37 mHa, 1.4 Å는 49.49/43.64/59.85 mHa였다. Meta의 일관된 이점이나 전체 비용 절감은 확인하지 못했다. 두 point와 18개 sampling/SQD 결과의 수치 검사를 통과했고 새 FCI도 수렴했다. Feature MSE만으로 성공을 주장하지 않는다. 기존 label archive 비용 약 418.37초와 feature preparation 기록을 보존한다. 추가 validation/test 결과를 보고 model을 변경하면 새 독립 test를 확보해야 한다. 상세 증거는 experiments/PHASE6_PILOT_RESULTS.md에 있다. Phase 7로 진행한 것은 아니다.

## 2026-11-04 — D038: Frozen Meta 모델 재구성 진단

Phase 6 모델을 재학습/수정하지 않고 학습 geometry에서 label feature decode control과 affine prediction을 비교한다. Exact-label encode/decode/inverse-frame state 일치가 통과하면 decoder 구현 오류와 regression 오차를 구분하는 근거로 쓴다. Fresh sampling seeds 445566/556677/667788에서 label과 prediction의 SQD를 같은 예산으로 평가한다. Pre-projection unitarity/singular values/polar displacement, J angle radius, fidelity, probability TV 및 entropy/HF mass를 기록한다. Unseen 1.1/1.4는 저장된 method states의 분포만 분석하며 새 후보를 선택하지 않는다. Approximate label/baseline fidelity는 ground-state 정확도 자체가 아님을 유지한다. 이번 결과를 본 뒤 모델을 바꾸면 두 pilot target은 개발 데이터로 취급하고 새 독립 test를 정해야 한다.


## D039: Frozen Meta 진단 결과와 다음 원인 분리

Exact feature control은 세 training states를 약 1e-14 이내로 복원했다. Affine prediction의 label fidelity는 0.922/0.721/0.970이며 1.0/1.2 Å에서 label 대비 SQD 평균 오차가 약 10–11 mHa 높았다. 내부 U의 pre-projection 최소 singular value는 0.335/0.118/0.643으로, final F보다 크게 unitary 제약에서 벗어났다. 단일 원인으로 확정하지 않지만 affine feature 평균/표현의 training reconstruction을 먼저 조사할 근거다. Entropy/다양성도 SQD energy를 대신하지 못했다. 모델 수정 없이 약 47.36초에 진단했다. 다음 후보는 training-point-exact local/manifold interpolation 대조군이다. 모델 변경 시 기존 두 pilot targets를 development로 취급하고 새로운 독립 평가를 확보한다. 상세 증거는 experiments/META_DIAGNOSTIC_RESULTS.md에 있다.
