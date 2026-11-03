# Multi-Stage Compression Results

실행일: 2026-11-03. **Phase 2 진입 보류.** Multi-stage compression이 압축 수렴이나 최종 SQD 정확도를 개선한다는 증거를 얻지 못했다.

## 검증과 설정

설정은 results/initialization_20261103T071730/source_snapshot/configs/multistage_comparison.json이다. N₂ 1.2 Å, 6-31G, active (10e,16o), frozen core 2, 1-layer 최종 ansatz, 동일한 locality 및 t₁ final rotation을 유지했다. 4→3→2→1항으로 단계별 압축하고 각 단계 결과를 다음 초기값으로 사용했다. Library의 public lower API로 각 단계 결과를 보존한다. 이는 별도의 제안 알고리즘이 아니라 기존 multi-stage 절차의 진단용 실행이다.

각 단계 maxiter=10,000, ftol=1e-12, gtol=1e-7, regularization=0이다. SQD budget, seeds 12345/23456/34567, shots 10,000/50,000은 이전 비교와 같다. Single-stage보다 최대 총 optimization 예산이 크므로 equal-compute 비교가 아니다. Fitting objective는 amplitude loss이며 SQD objective가 아니다.

작은 H₂에서 ffsim의 multi_stage_start=2/multi_stage_step=1 constructor와 최종 state가 일치하는 테스트를 추가했다. 전체 테스트 7개가 통과했다. 설치된 ffsim은 JAX x64를 켜고 있음을 별도 확인했으므로 기본 float32 사용이 미수렴 원인이라는 근거는 없다.

## 단계별 결과

| 압축 항 수 | Iterations | Fitting loss | Gradient norm | 수렴 |
| --- | --- | --- | --- | --- |
| 4 | 10,000 | 0.00139110 | 0.000529 | 아니오: 반복 한도 |
| 3 | 10,000 | 0.00266422 | 0.00218 | 아니오: 반복 한도 |
| 2 | 10,000 | 0.00570760 | 0.000402 | 아니오: 반복 한도 |
| 1 | 10,000 | 0.02137577 | 0.00186 | 아니오: 반복 한도 |

모든 단계가 반복 한도에 도달했다. 서로 다른 항 수의 loss는 표현 용량이 달라 직접적인 optimizer 진행도 비교가 아니다. 최종 1항 loss 0.02137577은 이전 single-stage 0.01514719보다 크다. 손실과 SQD 에너지를 별도로 평가했으며, 낮은 loss가 항상 더 낮은 SQD 에너지를 보장한다고 가정하지 않았다.

## SQD 결과

Refined FCI -109.09813082054681 Ha 대비 seed 3개의 평균 ± 표본 표준편차다. Single-stage 행은 이전 실험 결과를 함께 표시한 것이다.

| 방법 | Shots | SQD 오차 (mHa) |
| --- | --- | --- |
| Single-stage | 10,000 | 48.817 ± 1.147 |
| Single-stage | 50,000 | 44.970 ± 1.268 |
| Multi-stage | 10,000 | 50.428 ± 4.399 |
| Multi-stage | 50,000 | 49.580 ± 0.246 |

Multi-stage는 이번 조건에서 개선되지 않았다. Shots를 늘려도 평균 오차 개선이 작고 seed별 단조 개선은 보장되지 않았다. 모든 sample은 입자수 조건을 만족했고, 모든 SQD batch projected residual은 1e-6 Ha 아래였다. 따라서 작은 projected-space 수치 오차와 큰 전체-space 에너지 오차를 구분해야 한다. 반복 압축 미수렴을 SQD solver 실패로 표현하지 않는다.

## 시간과 메모리

Multi-stage 초기화 42.104초, state preparation 1.142초다. 이전 single-stage 초기화는 5.328초였다. 전체 실행 53.203초, lifetime process peak RSS 1672.92 MiB (약 1.63 GiB)다. 전처리·baseline·12개 seed/shot 결과를 포함하지만 FCI reference 재계산은 포함하지 않는다. 이전 실행의 약 5 GiB peak와 달리 이번에는 FCI를 재계산하지 않았으므로 peak를 직접적인 알고리즘 메모리 절감으로 해석하지 않는다.

기준 에너지는 이전 refined FCI report에서 재사용했다. 분자/계산 조건, HF total 및 저장된 h1/eri/ecore 배열의 일치(절대 tolerance 1e-10)를 확인했고, reference convergence와 residual 기준도 검사했다. Reference 비용을 없다고 주장하지 않고 재사용 provenance를 저장했다.

## 기록과 해석

원본: results/initialization_20261103T071730/report.json. 결과 폴더에 source snapshot, parameter arrays, 모든 samples 및 batch history를 저장했다. Git 추적 요약은 docs/experiments/multistage_summary.json이다. 전체 status는 validation_incomplete이며 실패한 단계를 삭제하거나 success로 바꾸지 않았다.

이번 실험은 해당 schedule과 예산의 부정적 결과다. Multi-stage 일반의 실패, LUCJ 표현력의 절대 한계, meta 초기화 가설의 실패를 입증하지 않는다. 기존 baseline도 예산 내 미수렴 상태이므로 아직 최적화된 label로 취급할 수 없다.

## 다음 작업과 Phase 2 판단

Phase 2는 시작하지 않았다. 다음은 큰 sweep이 아니라 압축 objective의 gradient, parameter scale, optimizer trajectory와 norm 증가를 진단하는 작은 실행이다. 원인을 분리한 후 문헌의 norm regularization 또는 초기값 전략을 별도 실험으로 검토한다. Tolerance 완화나 반복 한도 증가만으로 수렴 성공을 만들지 않는다. 이후 진단용 sweep을 허용하려면 미수렴 baseline의 취급과 비용 예산을 명시적으로 다시 결정해야 한다.

## 재현

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/compare_initialization.py --config results/initialization_20261103T071730/source_snapshot/configs/multistage_comparison.json
```

로컬 reference report와 integral archive가 필요하다. 새 환경에서 해당 기록이 없으면 초기 Phase 1 및 single-stage 기준 계산을 먼저 재생성하고 경로를 설정해야 한다.
