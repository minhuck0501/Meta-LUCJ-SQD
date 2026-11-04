# Block-Polar Warm-Start Recheck and Common Representation

실행일: 2026-11-04. **Block-polar는 sign-only보다 네 구간 모두 평균 오차가 낮았지만, 독립 최적화 대비 개선은 방향에 따라 달랐다. Meta 모델은 학습하지 않았다.**

## 사전 고정 조건

configs/phase4_block.json에 block-polar를 모든 구간의 규칙으로 고정했다. 1.0→1.2→1.6 Å와 역방향에서 이전 best를 전달하며 각 target은 같은 12회 SPSA, 50,000 shots, gain·step cap·training/evaluation seeds 및 SQD solver 조건을 사용했다. 첫 점은 기존 independent endpoint를 재사용했고 생성 비용도 chain 비용에 포함했다.

규칙은 Phase 5 탐색 결과를 보고 선택했다. 이번 geometry와 sampling seeds도 동일한 개발 pilot 데이터이므로 독립적인 최종 method-selection test가 아니다. 거리별 결과로 규칙이나 방향을 사후 선택하지 않았다.

## 추가 최적화 후 SQD 오차

각 칸은 FCI 대비 sampling seed 3개의 평균 ± 표본 표준편차다. 각 방향의 optimizer trajectory는 하나다.

| 거리 (Å) | Independent (mHa) | 증가 방향 block-polar (mHa) | 감소 방향 block-polar (mHa) |
| --- | --- | --- | --- |
| 1.0 | 23.47 ± 0.89 | 독립 첫 점 재사용 | 36.19 ± 5.04 |
| 1.2 | 36.62 ± 3.05 | 30.96 ± 0.44 | 41.15 ± 1.98 |
| 1.6 | 54.52 ± 3.39 | 50.31 ± 3.88 | 독립 첫 점 재사용 |

증가 방향은 두 target에서 independent보다 평균 오차가 낮았고, 감소 방향은 두 target에서 높았다. 효과 크기와 sampling 변동을 함께 보아야 하며 통계적 유의성이나 일반적인 우위를 주장하지 않는다. 목표 정확도는 아직 달성하지 못했다.

## 이전 sign-only와 비교

| 방향/target | Sign-only (mHa) | Block-polar (mHa) |
| --- | --- | --- |
| 증가 / 1.2 Å | 43.70 | 30.96 |
| 증가 / 1.6 Å | 83.50 | 50.31 |
| 감소 / 1.2 Å | 44.64 | 41.15 |
| 감소 / 1.0 Å | 54.25 | 36.19 |

이번 동일 예산의 평균 결과에서 개선을 관측했다. 오비탈 대응 처리가 결과에 영향을 준다는 증거이며, 기존 큰 오차의 유일한 원인을 증명한 것은 아니다. Phase 5의 추가 refinement 없는 zero-shot 진단과 이번 chain refinement 결과를 구분한다.

## 비용과 검증

- 증가 방향의 endpoint 포함 child wall time 합: 404.37초.
- 감소 방향의 endpoint 포함 child wall time 합: 388.38초.

새 네 target의 orchestration wall time은 518.78초다. 각 target 46회로 총 184 objective evaluations와 9,200,000 shots를 사용했다. 기존 endpoint/FCI 생성 비용은 신규 실행 시간에 중복 합산하지 않았으나 chain 비용과 provenance에는 포함했다. Source chemistry 재구성 및 transfer 비용도 target timer에 포함한다.

표현 검증과 테스트가 실행 일부에 겹쳤고 시간 측정은 각 한 번이므로 미세한 runtime 차이나 speedup을 주장하지 않는다. 모든 run이 norm/reference consistency/SQD projected residual 검사를 통과했다. Optimizer는 모두 budget_exhausted이며 수렴한 결과로 부르지 않는다. 전체 수치 테스트 14개가 통과했다.

## 공통 표현 검증

1.2 Å anchor를 training 기준으로 고정한 표현 후보를 구현했다. Block-frame conjugation은 내부 U→GU, final F→GFG†이며 J는 유지한다. 내부 column phase를 제거하고 회전행렬 real/imag 및 J의 cos/sin을 저장한다. Decode 후 inverse frame에서 원래 state를 복원하는 검증을 세 geometry에서 통과했다.

Features는 1062개이며 raw 531보다 많은 redundant embedding이다. State L2 roundtrip error는 최대 약 1.13e-14다. 이것은 정보 보존 검증이지 model learnability 증거가 아니다. Internal permutations, degenerate gauge, final global phase와 anchor 의존성을 모두 없앤 유일 표현도 아니다. 상세한 수식·한계·train/test 원칙은 ../META_REPRESENTATION.md에 있다.

## 기록과 다음 단계

Warm 원본: results/phase4_20261104T064917/report.json. 표현 원본: results/representation_20261104T065315/report.json. 설정·source snapshot·MO/rotation·parameter/RNG checkpoint·SQD histories와 features.npz를 저장했다. 추적 수치는 phase4_block_summary.json, representation_summary.json이다. 최초 output-only draft는 보존하지만 현재 전체-frame schema와 섞지 않는다.

다음은 Phase 6의 작은 Meta pilot을 이 고정 표현에서 검토하는 것이다. 이미 사용한 세 구조는 개발 training 후보이며 anchor를 train에 포함해야 한다. 새로운 interpolation geometry를 별도로 정하고, 단순 affine/ridge 모델의 SQD energy와 학습/label 생성 overhead를 평가한다. 이 문서의 결과를 미관측 geometry 일반화나 Meta 효율성 입증으로 부르지 않는다. 이번 작업에서는 Meta fitting을 수행하지 않았다.

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/run_phase4.py --config configs/phase4_block.json
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/build_representation.py
```
