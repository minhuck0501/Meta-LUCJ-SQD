# Experiment Records

진행 순서대로 정리한 Phase 1 기록이다. 이전 실패 결과도 연구 근거로 보존한다.

| 기록 | 내용 |
| --- | --- |
| [Phase 1](PHASE1_RESULTS.md) | 최초 chemistry–LUCJ–SQD 수치 검증 |
| [초기화 비교](INITIALIZATION_COMPARISON.md) | 단순 초기화와 single-stage 압축 비교 |
| [Multi-stage](MULTISTAGE_RESULTS.md) | 단계별 압축의 미수렴 및 비용 |
| [진단과 수정](COMPRESSION_FIX_RESULTS.md) | Gradient 검증, norm 증가 진단, regularization 수렴 |
| [Phase 2](PHASE2_RESULTS.md) | 세 거리의 수렴·에너지 오차·자원 사용량 |
| [Phase 3 pilot](PHASE3_PILOT_RESULTS.md) | 독립 SQD refinement와 held-out seed 평가 |
| [Phase 3 반복](PHASE3_REPETITIONS.md) | 독립 반복 3개와 12/24회 예산 진단 |
| [다른 거리 적용](PHASE3_GEOMETRIES.md) | 1.0/1.6 Å의 독립 refinement |
| [Phase 4](PHASE4_RESULTS.md) | 양방향 sign-only warm-start pilot |
| [Phase 5](PHASE5_RESULTS.md) | 오비탈 대응·주기성·polar 전달 진단 |
| [Block warm-start 재평가](BLOCK_WARMSTART_RESULTS.md) | 양방향 고정 규칙 비교와 공통 표현 검증 |
| [Phase 6 Meta pilot](PHASE6_PILOT_RESULTS.md) | Affine 학습과 새 geometry 평가 |
| [Frozen Meta 진단](META_DIAGNOSTIC_RESULTS.md) | 학습점 재구성·unitary projection·확률 분포 |
| [직접 SQD 공동 학습](JASTROW_JOINT_RESULTS.md) | Frozen rotations의 공유 Jastrow 보정 pilot |

같은 폴더의 `*_summary.json`은 추적 가능한 수치 요약이다. 원본 배열·trajectory·실행 환경·source snapshot은 Git에서 제외한 `results/`에 저장한다.

정리 과정에서는 바이트가 같은 예비 실행 배열만 삭제했다. 원본을 남긴 경로와 SHA-256은 `results/cleanup_manifest.json`에 기록했다. 실행 report와 실패 기록은 유지했다.

이전 실패·진단 설정 3개는 활성 `configs/`에서 삭제했다. 동일한 원본은 기존 실행의 `source_snapshot/configs/`에 있으며, 각 보고서의 재현 명령은 해당 경로를 사용한다. 현재 기본 실행은 regularized 설정을 사용한다.

## 그래프

각 보고서 하단에 PNG 그래프와 SVG·수치 JSON 링크가 있습니다. [전체 그래프 폴더](figures/)에서 확인할 수 있습니다. 최적화 곡선은 훈련 목적함수이며, 별도 seed 평가와 구분합니다. 계산 지점 연결선은 fitting된 PEC가 아닙니다.
