# Phase 2 — Small Geometry Sweep

실행일: 2026-11-03. 소규모 진단 sweep 3지점이 모두 수치 검증을 통과했다. 전체 dissociation curve, 일반화 성능, 목표 정확도 또는 Meta 비용 절감을 입증한 실험은 아니다.

## 설정

N₂ 1.0/1.2/1.6 Å, 6-31G, frozen core 2, active (10e,16o), 1-layer spin-balanced LUCJ와 같은 locality/t₁ final rotation을 유지했다. 각 구조에서 독립 SCF/CCSD 초기화를 사용했다. Truncation control과 λ=0.001 regularized compression을 비교한다. 압축 maxiter=10,000, ftol=1e-12, gtol=1e-7을 모든 구조에서 고정했다. Seed는 12345/23456/34567이며 각 50,000 shots, 200 samples/batch, 3 batches, 최대 2 SQD iterations다. Solver tolerance는 1e-13, 최대 200 cycles다. 설정은 configs/phase2.json 및 configs/regularized_comparison.json에 있다.

Warm start, geometry별 설정 선택, orbital alignment 및 meta 학습은 수행하지 않았다. 1.2 Å는 이전 pilot 재현이고 나머지 2개가 새 geometry다. 이 세 지점은 최종 test set으로 간주하지 않는다.

## 결과

오차는 각 구조의 FCI total 대비 seed 3개 평균 ± 표본 표준편차다.

| 거리 (Å) | 단순 초기화 오차 (mHa) | Regularized 압축 오차 (mHa) | 압축 iterations | 수렴 |
| --- | --- | --- | --- | --- |
| 1.0 | 142.10 ± 4.69 | 35.48 ± 1.59 | 2699 | 통과 |
| 1.2 | 162.89 ± 5.88 | 44.25 ± 3.19 | 5290 | 통과 |
| 1.6 | 191.92 ± 17.54 | 65.44 ± 3.84 | 5859 | 통과 |

SCF, CCSD, regularized compression, FCI convergence 검사를 세 지점 모두 통과했다. 총 18개 method/seed 실행의 sample particle number와 norm 검사 및 모든 batch projected residual <1e-6 Ha 검사도 통과했다. 1.2 Å의 결과가 이전 측정과 일치했다. 압축의 더 낮은 오차가 곧 accuracy-matched speedup을 의미하지 않는다.

## Reference와 자원

새 거리의 FCI tolerance는 1e-11 Ha, max_cycle=100이다. 1.2 Å는 물리 설정·HF 에너지·적분 일치 검사를 거쳐 기존 refined reference를 재사용했다. 각 reference residual은 1e-5 Ha 미만이다. 이는 certified energy uncertainty를 제공하지 않으며 미세한 차이를 비교할 때 추가 수렴 검토가 필요하다.

| 거리 (Å) | FCI total (Ha) | FCI residual | 전체 point 시간 (초) | Process peak RSS (MiB) |
| --- | --- | --- | --- | --- |
| 1.0 | -109.04667177832 | 2.73e-06 | 87.33 | 5382.47 |
| 1.2 | -109.09813082055 | 2.99e-06 | 11.82 | 1600.16 |
| 1.6 | -108.94225171073 | 2.99e-06 | 147.10 | 5380.48 |

Sweep orchestration 총 wall time은 249.21초다. 각 point는 별도 process이므로 표의 peak는 point process lifetime peak이며 부모 process를 합친 동시 전체 peak가 아니다. 단일 스레드로 실행했고 기존 OpenMP 미지원 경고를 기록했다. 1.2 Å 시간에는 reference 재계산이 없어 다른 지점과 실행 시간을 직접 비교할 수 없다. 기존 reference 생성 비용은 앞선 보고서에 별도 기록되어 있다. 초기 library import 시간은 child report timer 밖이며 부모 orchestration timer에는 포함된다.

## 해석

고정된 regularization 설정이 이번 세 거리에서 수렴했다. 따라서 단일 지점에서만 동작하는 계산 연결 문제는 관측되지 않았다. 그러나 수십 mHa의 SQD 오차가 남는다. 이 실험은 아직 초기화만 사용했으며 SQD parameter refinement를 수행하지 않았다. 1.6 Å 결과가 전체 stretched-bond/strong-correlation 영역의 안정성을 보장하지는 않는다.

이 소규모 Phase 2는 완료했다. 다음 단계는 Phase 3의 독립 SQD parameter refinement baseline을 설계·검증하여 같은 sampling/solver 조건에서 정확도-비용 관계를 측정하는 것이다. Warm start와 meta learning 비교 전에 optimizer, objective noise, budget과 최종 독립 평가 절차를 고정해야 한다. 현재 결과를 목표 정확도 달성으로 간주하지 않는다.

## 기록과 재현

원본 orchestration report: results/phase2_20261103T073148/report.json. 각 point의 base/comparison 설정 및 execution.log를 같은 디렉터리에 저장했다. 각 child report와 source snapshot, parameter 및 sample arrays 경로는 원본 report에 있다. Git 추적 수치는 phase2_summary.json이다. 수치 테스트 8개가 통과했다. 이번 sweep에서는 timeout·실패·미수렴 point가 없었다.

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/run_phase2.py
```

기존 local reference 파일이 필요한 설정이다. 새 checkout에서는 선행 reference를 재생성해야 한다. 중단 시 완료 point 기록은 보존되지만 자동 resume은 아직 지원하지 않는다.
