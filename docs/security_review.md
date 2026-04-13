# Security Review: Dependencies

## Summary

원본 `agentsociety2`의 litellm 의존성을 제거하고 `google-genai`로 대체.
Python 3.14 호환 + 보안 강화.

## Package-by-Package Assessment

| Package | Status | Notes |
|---------|:------:|-------|
| **google-genai** | SAFE | Google 유지관리. 얇은 API 클라이언트. CVE 없음 |
| **pydantic** | SAFE | 널리 채택, Rust 코어 (v2). CVE 없음 |
| **json-repair** | CAUTION | 단일 메인테이너. CVE 없으나 커뮤니티 리뷰 제한적. 버전 고정 권장 |
| **python-dotenv** | SAFE | 단순, 성숙, 널리 사용. .env 파일을 VCS에서 제외할 것 |
| **sqlalchemy** | SAFE | 업계 표준 ORM. 매개변수화된 쿼리 사용 시 안전 |
| **aiohttp** | CAUTION | HTTP 서버/클라이언트 복잡성으로 CVE 이력 있음. 최신 버전 유지 |
| **streamlit** | CAUTION | 과거 XSS/경로 탐색 CVE 이력. 배포 시 주의. 버전 고정+업데이트 |
| **plotly** | SAFE | 클라이언트 사이드 차트 생성. 최소 보안 표면 |
| **pyvis** | CAUTION | 소규모 커뮤니티. 업데이트 빈도 낮음. 방치 리스크 |

## LLM SDK Comparison

| 기준 | google-genai | openai | litellm |
|------|:---:|:---:|:---:|
| 유지관리 | Google | OpenAI | BerriAI (소규모) |
| 알려진 CVE | 없음 | 없음 | **공급망 공격 (2026.03)** |
| 공격 표면 | 얇은 API 클라이언트 | 얇은 API 클라이언트 | 100+ 프로바이더 래핑, 넓은 표면 |
| 판정 | **SAFE** | **SAFE** | **RISKY** |

### litellm 사건 상세

- **날짜**: 2026년 3월 24일
- **공격자**: TeamPCP
- **경로**: Trivy GitHub Action 태그 변조 → CI/CD에서 PyPI 토큰 탈취 → 악성 litellm 배포
- **감염 버전**: 1.82.7, 1.82.8
- **악성 행위**: `.pth` 파일로 Python 시작 시 자동 실행, 환경 변수(API 키, 클라우드 자격증명) 탈취
- **영향**: 40분간 노출, 4만+ 다운로드

### 결정: litellm 완전 제거

`agentsociety2`가 litellm을 핵심 의존성으로 사용하므로, 경량 재구현(`agentsociety2_lite`)에서는 litellm을 **완전히 제거**하고 `google-genai`로 직접 대체.

## 보안 권장사항

1. **API 키 관리**: `.env` 파일에만 저장, `.gitignore`에 포함 확인
2. **버전 고정**: 모든 의존성에 최소 버전 지정 (`>=` 사용)
3. **정기 업데이트**: `pip audit` 또는 `safety check`으로 CVE 모니터링
4. **Streamlit 배포 시**: 인증 미들웨어 추가, 공개 배포 지양
5. **.env.example**: 실제 키 값이 포함되지 않도록 주의
