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

N₂ 단일 지점 최소 pipeline과 H₂ 검증 5개는 통과했다. 측정된 SQD–FCI 오차가 189.95 mHa이므로 에너지 품질을 달성했다고 선언하지 않는다. Phase 2 sweep은 보류하고 같은 지점에서 압축 초기화와 sampling support를 조사한다. FCI energy convergence flag와 eigenvector residual을 구분하며 현재 reference를 미세한 성능 차이의 certified 기준으로 사용하지 않는다. 상세 증거는 PHASE1_RESULTS.md와 원본 report에 저장했다.
