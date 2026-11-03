# Meta-LUCJ-SQD

분자 구조에 따라 LUCJ 초기 파라미터를 예측하여, Sample-Based Quantum Diagonalization(SQD)의 에너지 정확도를 유지하면서 전체 계산 비용을 줄일 수 있는지 검증하는 연구 프로젝트입니다.

## 연구 목표

분자의 potential energy curve를 계산하려면 여러 구조에서 전자 에너지를 반복해서 구해야 합니다. 이 프로젝트는 구조마다 독립적으로 LUCJ 파라미터를 최적화하는 대신, 여러 구조에서 얻은 정보를 재사용하는 초기화 방법을 연구합니다.

\[
f_\phi(R) \longrightarrow \theta_{\mathrm{init}}(R)
\]

여기서 \(R\)은 분자 구조, \(\phi\)는 학습 모델의 파라미터, \(\theta_{\mathrm{init}}\)는 LUCJ 계산의 초기 파라미터입니다. 예측 후 필요한 경우 추가 최적화를 수행합니다.

핵심 성공 기준은 **학습하지 않은 구조에서 비슷하거나 더 좋은 SQD 에너지 정확도를 달성하면서, 학습 비용을 포함한 전체 계산 비용을 강한 기존 방법보다 줄이는 것**입니다. 파라미터 예측 정확도만으로 성공을 판단하지 않습니다.

## 계산 흐름

1. 분자 구조에서 전자 Hamiltonian과 필요한 기준 계산을 준비합니다.
2. 기존 초기화 또는 geometry-conditioned 모델로 LUCJ 파라미터를 준비합니다.
3. LUCJ 상태에서 전자 배치를 샘플링합니다.
4. SQD로 선택된 부분공간에서 Hamiltonian을 대각화하여 에너지를 계산합니다.
5. 필요하면 파라미터를 추가 최적화하고 정확도와 비용을 기록합니다.

LUCJ는 샘플링할 근사 양자 상태를 구성하고, SQD는 샘플에서 얻은 전자 배치를 활용해 에너지를 계산합니다. LUCJ 상태의 평균 에너지와 최종 SQD 에너지는 구분해서 평가합니다.

LUCJ와 SQD는 참고 문헌에 기반한 방법입니다. 이 프로젝트에서 검증할 연구 가설은 **geometry-conditioned LUCJ 초기화의 일반화 성능과 계산 비용 절감 효과**입니다. 아직 그 효과를 입증한 실험 결과는 없습니다.

## 초기 benchmark

다음은 연구 지침에 따른 초기 설정이며, 아직 수치 검증을 완료한 설정은 아닙니다.

| 항목 | 초기 설정 |
| --- | --- |
| 분자 | N₂ |
| Basis set | 6-31G |
| Active space | 전자 10개, spatial orbital 16개 |
| Frozen core | Spatial orbital 2개 |
| Active electron 수 | Nα = Nβ = 5 |
| 첫 검증 지점 | N–N 거리 1.2 Å |
| 초기 조사 범위 | 0.8–2.2 Å |
| 확장 후보 | 수치적으로 가능한 경우 3.0 Å까지 |

오비탈 순서, active-space 선택, 핵 반발 에너지, frozen-core 에너지, 적분 변환을 검증한 뒤 범위를 확장합니다. 설정이나 방법론을 변경하면 `docs/DECISIONS.md`에 근거를 기록합니다.

## 비교와 검증 원칙

- 각 구조에서 독립적으로 시작하는 최적화와 비교합니다.
- 이전 구조의 결과를 이어받는 sequential warm start와 비교합니다.
- 학습·검증·테스트 구조를 구분하고 interpolation과 extrapolation을 별도로 평가합니다.
- SQD 에너지 오차, 목적함수 평가 횟수, 샘플 수, 부분공간 크기, 실행 시간, 최대 메모리를 기록합니다.
- 학습 자료 생성과 모델 학습 비용을 포함하고, 비용을 회수하는 break-even point를 평가합니다.
- Seed와 의존성 버전, 실험 설정, 실패 및 수렴 상태를 저장합니다.
- 파라미터 비유일성, 오비탈 gauge, 데이터 누출, stretched-bond 영역의 SCF/CCSD 신뢰성을 점검합니다.
- 작은 결정론적 수치 검증을 먼저 수행하며, 검증 전에 대규모 계산을 실행하지 않습니다.

고전 시뮬레이션에서의 계산 비용 절감과 quantum advantage 주장은 구분합니다.

## 현재 상태

Phase 1의 최소 계산 파이프라인 검증을 수행했습니다. 초기 SQD 정확도 개선이 필요하며 geometry sweep은 시작하지 않았습니다.

실행 설정과 수치 결과는 [Phase 1 결과](docs/experiments/PHASE1_RESULTS.md), [초기화 비교](docs/experiments/INITIALIZATION_COMPARISON.md), [Multi-stage 결과](docs/experiments/MULTISTAGE_RESULTS.md), [압축 진단과 수정 결과](docs/experiments/COMPRESSION_FIX_RESULTS.md)를 참고하세요.

