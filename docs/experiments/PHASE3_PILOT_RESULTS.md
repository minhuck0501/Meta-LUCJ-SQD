# Phase 3 — Independent SQD Refinement Pilot

실행일: 2026-11-03. **단일 지점 pilot 완료. 전체 Phase 3 baseline 확립이나 optimizer 수렴은 아직 아니다.**

## 목표와 방법

N₂ 1.2 Å, 6-31G, frozen core 2, active (10e,16o), 같은 1-layer LUCJ와 t₁ final rotation을 사용했다. λ=0.001 regularized CCSD 초기화는 이전 gradient 기준으로 수렴했다. 이후에는 amplitude loss가 아니라 실제 sampled SQD energy를 목적함수로 사용하여 531개 파라미터 전체를 조정했다. 이 단계의 SQD objective에는 초기화의 norm penalty를 추가하지 않았다.

방법은 Spall의 SPSA를 기본으로 하며, 이번 pilot에서는 L2 step cap을 추가했다. 근거: [Spall (1998), An Overview of the Simultaneous Perturbation Method for Efficient Optimization](https://www.jhuapl.edu/spsa/pdf-spsa/spall_an_overview.pdf).

각 iteration에서 Rademacher direction Δ를 뽑고 g=(E(θ+cΔ)−E(θ−cΔ))/(2c)·Δ를 계산한다. θ←θ−a g로 갱신하되 step L2 norm은 0.1로 제한한다. a/c는 configs/phase3.json의 고정 감소 schedule을 사용한다. 이 방식의 일반적인 asymptotic 성질을 이 유한 예산·불연속 sampled SQD objective의 수렴 보장으로 사용하지 않는다.

12회 갱신, 초기값 1회와 각 iteration plus/minus/candidate 각 1회로 훈련 목적함수 37회다. 훈련 seed는 12345로 고정하고 optimizer direction RNG는 45678로 분리했다. 최종 후보는 candidate/initial 중 훈련 에너지가 가장 낮은 값이다. 훈련 seed 고정은 empirical sample objective 정의이며 true expected SQD objective의 최적화를 보장하지 않는다. Plus/minus 값도 보고서에 남기지만 최종 후보 선택은 사전 정의한 candidate 집합에 한정했다.

초기 noise probe는 23456/34567/45670이며, final evaluation은 별도의 56789/67890/78901이다. Final 결과로 후보를 재선택하지 않았다. 같은 seed를 initial/refined에 적용했지만 완전한 common-random-number coupling이나 독립 paired statistical significance를 주장하지 않는다. 모든 목적함수는 50,000 shots와 기존 SQD 200 samples/batch, 3 batches, 최대 2 iterations, solver tol=1e-13을 유지했다.

## 결과

| 평가 | FCI 대비 평균 오차 ± 표본 표준편차 |
| --- | --- |
| Initial noise probe | 45.18 ± 2.57 mHa |
| Held-out initial | 46.07 ± 1.08 mHa |
| Held-out refined | 37.73 ± 3.14 mHa |

평균 감소는 8.33 mHa이며 3개 held-out sampling seed 모두에서 감소했다. 이는 한 optimizer trajectory의 관측 결과다. 복수 optimizer seed의 재현성, 통계적 유의성, 다른 geometry의 효능은 아직 검증하지 않았다. 약 38 mHa의 오차가 남아 있어 목표 정확도를 확보한 결과는 아니다. 훈련에서 선택한 후보의 오차는 약 28.68 mHa로, held-out 평가와 차이가 있어 훈련 값만으로 성능을 보고하면 낙관적이다.

전체 46회 목적함수는 noise probe 3회 + training 37회 + held-out initial/refined 6회다. 총 2,300,000 shots와 276회 batch diagonalization을 수행했다. 모든 기록된 projected residual이 1e-6 Ha 아래였고 state norm 및 reference 적분 일치 검사도 통과했다. Reference는 이전 refined FCI를 재사용했으며 재계산 비용을 이번 실행 시간에 포함하지 않았다.

## 비용과 종료 상태

전체 wall time 약 140.65초, process lifetime peak RSS 약 1605.86 MiB다. 초기화, probe, 훈련, final 평가 및 기록 비용을 포함하며 초기 Python import는 timer 밖이다. 측정은 단일 스레드이며 OpenMP 미지원 경고가 있었다. 시간은 단일 실행 관측값이고 speedup 주장에 사용하지 않는다.

Run status는 success로 실행 검사가 통과했다는 의미이며 optimizer_status는 **budget_exhausted**다. 수렴 tolerance에 도달했다고 해석하지 않는다. Gain과 예산은 사전 고정한 첫 pilot 값이며 강한 baseline의 최적 설정을 확립한 것은 아니다.

## 검증과 기록

SPSA step의 quadratic objective 방향과 step cap을 검사하는 테스트를 추가해 총 9개가 통과했다. 원본 결과는 results/phase3_20261103T074031/report.json이다. Source snapshot, initial/best/current parameters와 iteration별 RNG state를 보존했다. 모든 평가의 seed·시간·energy·dimension·batch residual history를 기록했다. 전이 의존성까지의 lock은 없으며 직접 의존성 버전을 report에 추가했다. 버전/revision/hash metadata는 같은 환경에서 실행 종료 후 추가했음을 report에 명시했다.

Git 추적 요약은 phase3_summary.json이다. 자동 resume은 아직 제공하지 않는다. Candidate checkpoint와 RNG state는 보존하지만 중단 시 이어 실행하는 검증은 별도 필요하다.

## 다음 단계

Phase 3의 첫 단일 지점 검증은 완료했다. 전체 baseline을 확립하려면 optimizer RNG/훈련 seed를 바꾼 독립 반복, 예산에 따른 정확도 곡선, 추가 geometry를 검증해야 한다. 이 과정에서 sampling/solver 조건을 통제하고 최종 평가 비용까지 포함한다. 아직 Phase 4 warm-start 비교나 Meta 학습으로 넘어가지 않는다.

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/run_phase3.py
```

선행 reference와 integral archives가 필요한 로컬 재현 명령이다.
