# Compression Diagnosis and Regularization Results

실행일: 2026-11-03. **압축의 gradient 수렴을 확인했다. 목표 에너지 정확도나 Meta 비용 이점은 미입증이다.**

## 진단

기존 미수렴을 재현하는 별도 실행에서 2,000회까지 loss, gradient L2/∞ norm 및 parameter norm을 매 iteration 기록했다. 동일 초기점에서 L-BFGS-B와 BFGS를 비교했으며 둘 다 반복 한도에 도달했다. 5개의 고정 seed random unit directions, central difference steps 1e-4/1e-5/1e-6으로 gradient를 검사했다. 초기 최대 absolute directional error는 1.30e-11이었다. 2,000회 종료점의 최대 오차는 L-BFGS-B 1.96e-9, BFGS 2.27e-8로 해당 gradient 크기에 비해 작았다. 이 유한 지점 검사는 모든 좌표와 모든 점의 correctness 증명은 아니지만 gradient 구현 오류의 증거를 발견하지 못했다.

대신 Jastrow matrix 제곱 norm이 full factorization의 0.2112184에서 2,000회 진단 종료점의 L-BFGS-B 547.27, BFGS 6541.24로 커졌다. Parameter norm도 각각 약 19.68/65.52로 증가했다. 이는 작은 amplitude fitting 오차를 위해 큰 계수를 사용하는 경로를 관측한 것이다. Hessian condition number를 계산하지 않았으므로 ill-conditioning의 유일한 원인이나 엄밀한 원인 증명으로 표현하지 않는다.

원본 진단은 results/compression_diagnostic/report.json에 있다. 진단 도구는 설치 버전으로 고정된 ffsim의 private objective를 사용하므로 library upgrade 시 재검증해야 한다.

## 수정한 방법

LUCJ 초기화 논문의 norm regularization과 설치된 ffsim 구현에 따라 다음 목적함수를 사용한다.

L = 0.5 ||t₂_reconstructed − t₂_CCSD||² + λ |Σμ ||Jμ||² − Σμ ||Jμ_initial,full||²|

λ=0.001의 단일 진단 후보를 configs/regularized_comparison.json에 명시했다. 이는 기존 목적함수의 수치 버그 수정이 아니라 문헌에 근거한 목적함수 변경이다. 과거 regularization=0 결과는 유지했다. Topology, 1-layer, final rotation, seeds, sample/SQD 예산은 변경하지 않았다. 합집합 mask에서 fitting한 후 spin별 mask를 적용하는 절차도 유지한다.

Library optimizer를 재구현하지 않고 기존 public API의 regularization 인수를 연결했다. 별도 작은 H₂ 테스트에서 library 고수준 constructor와 최종 상태가 일치했다.

## 수렴 결과

- L-BFGS-B는 5,290 iterations/5,523 evaluations에서 gradient 기준으로 종료했다.
- Gradient ∞ norm: 7.79e-8, 기존 gtol=1e-7 아래다. L2 norm은 4.89e-7이다. 서로 다른 norm의 기준을 혼동하지 않는다.
- 최종 J 제곱 norm: 1.2898589.
- 최종 목적함수: 0.01589538. Regularization 포함 값이므로 이전 unregularized loss와 같은 양으로 직접 비교하지 않는다.
- 별도 trajectory 진단에서도 같은 종료점이 재현됐으며, 종료점 directional gradient 최대 absolute error는 1.59e-11이었다.

기존 tolerance를 완화하지 않았다. 이는 해당 regularized objective의 한 stationary solution에 대한 검증이며 global optimum을 보장하지 않는다. Norm penalty의 absolute value는 기준 norm과 같은 곳에서 미분 불가능하지만 관측된 최종점은 그 지점과 다르다.

## SQD 결과

같은 N₂ 1.2 Å의 refined FCI 대비 seed 3개 평균 ± 표본 표준편차다.

| 방법 | 10,000 shots 오차 | 50,000 shots 오차 |
| --- | --- | --- |
| Unregularized single-stage, 미수렴 | 48.82 ± 1.15 mHa | 44.97 ± 1.27 mHa |
| Regularized single-stage, 수렴 | 55.42 ± 3.97 mHa | 44.25 ± 3.19 mHa |

수렴은 개선됐지만 SQD 에너지가 일관되게 좋아진 것은 아니다. 50,000 shots에서의 평균 차이는 표본 변동성과 비교할 때 작고, 10,000 shots에서는 평균 오차가 증가했다. Regularization을 에너지 정확도 개선이나 speedup으로 주장하지 않는다. 12개 SQD 실행은 projected residual <1e-6 검사를 통과했다. Particle number, norm 및 reference 재사용 검사도 통과했다.

## 비용과 기록

초기화는 약 3.05초, 전체 비교는 약 15.11초, process lifetime peak RSS는 1602.72 MiB다. 이는 전처리, truncated control 및 12개 sample/SQD 실행을 포함하고 FCI 재계산 및 별도 gradient 진단/테스트 시간은 제외한다. 별도 regularized trajectory 진단은 약 5.56초였다. 기준 FCI 비용은 이전 실험 기록에 있으며 원본 적분과 조건을 검사해 재사용했다.

원본은 results/initialization_20261103T072303/report.json, regularized trajectory는 results/regularized_diagnostic/report.json이다. 설정·source snapshot·parameter·sample 배열과 batch history를 저장했다. Git 추적 수치는 docs/experiments/regularized_summary.json에 있다. 전체 테스트는 8개이며 OpenMP 미지원 경고는 그대로 기록한다.

## Phase 2 판단

이제 **소규모 진단용 Phase 2로 진행할 근거는 확보됐다.** 이전 보류 사유였던 미수렴 초기화와 불명확한 수렴 원인에 대해 gradient 검증, norm 증가 진단, 문헌 기반 완화, 실제 gradient 수렴 및 자원 측정을 완료했기 때문이다. 이는 약 44 mHa의 오차를 최종 목표 정확도로 수용한다는 뜻이 아니다.

후속 단계는 소수 geometry에서 이 pilot 설정의 수렴과 sampling/energy 변화를 조사하는 것으로 제한한다. 고정 λ=0.001은 최종 최적값이 아니라 한 지점에서 선택한 pilot 설정이다. Geometry sweep에서 실패·오차를 그대로 기록해야 하며 실패를 숨기거나 geometry별 유리한 설정을 사후 선택하지 않는다. 대규모 benchmark, meta training 및 효율성 주장은 아직 진행 조건이 갖춰지지 않았다. 이번 turn에서는 geometry sweep을 실행하지 않았다.

## 재현

```bash
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/diagnose_compression.py --config results/initialization_20261103T072303/source_snapshot/configs/compression_diagnostic.json
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/diagnose_compression.py --config configs/regularized_diagnostic.json
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/compare_initialization.py --config configs/regularized_comparison.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q
```

기존 amplitude 및 reference archives가 필요하다. 없어졌다면 앞선 Phase 1 결과부터 재생성해야 한다. 진단 output_directory는 재실행 시 덮어쓸 수 있으므로 별도 실험에는 새로운 경로를 설정한다.
