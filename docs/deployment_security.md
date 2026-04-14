# Deployment Security Checklist

> **목표**: Private Repo → Streamlit Community Cloud 공개 URL 배포
> **전제**: 앱 URL은 공개되지만 앱 내부는 외부 악용/남용이 불가능해야 함

---

## Threat Model

| # | 위협 | 심각도 | 대응 |
|:-:|------|:---:|------|
| T1 | 서버 API 키 남용 (비용 폭탄) | **Critical** | **BYOK 강제** (서버 기본키 완전 제거) |
| T2 | Prompt Injection | High | 입력 검증 + Gemini Safety 필터 |
| T3 | DoS (대규모 시뮬레이션 파라미터) | High | 파라미터 상한 + Rate Limit |
| T4 | 스택 트레이스로 내부 구조 노출 | Medium | `showErrorDetails = false` + 에러 샌티타이즈 |
| T5 | 의존성 공급망 공격 (litellm 사건) | Medium | litellm 제거 + 버전 pinning |
| T6 | XSRF / CORS 허점 | Medium | Streamlit config 하드닝 |
| T7 | git history에 시크릿 유출 | Low | gitleaks 감사 (확인 완료) |
| T8 | 세션 간 데이터 누수 | Low | Streamlit session_state는 자연히 격리 |

---

## 구현된 보안 조치

### 1. BYOK (Bring Your Own Key) 강제

**파일**: [app/security.py](../app/security.py), [app/config.py](../app/config.py)

- 서버 환경변수에서 기본 API 키를 읽지 않음
- 사용자가 사이드바에서 직접 입력한 키만 사용
- 키 형식 검증 (`AIza` + 35자)
- 세션 메모리에만 보관, 디스크/로그에 쓰지 않음

```python
# 모든 LLM 호출 전 호출
from app.security import ready_to_run
if not ready_to_run(tag="hello_agent"):
    return  # BYOK 없거나 rate limit 초과 시 차단
```

### 2. 세션별 Rate Limiting

