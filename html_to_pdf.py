"""
HTML → PDF 변환 스크립트 (이미지 손실 없음)
=============================================
Playwright 기반 — 실제 브라우저로 렌더링하여 PDF 생성

사용법:
    python html_to_pdf.py <HTML파일경로> [옵션]

옵션:
    --output <파일명>   출력 PDF 파일명 (기본: 입력파일명.pdf)
    --width <px>        페이지 너비 (기본: 1280)
    --scale <배율>      렌더링 배율 1.0~2.0 (기본: 1.0)
    --landscape         가로 방향 출력
    --no-bg             배경색/이미지 제외

설치:
    pip install playwright
    playwright install chromium

예시:
    python html_to_pdf.py index.html
    python html_to_pdf.py index.html --output dashboard.pdf --landscape
    python html_to_pdf.py index.html --scale 1.5 --width 1440
"""

import argparse
import os
import sys
from pathlib import Path


def convert(html_path, output=None, width=1280, scale=1.0, landscape=False, print_bg=True):
    html_path = Path(html_path).resolve()
    if not html_path.exists():
        print(f"[오류] 파일을 찾을 수 없습니다: {html_path}")
        sys.exit(1)

    if output is None:
        output = html_path.with_suffix(".pdf").name

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[오류] playwright가 설치되어 있지 않습니다.")
        print("  pip install playwright")
        print("  playwright install chromium")
        sys.exit(1)

    file_url = html_path.as_uri()
    print(f"  입력: {html_path.name}")
    print(f"  출력: {output}")
    print(f"  설정: {width}px, 배율 {scale}, {'가로' if landscape else '세로'}, 배경{'O' if print_bg else 'X'}")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 900})

        print("  브라우저 로딩 중...")
        page.goto(file_url, wait_until="networkidle")
        page.wait_for_timeout(2000)

        print("  PDF 생성 중...")
        page.pdf(
            path=output,
            format="A4",
            scale=scale,
            landscape=landscape,
            print_background=print_bg,
            margin={"top": "10mm", "right": "10mm", "bottom": "10mm", "left": "10mm"},
        )

        browser.close()

    size_kb = os.path.getsize(output) / 1024
    print(f"\n  완료! {output} ({size_kb:,.1f} KB)")


def main():
    parser = argparse.ArgumentParser(
        description="HTML → PDF 변환 (Playwright 기반, 이미지 무손실)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("html_path", help="변환할 HTML 파일 경로")
    parser.add_argument("--output", default=None, help="출력 PDF 파일명")
    parser.add_argument("--width", type=int, default=1280, help="뷰포트 너비 (기본: 1280)")
    parser.add_argument("--scale", type=float, default=1.0, help="렌더링 배율 (기본: 1.0)")
    parser.add_argument("--landscape", action="store_true", help="가로 방향")
    parser.add_argument("--no-bg", action="store_true", help="배경색/이미지 제외")
    args = parser.parse_args()

    convert(
        html_path=args.html_path,
        output=args.output,
        width=args.width,
        scale=args.scale,
        landscape=args.landscape,
        print_bg=not args.no_bg,
    )


if __name__ == "__main__":
    main()
