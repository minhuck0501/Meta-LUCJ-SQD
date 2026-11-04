# Phase 5 — Orbital Correspondence and Parameter Representation

실행일: 2026-11-04. 세 geometry와 인접 양방향 네 쌍에서 표현 문제를 진단했다. **오비탈 대응 변화와 Jastrow 좌표의 비유일성을 확인했으며, raw parameter regression을 곧바로 적용할 근거는 부족하다. Meta 학습은 수행하지 않았다.**

## 분석 데이터와 범위

N₂ 1.0/1.2/1.6 Å의 독립 12회 refinement best를 사용했다. 같은 source best에 각 전달 규칙을 적용하고 target에서 추가 최적화 없이 50,000 shots, seeds 89012/90123/101234, 기존 SQD batch/solver 조건으로 평가했다. Phase 4 chain의 누적 history와 source 품질을 분리하기 위해 독립 source를 고정했다. 따라서 이번 값은 Phase 4의 refinement 후 수치와 동일한 실험이 아니며 대체하지 않는다.

Target independent state는 fidelity/분포 TV를 평가할 때만 사용했다. Mapping은 HF orbital overlap에서 계산하며 target optimized parameters를 학습하거나 선택하지 않았다. 이 세 geometry와 seeds는 development pilot 데이터이며 최종 test가 아니다.

## 오비탈 대응

O=C_source† S_cross C_target의 diagonal, singular values 및 |O|² 최대 assignment를 계산했다. Assignment는 순열 진단이며 직접 parameter permutation에 사용하지 않았다.

| 거리 쌍 (Å) | 같은 index의 평균 절대 overlap | Assignment 후 평균 절대 overlap | 최소 singular value |
| --- | --- | --- | --- |
| 1.0↔1.2 | 0.632 | 0.879 | 0.730 |
| 1.2↔1.6 | 0.634 | 0.768 | 0.294 |

같은 index의 overlap이 거의 0인 오비탈도 있고 permutation/축퇴공간 변화와 일관된 큰 offdiagonal overlap이 있다. Assignment 후에도 overlap이 1이 아니며, 1.2↔1.6 Å의 최소 singular value는 약 0.294다. 유한 basis/active orbital spaces 사이의 overlap은 unitary가 아니므로 단순한 gauge change로 전부 설명하지 않는다. 모든 차이를 순열 때문이라고 확정하지 않는다.

## 전달 규칙과 수학적 의미

- Sign: Phase 4와 동일한 index별 부호 D, 내부 회전 U→DUD 및 final rotation의 같은 변환.
- Full polar: G=polar(O†), final rotation F→GF. 전체 occupied/virtual mixing을 허용한다.
- Block polar: O의 occupied/virtual diagonal blocks에서 각각 polar를 계산해 block-diagonal G를 만든다. HF occupied/virtual partition을 보존한다.

Final rotation의 왼쪽에 G를 곱하면 ansatz 내부 locality를 바꾸지 않고 Γ(G)|ψ>를 정확히 표현한다. 하지만 서로 다른 geometry의 overlap을 unitary로 근사하는 선택 자체는 approximate transport 제안이다. 특히 full polar는 physical state를 동일하게 보존하는 harmless preprocessing이 아니다. Block polar도 geometry 간 정확한 파동함수 대응이나 유일한 최적 정렬을 보장하지 않는다.

Full polar/sign의 첫 결과를 확인한 뒤 occupied/virtual mixing을 분리하려고 block polar를 추가했다. 따라서 세 방법의 비교는 탐색적 후속 진단이며 사전 등록한 최종 성능 비교가 아니다. 이 데이터를 보고 geometry마다 가장 유리한 규칙을 선택하지 않았다.

## 전달 직후 SQD 오차

추가 refinement 없이 FCI 대비 평균 ± sampling seed 표본 표준편차다.