**위치**: [app/security.py#check_rate_limit](../app/security.py)

- 분당 20회, 시간당 100회 제한
- Streamlit session_state 기반 (사용자별 독립 카운터)
- 단일 세션 장악 시에도 시간당 비용 상한 존재

### 3. 입력 검증 (Prompt Injection 대응)

**위치**: [app/security.py#sanitize_user_input](../app/security.py)

- 최대 2000자 truncate
- 제어 문자 제거 (개행/탭은 허용)
- 인젝션 패턴 차단: `<|system|>`, `[INST]`, `### System:` 등
- 자유입력이 허용되는 페이지(hello_agent, custom_env 등)에서 호출

### 4. 파라미터 상한 (DoS 대응)

**위치**: [app/security.py#PARAM_CAPS](../app/security.py)

| 파라미터 | 상한 |
|----------|:---:|
| agents | 20 |
| rounds | 5 |
| steps | 20 |
| cot_depth | 3 |

`cap("agents", user_input)` 로 적용.

### 5. 에러 메시지 샌티타이즈

**위치**: [app/security.py#sanitize_error](../app/security.py)

노출 차단 대상:
- API 키 (`AIza...`, `sk-...`, `ghp_...`)
- 파일 경로 (`C:\...`, `/home/...`)
- 스택 트레이스 (Streamlit config `showErrorDetails = false`)

### 6. Gemini Safety Filter

**위치**: [agentsociety2_lite/llm/client.py](../agentsociety2_lite/llm/client.py)

```python
BLOCK_MEDIUM_AND_ABOVE for:
- HARM_CATEGORY_HARASSMENT
- HARM_CATEGORY_HATE_SPEECH
- HARM_CATEGORY_SEXUALLY_EXPLICIT
- HARM_CATEGORY_DANGEROUS_CONTENT
```

추가로 `max_output_tokens = 2048` — 런어웨이 생성 방지.

### 7. Streamlit Config 하드닝

**파일**: [.streamlit/config.toml](../.streamlit/config.toml)

| 설정 | 값 | 효과 |
|------|------|------|
| `enableXsrfProtection` | `true` | XSRF 방어 |
| `enableCORS` | `false` | 크로스 오리진 요청 차단 |
| `showErrorDetails` | `false` | 스택 트레이스 숨김 |
| `toolbarMode` | `"minimal"` | Deploy/Source 버튼 숨김 |
| `gatherUsageStats` | `false` | 텔레메트리 비활성 |
| `maxUploadSize` | `5` MB | 업로드 크기 제한 |

### 8. 의존성 보안

**파일**: [requirements.txt](../requirements.txt)

- `>=min,<major-next` 범위 고정 (보안 패치는 허용, 주 버전 업 차단)
- **litellm 완전 제거** (2026.03 공급망 공격 대응)
- 9개 패키지로 최소화 (원본 45+)

### 9. 시크릿 관리

- `.gitignore`: `.env`, `.env.*` 전체 차단. `.env.example`만 예외 허용
- `.env.local` 로컬 개발용만, 배포 환경에는 존재하지 않음
- git history 감사 완료: 시크릿 유출 흔적 없음

---

## Streamlit Community Cloud 배포 체크리스트

### 배포 전

- [ ] `streamlit run run.py` 로컬에서 정상 실행 확인
- [ ] `.env.local`이 git에 커밋되지 않았는지 `git ls-files | grep env` 확인
- [ ] `git log --all -p -- '.env*'` 로 히스토리 확인 (실제 키 노출 없음)
- [ ] `pip-audit` 또는 Dependabot으로 의존성 취약점 검사
- [ ] Private Repo인지 최종 확인

### 배포 단계

1. [Streamlit Community Cloud](https://share.streamlit.io) 접속 → GitHub 로그인
2. **Private Repo 접근 권한 부여** (`repo` OAuth scope 승인)
3. "New app" → Repository 선택 → Branch: `main`, Main file: `run.py`
4. **Secrets는 비워둠** (BYOK이므로 서버 키 필요 없음)
5. Deploy 클릭

### 배포 후

- [ ] 공개 URL 접속 시 "API Key 입력 필요" 경고 확인
- [ ] 임의의 Gemini 키로 Hello Agent 테스트
- [ ] 잘못된 키 입력 시 에러가 스택 없이 친절하게 표시되는지 확인
- [ ] 파라미터 상한(agents=20 등) 초과 입력 차단 동작 확인
- [ ] Rate Limit 초과 시 차단 메시지 확인 (21회 연속 요청 테스트)
- [ ] DevTools Network 탭에서 응답 헤더의 `X-Frame-Options` 등 확인

---

## 지속적 보안 운영

### 주기적 점검 (월 1회)

- [ ] `pip-audit` 실행하여 CVE 확인
- [ ] Streamlit, google-genai 최신 버전 릴리즈 노트 확인
- [ ] 앱 로그에서 이상 패턴(특정 IP 대량 요청 등) 점검

### 즉시 대응이 필요한 경우

- Gemini API에서 이상 비용 알림 → 사용자 키 관련 이슈 (서버는 무관)
- 의존성에서 CVE 경보 → `requirements.txt` 업데이트 후 재배포
- Streamlit Cloud 상태 페이지 장애 알림 → 관찰만 (앱 변경 불필요)

### 키 회전 정책

서버 측 키가 없으므로 **회전 대상 없음**. 사용자는 자신의 Gemini 키를 자율적으로 관리.

---

## 추가 강화 옵션 (선택)

| 옵션 | 공수 | 효과 |
|------|:---:|------|
| pre-commit + gitleaks 훅 | 낮음 | 커밋 시점에 시크릿 유출 차단 |
| GitHub Dependabot 활성화 | 낮음 | CVE 자동 PR |
| Sentry 에러 모니터링 | 중간 | 프로덕션 에러 가시화 (단, PII 주의) |
| Cloudflare 앞단 배치 | 중간 | DDoS 방어 + WAF |
| Viewer Allowlist | 낮음 | 앱 자체를 특정 사용자에게만 공개 |
| OIDC/SSO 연동 | 높음 | 엔터프라이즈 인증 |

현재 구성만으로도 **공개 URL + 남용 방지**는 충분히 달성 가능합니다.

---

## 요약

본 프로젝트는 다음 세 가지 축으로 공개 배포에 대비했습니다.

1. **비용 폭탄 방지** — 서버 키 없음, BYOK 강제, Rate Limit, 파라미터 상한
2. **정보 유출 방지** — 에러 샌티타이즈, 스택 숨김, Streamlit 툴바 최소화
3. **공급망 공격 방지** — litellm 제거, 의존성 pinning, git 시크릿 감사