- 프로젝트 디렉터리, 연구 지침, 참고 논문 3편 및 참조 notebook이 준비되어 있습니다.
- 로컬 `.venv`에서 Python 3.11.18과 native ARM64 실행을 확인했습니다.
- NumPy, SciPy, PySCF, ffsim, Qiskit, qiskit-addon-sqd, pytest의 import를 확인했습니다.
- Chemistry/LUCJ/sampling/SQD 최소 구현과 수치 테스트 8개가 통과했습니다.
- N₂ 1.2 Å의 FCI 및 초기 SQD 결과를 측정했습니다. 최초 SQD 오차는 약 189.95 mHa였습니다. 후속 압축 초기화 비교에서는 평균 약 45–49 mHa로 개선됐지만 초기 압축 optimizer는 미수렴이었습니다. 후속 norm regularization으로 gradient 수렴을 확인했으며, 50,000 shots의 평균 오차는 약 44.25 mHa입니다. 소규모 진단 sweep은 진행할 수 있지만 목표 정확도와 Meta 효율성은 미입증입니다.
- 연구 문서 4종에 Phase 0 설계 초안과 참조 notebook 검토 내용을 작성했습니다.
- `pyproject.toml`에 패키지 구성과 현재 직접 의존성 버전을 선언했습니다.
- 직접 의존성 버전을 고정했으며 해당 로컬 환경에서 작은 수치 검증을 수행했습니다. 전체 전이 의존성 lock과 별도 환경 설치 검증은 미완료입니다.

환경 확인은 해당 로컬 환경에 대한 점검이며, 다른 환경에서의 설치나 수치적 정확성을 보장하지 않습니다.

## 개발 단계

1. **연구 설계:** 논문과 notebook을 검토하고 방법론, 비교 조건, 검증 기준을 문서화합니다.
2. **단일 구조 검증:** 작은 문제의 수치 테스트 후 N₂의 1.2 Å 지점에서 chemistry, LUCJ, sampling, SQD를 검증하고 자원 사용량을 측정합니다.
3. **소규모 구조 조사:** 선택한 거리에서 수렴, 에너지, 샘플링 특성을 확인합니다.
4. **기준 방법 구축:** 독립 최적화와 sequential warm start를 통제된 예산으로 비교합니다.
5. **파라미터 분석:** 구조에 따른 연속성, 표현의 비유일성, 정렬과 유효 차원을 조사합니다.
6. **Meta 초기화:** 간단한 회귀 모델부터 시작해 미관측 구조에서 평가합니다. 직접 SQD 목적함수 학습과 혼합 접근은 비용과 근거에 따라 검토합니다.
7. **전체 benchmark:** 정확도, 변동성, 학습 비용 회수, 강상관 영역의 한계를 평가합니다.

## 프로젝트 구조

```text
Meta-LUCJ-SQD/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── references/            # 논문과 참조 notebook
├── docs/                  # 연구 계획, 방법론, benchmark, 결정 기록
├── configs/               # 실험 설정
├── src/meta_lucj_sqd/      # 모듈화된 Python 구현
├── scripts/               # 실행 진입점
├── tests/                 # 수치 검증
├── notebooks/             # 탐색 및 분석
├── results/               # 생성된 실험 결과
└── artifacts/             # 생성된 중간 산출물
```

빈 디렉터리는 Git clone에 포함되지 않을 수 있습니다. 생성 결과는 기본적으로 Git에서 제외하며, 재현에 필요한 설정과 검증된 작은 fixture는 별도로 관리합니다.

## 개발 환경

목표 실행 환경은 Apple Silicon Mac의 CPU 기반 Python 환경입니다. CUDA 또는 Metal/MPS 가속을 전제로 하지 않습니다. BLAS thread 수와 실제 시간·메모리 사용량은 소규모 실행으로 측정합니다.

기존 로컬 환경을 활성화하려면:

```bash
source .venv/bin/activate
python --version
```

Phase 1 테스트와 실행 명령은 [결과 문서](docs/experiments/PHASE1_RESULTS.md)에 있습니다. 실행 결과는 `results/`에 저장됩니다. 현재 단계별 자동 resume과 전체 benchmark CLI는 제공하지 않습니다.

## 참고 자료

`references/`에는 다음 자료가 있습니다.

- *Improved parameter initialization for the (local) unitary cluster Jastrow ansatz*
- *The Meta-Variational Quantum Eigensolver: Learning energy profiles of parameterized Hamiltonians for quantum simulation*
- *Chemistry Beyond the Scale of Exact Diagonalization on a Quantum-Centric Supercomputer*
- `SQD_N2_resetEM.ipynb`

참조 notebook도 검증 대상입니다. 수치 설정과 구현을 자동으로 정답으로 간주하지 않습니다.

## 작업 규칙

세부 지침은 [AGENTS.md](AGENTS.md)를 따릅니다. 정확성과 재현성을 우선하고, 소스 코드에 주석을 작성하지 않으며, 설정과 구현을 분리합니다. 과학적 주장은 실험 근거와 함께 기록하고 실패한 실험과 한계도 보고합니다.
