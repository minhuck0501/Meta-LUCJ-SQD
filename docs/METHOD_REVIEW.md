# Method Review — Interpolation versus Physical Meta Objectives

검토일: 2026-11-04. 기존 reference PDF의 관련 식과 방법을 다시 대조했다. Local/manifold interpolation은 진단용 대조군 후보이며, 검증된 Meta 해결책으로 확정하지 않는다.

## Meta-VQE가 실제로 학습한 것

Reference: Cervera-Lierta et al., arXiv:2009.13545v3, §II Eq. (1)–(2), molecular example Eq. (16)–(17), Fig. 5.

원 논문은 여러 Hamiltonian parameters에서 기대 에너지 합을 최소화한다. 독립 최적화로 만든 parameter labels를 정확히 재현하는 회귀가 아니다. Opt-meta-VQE는 공유 학습 결과를 개별 VQE 초기값으로 사용한다. Nonlinear encoding이 molecular example의 convergence를 개선하지만 그것이 training parameter labels의 exact interpolation을 보장하거나 요구하는 것은 아니다.

논문의 θ(R)=wR+b 같은 linear angle encoding은 exp(iθA)로 circuit에 들어간다. 따라서 matrix entries와 상태는 R에 비선형일 수 있다. 현재 프로젝트의 affine matrix-entry/sin-cos regression 실패를 논문의 linear encoding 실패 또는 nonlinear Meta가 반드시 필요하다는 증거로 해석하면 안 된다.

## LUCJ 초기화 논문의 구분

Reference: Lin et al., arXiv:2511.22476v1, §3.1 Eq. (13)–(14), §3.1.3, Fig. 2–4.

Compressed double factorization은 constrained unitary/Jastrow 표현으로 CCSD t₂ 재구성 오차를 줄인다. 논문은 amplitude fitting loss, expectation energy와 sample-selected energy가 동일 목표가 아님을 구분한다. 특히 norm regularization은 해당 실험에서 VQE energy에 도움이 되지만 QSCI energy에는 불리할 수 있다. 이 프로젝트의 λ=0.001 선택은 수렴 진단에서의 선택이지 SQD 최적 설정이라는 문헌 보장이 아니다.

따라서 exact label interpolation이나 unitary 제약 보존은 중요한 구현 조건일 수 있어도 좋은 SQD 에너지의 충분조건은 아니다. 문헌이 보고한 entropy/부분공간 크기의 경향도 단일 지표의 보편적인 단조 관계로 취급하지 않는다.

## 현재 증거에서 정당한 결론

Exact feature decode control은 약 1e-14로 상태를 복원했고 affine prediction은 일부 training states를 충분히 재구성하지 못했다. 이는 현재 회귀/표현에서의 reconstruction limitation이다. 하지만 labels는 12회 budget-limited SPSA 결과이며 global optimum이 아니다. Gauge 비유일성과 finite sampling variability도 있다. Training labels를 반드시 정확히 fit해야 연구가 성공한다는 결론은 정당하지 않다.

Manifold interpolation은 다음 질문의 대조군으로는 적절하다: 학습점을 정확히 통과하고 unitary 구조를 유지하면 affine regression보다 SQD가 나아지는가? 그러나 geometry 간 geodesic이 low-energy state나 좋은 sampling support를 따라간다는 보장은 없다. Warm transfer와의 중복도 있으므로 독립 Meta 성과로 과장하지 않는다. 학습점 암기와 label noise 전파 가능성도 보고해야 한다.

## 다음 실험의 우선순위

1. 필요하면 local/manifold interpolation을 저비용 control로만 추가하고 exact-fit 자체를 성공 기준으로 삼지 않는다.
2. Model family는 작은 공유 geometry encoding으로 제한하고 실제 SQD energy 또는 검증된 physical surrogate를 통한 공동 개선을 연구 후보로 둔다.
3. 계산 가능한 작은 문제에서 surrogate의 물리적 일관성과 비용을 먼저 확인한다. VQE expectation이나 tensor-network surrogate를 쓰면 SQD와의 차이를 명시하고 SQD로 최종 평가한다.
4. Existing supervised initialization + 제한된 training-geometry physical refinement의 hybrid는 후보지만, 아직 효과가 입증된 방법이 아니다.
5. 같은 downstream refinement budget에서 independent/block-polar warm과 비교하고, label 생성·공동 학습·inference·SQD 비용을 포함한다.

제안 가능한 SQD meta objective는 L(φ)=Σ_train w_R E_ξ[E_SQD(f_φ(R);R,ξ)]다. 이는 원 Meta-VQE 기대 에너지 objective를 SQD에 확장한 본 연구의 제안이며 reference가 직접 입증한 방법이 아니다. Finite-sample non-smoothness와 training cost를 먼저 검증해야 한다. 이 검토에서 해당 optimizer를 실행하지 않았다.

1.1/1.4 Å 결과는 이미 분석했으므로 향후 model selection에 쓰면 development 데이터로 취급하고 새 final geometry/seeds를 확보한다. Reference Eq./figure 검토는 위 관련 부분에 한정하며 모든 논문 결과를 재현한 상태는 아니다.