| 전달 (Å) | Sign (mHa) | Full polar (mHa) | Block polar (mHa) |
| --- | --- | --- | --- |
| 1.0→1.2 | 53.79 ± 2.38 | 35.78 ± 2.38 | 31.55 ± 1.11 |
| 1.2→1.6 | 81.66 ± 3.67 | 58.27 ± 1.48 | 57.02 ± 0.73 |
| 1.6→1.2 | 60.23 ± 4.92 | 65.19 ± 4.17 | 45.97 ± 3.48 |
| 1.2→1.0 | 57.80 ± 7.73 | 38.23 ± 3.93 | 28.50 ± 2.75 |

Block polar는 이번 네 쌍에서 sign보다 낮은 오차를 보였다. Full polar는 세 쌍에서 개선됐지만 역방향 한 쌍에서는 개선되지 않았다. Target independent best와의 fidelity가 높다고 SQD energy가 반드시 더 낮지는 않았다. Fidelity의 비교 대상도 exact ground state가 아니라 제한된 예산의 approximate best다. 따라서 fidelity나 raw parameter 오차를 최종 학습 목적의 충분한 대체 지표로 삼지 않는다.

## 비유일성과 차원

AB diagonal Jastrow entry 하나에 2π를 더했을 때 N₂ state L2 difference는 6.21e-16이었다. Source parameter는 2π 달라져도 같은 물리 상태가 되는 직접적인 예다. 이는 해당 검증된 J 좌표의 성질이며 모든 orbital-rotation packing 좌표에 동일한 주기를 가정하면 안 된다.

세 raw parameter vectors를 중심화한 singular values는 약 5.667, 5.460, 2.21e-15였다. Rank≤2는 표본이 세 개여서 생기는 수학적 한계이며 low-dimensional learnability의 증거가 아니다. 앞 두 singular values도 비슷해 지배적인 한 방향을 발견했다고 주장할 수 없다. Gauge를 고정하지 않은 parameter PCA를 물리적 매끄러움의 증명으로 사용하지 않는다.

## 검증, 자원, provenance

Nontrivial state에서 output rotation의 정확한 상태 관계, Jastrow periodicity, block rotation의 unitarity와 HF occupation 보존을 검증했다. 전체 테스트 12개가 통과했다. N₂ periodicity, state norm 및 총 36개 SQD 평가의 projected residual <1e-6 Ha 검사도 통과했다. 재최적화는 수행하지 않았다.

두 실행 wall time 합은 76.58초, 최대 lifetime process RSS는 2028.19 MiB다. Geometry 준비·전달·state/metric 계산·sampling/SQD와 기록을 포함하고 initial import 및 기존 independent/FCI 생성 비용은 제외한다. 이 진단의 시간만으로 warm-start 비용 이점을 주장하지 않는다.

원본은 results/phase5_20261104T063952/report.json과 results/phase5_20261104T064143/report.json이다. Configuration/source snapshot, 재구성 MO coefficients, polar rotations, overlap assignment, raw parameter SVD, state metrics 및 batch histories를 저장했다. 과거 independent run에 MO archive가 없어 같은 로컬 환경에서 재구성한 한계는 유지된다. 동일 환경의 직접 의존성 버전은 실행 후 phase5_summary.json에 수집했다고 명시했다.

## 다음 단계

Phase 5의 첫 표현 진단을 완료했다. Sign-only Phase 4 baseline을 강한 비교군으로 쓰기 전에, 고정 block-polar 규칙으로 같은 예산의 warm-start 비교를 다시 검증할 필요가 있다. Meta 회귀에는 공통 orbital frame과 unitary/Jastrow encoding, 주기성·내부 gauge 처리 규칙이 필요하다. 이번에는 internal gauge 전부의 canonicalization이나 geometry split을 확정하지 않았으므로 raw 531차원 숫자 회귀를 바로 시작하지 않는다.

가능한 다음 실험은 사전 고정한 block-polar warm-start 재평가다. 그 후 작은 Meta pilot의 train/validation/unseen geometry를 새로 구분하고, 단순 affine model부터 SQD energy와 전체 비용으로 평가한다. 이 결과를 Meta 일반화의 증거로 부르지 않는다.

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/run_phase5.py
```

현재 기본 설정은 세 방법 모두다. 기록된 첫 실행은 sign/full polar만, 후속 실행은 --methods block_polar로 계산했다. 기존 independent/reference archives가 필요하다.
