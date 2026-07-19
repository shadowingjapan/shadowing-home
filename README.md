# 쉐도잉 일본어 홈페이지 — 자동 업데이트

유튜브 채널 [쉐도잉 일본어](https://www.youtube.com/@shadowingjapan)의 영상 목록 홈페이지입니다.
**매일 아침 6시(한국시간)에 GitHub Actions가 유튜브에서 최신 데이터를 받아 페이지를 자동으로 갱신합니다.**
구독자 수, 인기 영상 순위, 최근 업로드, 추천 영상도 매일 새로 계산됩니다.

---

## 처음 설정하기 (약 20분, 한 번만 하면 됩니다)

### 1단계. GitHub 계정 만들기

1. https://github.com 접속 → **Sign up**
2. 이메일 주소 입력 → 비밀번호 설정 → 사용자 이름(username) 정하기
   - 이 username이 홈페이지 주소가 됩니다: `https://username.github.io/...`
3. 이메일 인증 완료

### 2단계. 저장소(repository) 만들고 파일 올리기

1. 로그인 후 우측 상단 **+** → **New repository**
2. Repository name: `shadowing-home` (원하는 이름 가능)
3. **Public** 선택 → **Create repository**
4. 생성된 페이지에서 **uploading an existing file** 링크 클릭
5. 이 압축파일 안의 **모든 파일과 폴더**를 드래그해서 업로드
   - `build.py`, `template.html`, `curation.json`, `index.html`, `.github` 폴더
   - ⚠️ `.github` 폴더가 안 보이면(숨김 폴더): 압축을 푼 뒤 폴더 안에서 `Ctrl+H`(윈도우) / `Cmd+Shift+.`(맥)로 숨김 파일을 표시하고 올려주세요.
   - 웹 업로드에서 폴더 업로드가 잘 안 되면: 저장소에서 **Add file → Create new file** → 파일명에 `.github/workflows/update.yml` 입력 → 내용 붙여넣기로 만들 수도 있습니다.
6. 하단 **Commit changes** 클릭

### 3단계. YouTube API 키 발급 (무료)

1. https://console.cloud.google.com 접속 (구글 계정으로 로그인)
2. 상단 프로젝트 선택 → **새 프로젝트** → 이름 예: `shadowing-home` → 만들기
3. 왼쪽 메뉴 **API 및 서비스 → 라이브러리** → `YouTube Data API v3` 검색 → **사용 설정**
4. **API 및 서비스 → 사용자 인증 정보** → **+ 사용자 인증 정보 만들기 → API 키**
5. 생성된 키 복사 (예: `AIzaSy...`)
   - 무료 한도(하루 10,000 유닛)로 충분합니다. 이 스크립트는 하루 약 150 유닛만 사용해요.

### 4단계. API 키를 GitHub에 등록

1. 내 저장소 → **Settings** 탭 → 왼쪽 **Secrets and variables → Actions**
2. **New repository secret** 클릭
3. Name: `YT_API_KEY` (정확히 이대로), Secret: 복사한 API 키 붙여넣기 → **Add secret**

### 5단계. 홈페이지 켜기 (GitHub Pages)

1. 저장소 → **Settings → Pages**
2. Source: **Deploy from a branch** / Branch: **main**, 폴더 **/(root)** → **Save**
3. 1~2분 뒤 `https://username.github.io/shadowing-home/` 에서 홈페이지 확인!

### 6단계. 자동 업데이트 확인

1. 저장소 → **Actions** 탭 → 왼쪽 "홈페이지 자동 업데이트" 선택
2. **Run workflow** 버튼으로 지금 바로 한 번 실행해보세요 (초록색 체크가 뜨면 성공)
3. 이후에는 매일 아침 6시(한국시간)에 자동 실행됩니다.

---

## 파일 설명

| 파일 | 역할 |
|---|---|
| `index.html` | 홈페이지 본체 (자동 생성됨 — 직접 수정 불필요) |
| `template.html` | 페이지 디자인 틀. 디자인 수정은 여기서 |
| `build.py` | 유튜브 데이터 수집 + index.html 생성 스크립트 |
| `curation.json` | 재생목록별 분류·배지·소그룹 설정 (레벨/완결/PDF/추천/소그룹) |
| `.github/workflows/update.yml` | 매일 자동 실행 설정 |

## 자주 하는 수정

- **새 재생목록의 레벨/배지/소그룹 지정**: 채널에 새 재생목록이 생기면 제목을 분석해 자동으로 NEW 배지와 함께 적절한 섹션·소그룹에 들어갑니다. 세부 조정하려면 `curation.json`의 `meta`에 재생목록 ID를 추가하세요:
  ```json
  "PL재생목록ID": {"group": "basic", "order": 5, "sub": "여행 · 회화", "lv": "초급", "st": "연재중", "pdf": true, "rec": false, "new": true}
  ```
  - `group`: `basic`(기초~중급) / `inter`(중급 이상) / `jlpt`
  - `sub`: 소그룹 이름 (예: "여행 · 회화", "기본 단어", "문법 · 활용", "문장 연습", "한자", "표현 · 관용어", "실전 어휘")
  - JLPT는 `"level": "N3"`, `"type": "vocab"`(단어)/`grammar`(문법·문형)/`kanji`(한자)/`sentence`(문장) 추가
- **업데이트 시간 변경**: `update.yml`의 `cron: "0 21 * * *"` 수정 (UTC 기준, 한국시간-9시간)
- **문구/디자인 수정**: `template.html` 수정 후 Actions에서 Run workflow 실행

## 문제 해결

- **Actions가 빨간색 X로 실패**: 로그에서 `YT_API_KEY` 관련 오류면 4단계 Secret 이름/값 확인
- **페이지가 안 열림**: Settings → Pages에서 Branch가 main/(root)로 저장됐는지 확인
- **새 영상이 반영 안 됨**: Actions 탭에서 마지막 실행 시간 확인, Run workflow로 수동 실행
