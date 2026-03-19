# 증빙서류 검증 시스템 (Doc Verification Demo)

증빙서류(사업자등록증명, 중소기업확인서 등)를 업로드하면 **AI OCR로 문서를 판독**하고, **발급일자가 기준일 이내인지 자동 검증**하는 웹 데모입니다.

> 한국디자인진흥원 산업디자인전문회사 사이트 고도화 사업 —
> "기업 제출 증빙서류 이미지 내 텍스트 추출 → 자격 요건 교차 검증" AI 필터링 데모

### **[Live Demo — doc-demo.up.railway.app](https://doc-demo.up.railway.app)**

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **문서 업로드** | PDF, 이미지(JPG/PNG) 등 증빙서류 파일 입력 |
| **AI OCR 판독** | Upstage Document Parse API를 활용한 문서 텍스트 추출 (스캔본 포함) |
| **발급일자 자동 탐지** | 발급일·발행일·교부일 등 키워드 기반 날짜 추출 |
| **유효기간 검증** | 오늘 날짜 기준으로 발급일이 N일 이내인지 판정 |
| **신호등 표시** | 🟢 기준 이내 / 🔴 기준 초과 / 🟡 판독 불확실 |
| **기준일 조정** | 기본 30일, 사용자가 자유롭게 변경 가능 |

---

## 스크린샷

```
┌─────────────────────┬──────────────────────────────┐
│  📄 파일 업로드      │  📋 판독 결과                 │
│                     │                              │
│  [파일 선택]         │  추출된 문서 내용 표시          │
│  기준일: [30]일      │                              │
│  [분석하기]          │  🟢 발급일: 2026-03-01        │
│                     │     경과일: 18일 (30일 이내)   │
└─────────────────────┴──────────────────────────────┘
```

---

## 빠른 시작

### 1. 환경 설정

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에 Upstage API 키 입력
```

`.env` 파일:
```
UPSTAGE_API_KEY=your_upstage_api_key_here
```

### 2. 서버 실행

```bash
python main.py
# 또는
uvicorn main:app --host 0.0.0.0 --port 8001
```

브라우저에서 **http://localhost:8001** 접속

---

## 기술 스택

- **Backend**: Python / FastAPI
- **AI OCR**: [Upstage Document Parse API](https://www.upstage.ai/)
- **Frontend**: Vanilla HTML / CSS / JavaScript (별도 빌드 불필요)

---

## 프로젝트 구조

```
doc_verify/
├── main.py              # FastAPI 서버 & 문서 분석 로직
├── static/
│   └── index.html       # 프론트엔드 UI
├── requirements.txt     # Python 의존성
├── .env                 # API 키 (git 미포함)
└── README.md
```

---

## API

### `POST /api/analyze`

증빙서류를 분석하고 발급일자 유효성을 검증합니다.

**Request** (multipart/form-data):
| 필드 | 타입 | 설명 |
|------|------|------|
| `file` | File | 증빙서류 파일 (PDF, JPG, PNG) |
| `threshold_days` | int | 유효기간 기준일 (기본값: 30) |

**Response**:
```json
{
  "success": true,
  "filename": "사업자등록증명.pdf",
  "extracted_text": "...",
  "date_info": {
    "found": true,
    "issue_date": "2026-03-01",
    "keyword": "발급일자",
    "confidence": "high"
  },
  "verification": {
    "status": "valid",
    "signal": "green",
    "message": "발급일(2026-03-01)로부터 18일 경과 — 30일 기준 이내 ✓",
    "days_elapsed": 18
  }
}
```

---

## 라이선스

Internal use only — 뉴럴스튜디오(주)
