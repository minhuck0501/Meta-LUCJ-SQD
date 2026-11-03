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
