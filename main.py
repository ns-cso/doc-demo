import os
import re
import json
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

app = FastAPI(title="증빙서류 검증 시스템")

UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
UPSTAGE_URL = "https://api.upstage.ai/v1/document-digitization"


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "static" / "index.html"
    return html_path.read_text(encoding="utf-8")


@app.post("/api/analyze")
async def analyze_document(file: UploadFile = File(...), threshold_days: int = Form(30)):
    """증빙서류를 Upstage API로 분석하고 발급일자 검증"""
    file_bytes = await file.read()

    # 1) Upstage Document Parse API 호출
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            UPSTAGE_URL,
            headers={"Authorization": f"Bearer {UPSTAGE_API_KEY}"},
            files={"document": (file.filename, file_bytes, file.content_type or "application/pdf")},
            data={
                "model": "document-parse",
                "output_formats": '["html", "text"]',
                "ocr": "force",
            },
        )

    if resp.status_code != 200:
        return {
            "success": False,
            "error": f"Upstage API 오류 (HTTP {resp.status_code}): {resp.text}",
        }

    result = resp.json()
    extracted_text = result.get("content", {}).get("text", "")
    extracted_html = result.get("content", {}).get("html", "")

    # 2) 날짜 추출 시도
    date_info = extract_dates(extracted_text)

    # 3) 기준일 검증
    today = datetime.now().date()
    verification = verify_date(date_info, today, threshold_days)

    return {
        "success": True,
        "filename": file.filename,
        "extracted_text": extracted_text,
        "extracted_html": extracted_html,
        "date_info": date_info,
        "verification": verification,
        "today": today.isoformat(),
        "threshold_days": threshold_days,
    }


def extract_dates(text: str) -> dict:
    """텍스트에서 발급일/발행일 등의 날짜를 추출"""
    # 다양한 날짜 패턴
    date_patterns = [
        # 2024년 03월 15일, 2024. 03. 15, 2024-03-15, 2024/03/15
        r'(\d{4})\s*[년.\-/]\s*(\d{1,2})\s*[월.\-/]\s*(\d{1,2})\s*일?',
    ]

    # 발급/발행 관련 키워드 근처의 날짜 우선 탐색
    issue_keywords = [
        "발급일", "발행일", "발급일자", "발행일자", "교부일", "발급 일자",
        "확인일", "유효기간", "증명일", "발급번호", "발 급 일",
    ]

    found_dates = []

    # 키워드 근처 날짜 탐색
    for keyword in issue_keywords:
        # 키워드 위치 찾기
        keyword_positions = [m.start() for m in re.finditer(re.escape(keyword), text)]
        for pos in keyword_positions:
            # 키워드 앞뒤 200자 범위에서 날짜 탐색
            start = max(0, pos - 100)
            end = min(len(text), pos + 200)
            context = text[start:end]

            for pattern in date_patterns:
                matches = re.finditer(pattern, context)
                for m in matches:
                    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    try:
                        dt = datetime(year, month, day).date()
                        found_dates.append({
                            "date": dt.isoformat(),
                            "keyword": keyword,
                            "confidence": "high",
                        })
                    except ValueError:
                        pass

    # 키워드 없이 문서 전체에서 날짜 탐색 (fallback)
    if not found_dates:
        for pattern in date_patterns:
            matches = re.finditer(pattern, text)
            for m in matches:
                year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
                try:
                    dt = datetime(year, month, day).date()
                    # 너무 오래된 날짜나 미래 날짜 필터링
                    if datetime(2000, 1, 1).date() <= dt <= datetime.now().date() + timedelta(days=365):
                        found_dates.append({
                            "date": dt.isoformat(),
                            "keyword": None,
                            "confidence": "low",
                        })
                except ValueError:
                    pass

    # 중복 제거
    seen = set()
    unique_dates = []
    for d in found_dates:
        key = (d["date"], d["keyword"], d["confidence"])
        if key not in seen:
            seen.add(key)
            unique_dates.append(d)
    found_dates = unique_dates

    # 가장 최근 발급일 선택 (키워드 매칭된 것 우선)
    if found_dates:
        # high confidence 우선, 그 다음 날짜 최신순
        found_dates.sort(key=lambda x: (x["confidence"] == "high", x["date"]), reverse=True)
        best = found_dates[0]
        return {
            "found": True,
            "issue_date": best["date"],
            "keyword": best["keyword"],
            "confidence": best["confidence"],
            "all_dates": found_dates,
        }

    return {"found": False, "issue_date": None, "confidence": "none", "all_dates": []}


def verify_date(date_info: dict, today, threshold_days: int) -> dict:
    """발급일이 기준일(threshold_days) 이내인지 검증"""
    if not date_info.get("found"):
        return {
            "status": "unknown",
            "signal": "yellow",
            "message": "문서에서 발급일자를 찾을 수 없습니다. 수동 확인이 필요합니다.",
            "days_elapsed": None,
        }

    issue_date = datetime.fromisoformat(date_info["issue_date"]).date()
    days_elapsed = (today - issue_date).days

    if days_elapsed < 0:
        return {
            "status": "unknown",
            "signal": "yellow",
            "message": f"발급일({issue_date})이 미래 날짜입니다. 확인이 필요합니다.",
            "days_elapsed": days_elapsed,
        }

    if days_elapsed <= threshold_days:
        return {
            "status": "valid",
            "signal": "green",
            "message": f"발급일({issue_date})로부터 {days_elapsed}일 경과 — {threshold_days}일 기준 이내 ✓",
            "days_elapsed": days_elapsed,
        }
    else:
        return {
            "status": "expired",
            "signal": "red",
            "message": f"발급일({issue_date})로부터 {days_elapsed}일 경과 — {threshold_days}일 기준 초과 ✗",
            "days_elapsed": days_elapsed,
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
