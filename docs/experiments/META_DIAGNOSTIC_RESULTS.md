# Frozen Meta Model — Training Reconstruction and Distribution Diagnosis

실행일: 2026-11-04. **Affine 모델은 미학습 geometry뿐 아니라 학습 지점에서도 일부 label 상태를 충분히 재구성하지 못했다. Exact feature decode control은 통과했으므로 관측된 차이를 decoder의 단순 수치 오류로 설명할 근거는 없다.** 모델이나 hyperparameter를 변경하지 않았다.

## 분리한 질문

1. 원래 학습 feature를 decode/inverse frame하면 원래 state가 복원되는가?
2. Frozen affine prediction은 학습 state와 얼마나 다른가?
3. 내부 unitary/Jastrow feature의 projection은 얼마나 큰가?
4. 같은 fresh sampling seeds에서 label/prediction의 SQD 오차는 어떻게 달라지는가?
5. 기존 unseen predictions의 분포는 control과 어떻게 다른가?

configs/meta_diagnostic.json의 고정 seed 445566/556677/667788, 50,000 shots 및 기존 batch/solver 조건을 사용했다. Label/prediction 모두 같은 seeds에서 비교했다. Unseen 1.1/1.4 Å는 저장된 세 방법의 parameter states만 분석했고 새 모델을 선택하지 않았다. Approximate label이나 baseline state는 exact ground state가 아니다.

## 학습 지점의 재구성

| 학습 거리 (Å) | Exact feature roundtrip L2 error | Affine state fidelity to label | 확률 TV |
| --- | --- | --- | --- |
| 1.0 | 9.36e-15 | 0.9219 | 0.0537 |
| 1.2 | 1.08e-14 | 0.7207 | 0.1031 |
| 1.6 | 1.13e-14 | 0.9701 | 0.0617 |

Exact feature control은 세 지점 모두 tolerance=1e-10 아래다. 모델의 prediction은 다른 feature를 출력하고 decode projection을 거쳐 다른 state가 됐다. 이는 고정한 affine 모델/표현에서의 training reconstruction 한계다. Label 자체의 비유일성, 비선형 feature 변화, 남은 gauge와 projection 중 어느 것이 주된 원인인지 완전히 분리한 것은 아니다.

## 학습 지점 SQD

같은 fresh sampling seeds 3개의 FCI 대비 평균 ± 표본 표준편차다. 이전 실험의 다른 seeds 평균과 직접 같은 수치일 필요는 없다.

| 학습 거리 (Å) | Optimized label (mHa) | Affine prediction (mHa) |
| --- | --- | --- |
| 1.0 | 23.82 ± 0.84 | 33.71 ± 2.15 |
| 1.2 | 36.02 ± 0.91 | 46.96 ± 7.35 |
| 1.6 | 53.77 ± 2.10 | 53.30 ± 3.86 |

1.0/1.2 Å에서는 affine prediction의 평균 오차가 약 10–11 mHa 높았다. 1.6 Å의 차이는 sampling 변동보다 작아 우열을 단정하지 않는다. Fidelity, feature MSE와 SQD energy를 동일하게 취급하지 않는다.

## Projection 진단

각 predicted complex matrix를 unitary로 투영하기 전 ||M†M−I||F, 최소 singular value와 ||polar(M)−M||F를 측정했다.

| 거리 (Å) | 내부 U 최소 singular value | 내부 U projection 거리 | Final F projection 거리 |
| --- | --- | --- | --- |
| 1.0 | 0.335 | 1.251 | 0.00244 |
| 1.2 | 0.118 | 1.971 | 0.00398 |
| 1.6 | 0.643 | 0.792 | 0.00204 |

특히 내부 U의 선형 평균이 unitary manifold에서 크게 벗어났다. Final F와 비교해 projection 거리가 크므로 내부 회전 표현/회귀를 우선 조사할 근거다. 다만 projection은 제약을 지키기 위해 필요하며, projection 자체가 유일한 오류 원인이라는 증명은 아니다. J cos/sin도 unit circle에서 일부 벗어났지만 0에 가까운 undefined pair는 없었다.

## Unseen 상태 분포

HF probability, Shannon entropy와 inverse participation을 전체 fixed-particle-number 확률에서 계산했다. Entropy가 크거나 configurations가 다양하다고 SQD가 반드시 더 정확한 것은 아니다. 예를 들어 1.4 Å Meta의 entropy는 약 2.406 bits로 warm의 1.494 bits보다 높지만, 기존 SQD 오차는 Meta 59.85 mHa로 warm 43.64 mHa보다 컸다. 중요한 configuration의 선택이 핵심이며 단순 다양성만 최적화하면 안 된다.

Unseen Meta와 control 사이 fidelity/TV는 원본 report에 저장했다. 이는 approximate state 간 유사도이고 ground-state overlap의 측정이 아니다.

## 비용, 검증, 기록

진단 wall time 47.36초, process lifetime peak RSS 2307.48 MiB다. 학습 지점의 추가 SQD 평가는 18회, 900,000 shots다. Exact control 복원과 모든 SQD projected residual <1e-6 검사를 통과했다. 기존 FCI와 model archives를 재사용했으며 새 FCI/학습/최적화는 하지 않았다.

원본: results/meta_diagnostic_20261104T072047/report.json. 설정과 source snapshot, per-seed energy, projection, 확률 및 fidelity 진단을 저장했다. 추적 요약은 meta_diagnostic_summary.json이다. 이번 작업은 분석 도구 추가로 production 모델을 바꾸지 않았다. 기존 solver와 representation 수치 검증은 유지하며, 새 hyperparameter 탐색은 하지 않았다.

## 다음 연구 선택

현재 근거는 큰 neural network보다 training reconstruction과 unitary representation을 먼저 다뤄야 함을 보여준다. 다음 통제 실험 후보는 학습점을 정확히 재현하는 local/manifold interpolation을 baseline으로 추가하는 것이다. 그것이 affine underfitting을 분리하는 대조군이 될 수 있지만, 미학습 geometry에서 좋아질지는 검증해야 한다.

새 모델을 시도하면 1.1/1.4 Å는 이미 분석에 사용한 development 데이터로 취급하고, 최종 비교에는 새로운 geometry/seeds를 사전에 남겨둔다. SQD energy·동일 예산 baseline·label/학습 overhead가 여전히 주 평가 기준이다. Phase 7 전체 benchmark는 아직 아니다.

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/diagnose_meta.py
```
