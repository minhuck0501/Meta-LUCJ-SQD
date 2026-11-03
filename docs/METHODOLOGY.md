# Methodology

작성일: 2026-11-03. 설계 초안이며 구현 검증과 성능 실험은 미완료다.

## 에너지와 공간

Born–Oppenheimer, 고정 basis의 active-space Hamiltonian을 사용한다. PySCF CASCI의 get_h1cas 반환값을 h1_active, ecore로 명명한다. 설치된 PySCF 소스 h1e_for_cas 확인 결과 ecore는 핵 반발과 frozen-core 전자 기여를 포함한다. 총 에너지는 E_total = E_active + ecore이며 상수를 한 번만 더한다. 적분은 PySCF chemist convention을 기준으로 하고 ffsim/SQD에 전달할 때 작은 exact matrix와 비교한다.

첫 N₂ 설정은 neutral singlet, 6-31G, R=1.2 Å, frozen core 2 spatial orbital, active (10e,16o)다. 전체 orbital 수와 점유율을 실제 molecule에서 assert한다. SCF/CCSD의 converged flag, residual 및 반복 횟수를 저장한다. optimizer 종료와 물리적 정확도 도달은 구분한다.

## LUCJ와 목적함수

개념적 상태는 |ψ(θ;R)⟩ = U_LUCJ(θ)|HF(R)⟩이다. 정확한 operator 순서, final orbital rotation, 파라미터 수와 packing은 설치된 ffsim 구현과 round-trip 테스트로 고정할 때까지 미정이다. 초기 후보는 spin-balanced, 1 repetition, 같은 spin의 (p,p+1), 반대 spin의 (p,p), p=0,4,8,… interaction이다. 이는 notebook에서 가져온 후보이며 확정된 최적 topology가 아니다.

VQE 목적함수는 ⟨ψ|H|ψ⟩이고, sampled objective는 E_SQD(θ;R,ξ)=λ_min(H projected onto S(θ,R,ξ))이다. ξ는 sampling, batching, recovery randomness다. alpha/beta string의 Cartesian product를 쓰는 solver에서는 S가 단순 관측 determinant 목록보다 클 수 있다. 실제 dimension을 기록한다.

정상적인 Hermitian projected Hamiltonian을 수치적으로 충분히 풀면 동일 Hamiltonian의 ground energy에 대한 상계가 된다. Spin penalty 사용 시 penalty Hamiltonian과 원래 Hamiltonian의 에너지 보고 방식을 별도로 검증한다. 초기에는 penalty를 자동 채택하지 않는다.

## 문헌 비교

| 자료 | 확립된 구성 | 본 프로젝트에서의 한계 |
| --- | --- | --- |
| LUCJ 초기화, §2–3, Fig.1 및 §4 | CCSD 초기화, compressed t₂ fitting, tensor-network sample-quality surrogate | t₂ fitting, VQE, QSCI/SQD 목적함수는 동일하지 않음 |
| Meta-VQE, §II Eq.(1), Fig.1 | geometry/Hamiltonian encoding, 다지점 기대 에너지 학습, opt-meta refinement | supervised LUCJ regression이나 stochastic SQD meta-loss의 직접 검증이 아님 |
| SQD, 본문과 configuration-recovery 설명 | 샘플 기반 부분공간, self-consistent occupations로 recovery | 하드웨어 noise mitigation과 ideal CPU sampling의 역할을 구분해야 함 |

로컬 PDF의 추출 텍스트에서 관련 방법과 조건을 검토했다. 논문 전체 재현, 수식별 독립 유도, 도표의 시각 검증을 완료한 상태는 아니다. 정확한 구현 단계마다 관련 식과 library source를 재확인한다.

## 참조 notebook 정적 검토

셀 번호는 JSON cell index이며 0부터 센다. 실행하거나 IBM service에 접속하지 않았다.

- Cell 3: N₂ 1.0 Å, cc-pVDZ, core 2, active 26 orbital이다. 프로젝트의 6-31G (10e,16o), 1.2 Å와 다르다.
- Cell 3: exact_energy 상수의 출처와 수렴 오차가 notebook에서 입증되지 않는다. 새 benchmark의 reference로 재사용하지 않는다.
- Cell 3: nuclear_repulsion_energy라는 변수는 실제로 ecore를 받는다. 덧셈 자체보다 명명과 해석이 문제다.
- Cell 6: optimize=True는 CCSD amplitude 압축 단계다. SQD 에너지를 직접 최적화한 것으로 해석하지 않는다.
- Cells 7–9: account 저장, 실제 backend, 100,000 shots와 고정 job ID에 의존한다. 초기 CPU pipeline에 포함하지 않는다.
- Cell 8: bridge 수가 0이면 best_layout[:-0]은 빈 리스트가 된다. embedding 부재 처리와 전체 mapping 열거의 비용도 검토가 필요하다.
- Cell 11: 설치된 bit_array_to_arrays는 unique bitstrings를 반환한다. 행 수는 shots가 아니다. raw/retained shots, unique 수, probability-weighted 유효 비율을 구분한다.
- Cell 11: 설치된 diagonalize_fermionic_hamiltonian의 initial_occupancies는 alpha/beta 배열 tuple을 받는다. notebook의 2*norb flat fallback은 그대로 사용하지 않고 검증한다.
- Cell 11: spin_sq, symmetrize_spin, solver 수렴의 의미를 검증한다. spin inversion symmetry와 정확한 singlet projection을 동일시하지 않는다.
- Cell 12: 0.001 Ha 표시선을 보편적인 chemical accuracy 정의로 채택하지 않는다. LUCJ 논문 Fig.1은 1.6 mHa를 표시한다. 본 연구 acceptance tolerance는 기준 계산과 pilot 이후 결정한다.

## 수치 검증 계획

1. 작은 molecule에서 AO/MO orthonormality, h1 Hermiticity, eri permutation symmetry 및 전자 수 확인.
2. 동일 determinant의 active expectation + ecore와 HF total energy 비교.
3. 작은 공간의 전체 determinant matrix 대각화와 PySCF FCI 비교.
4. LUCJ zero parameter의 HF 복원, norm 및 particle-number 보존, packing round trip 확인.
5. 알려진 bitstring과 비대칭 alpha/beta 전자 수로 endian/spin block 변환 확인. singlet만으로는 swap 오류를 놓칠 수 있다.
6. 작은 공간에서 모든 determinant를 포함한 SQD와 exact 결과 비교, solver residual 확인.
7. 고정 seed의 반복 재현, 복수 seed의 독립 평가, failure serialization 확인.

작은 결정론적 비교의 초기 제안 tolerance는 norm 1e-10, energy 1e-8 Ha다. 이는 연구 성능 acceptance threshold가 아니며 backend 오차와 residual 확인 후 설정으로 고정한다.

## Alignment

오비탈 부호·순열·축퇴공간 회전은 integrals와 파라미터 변환을 일관되게 해야 한다. Jastrow 좌표의 주기성도 operator convention에 따라 확인한다. 어떤 변환도 state fidelity, 확률 또는 일관되게 변환한 energy의 불변성을 검증하기 전에는 harmless preprocessing으로 취급하지 않는다. 학습에 필요한 정렬 기준과 통계는 train에서만 추정하며, test의 최적화된 파라미터를 사용하지 않는다.
