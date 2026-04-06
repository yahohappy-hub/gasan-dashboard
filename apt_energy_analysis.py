"""
공용부 에너지 데이터 분석 스크립트
====================================
사용법:
    python apt_energy_analysis.py <CSV파일경로> [옵션]

옵션:
    --reversal-detail   누적값 역전 개별 발생 위치 전체 출력 (기본: 집계만)
    --encoding <enc>    인코딩 지정 (기본: 자동 감지)
    --output <파일명>    결과를 텍스트 파일로 저장

예시:
    python apt_energy_analysis.py 노원센트럴푸르지오01.csv
    python apt_energy_analysis.py data.csv --reversal-detail
    python apt_energy_analysis.py data.csv --output result.txt
"""

import sys
import os
import argparse
import pandas as pd
from datetime import datetime


# ─────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────

def detect_encoding(filepath):
    for enc in ["utf-8-sig", "cp949", "euc-kr", "utf-8", "latin1"]:
        try:
            pd.read_csv(filepath, encoding=enc, nrows=5)
            return enc
        except Exception:
            continue
    raise ValueError("지원되는 인코딩을 찾을 수 없습니다.")


def sep(char="=", n=72):
    return char * n


def print_table(headers, rows, col_widths=None, aligns=None, out=None):
    """텍스트 테이블 출력. out이 None이면 stdout, 아니면 파일 객체에 씀."""
    def pr(s):
        if out:
            out.write(s + "\n")
        else:
            print(s)

    if col_widths is None:
        col_widths = []
        for i, h in enumerate(headers):
            w = max(len(str(h)), max((len(str(r[i])) for r in rows), default=0))
            col_widths.append(w + 2)
    if aligns is None:
        aligns = ['<'] * len(headers)

    def fmt(val, w, a):
        s = str(val)
        return s.rjust(w) if a == '>' else s.center(w) if a == '^' else s.ljust(w)

    pr("  " + "  ".join(fmt(h, col_widths[i], '^') for i, h in enumerate(headers)))
    pr("  " + "  ".join("-" * col_widths[i] for i in range(len(headers))))
    for row in rows:
        pr("  " + "  ".join(fmt(row[i], col_widths[i], aligns[i]) for i in range(len(headers))))


class Output:
    """stdout + 선택적 파일 동시 출력"""
    def __init__(self, filepath=None):
        self.f = open(filepath, "w", encoding="utf-8") if filepath else None

    def pr(self, s=""):
        print(s)
        if self.f:
            self.f.write(s + "\n")

    def table(self, headers, rows, col_widths=None, aligns=None):
        print_table(headers, rows, col_widths, aligns)
        if self.f:
            print_table(headers, rows, col_widths, aligns, out=self.f)

    def close(self):
        if self.f:
            self.f.close()


# ─────────────────────────────────────────
# 메인 분석
# ─────────────────────────────────────────

def analyze(filepath, reversal_detail=False, encoding=None, output_file=None):

    o = Output(output_file)

    # ── 파일 로드 ──
    if not os.path.exists(filepath):
        print(f"[오류] 파일을 찾을 수 없습니다: {filepath}")
        sys.exit(1)

    if encoding is None:
        encoding = detect_encoding(filepath)

    try:
        df = pd.read_csv(filepath, encoding=encoding)
    except Exception as e:
        print(f"[오류] 파일 로드 실패: {e}")
        sys.exit(1)

    required = {"sDate", "sHour", "sApt", "sHome", "fElect", "fGas", "fWater", "fHotWater", "fHot"}
    missing = required - set(df.columns)
    if missing:
        print(f"[오류] 필수 컬럼 누락: {missing}")
        sys.exit(1)

    df["sDate"] = pd.to_datetime(df["sDate"])
    df["sHour"] = df["sHour"].astype(int)
    df["sApt"]  = df["sApt"].astype(str)
    df["sHome"] = df["sHome"].astype(str)

    ECOLS = ["fElect", "fGas", "fWater", "fHotWater", "fHot"]
    EUNIT = {"fElect": "kWh", "fGas": "m³", "fWater": "m³", "fHotWater": "m³", "fHot": "Mcal"}
    EKOR  = {"fElect": "전력", "fGas": "가스", "fWater": "수도", "fHotWater": "온수", "fHot": "열량"}

    date_min   = df["sDate"].min()
    date_max   = df["sDate"].max()
    date_range = pd.date_range(date_min, date_max, freq="D")
    apts       = sorted(df["sApt"].unique())
    homes      = sorted(df["sHome"].unique())
    fname      = os.path.basename(filepath)

    # ── 헤더 출력 ──
    o.pr()
    o.pr(sep())
    o.pr(f"  [공용부] 에너지 사용량 분석 리포트")
    o.pr(sep())
    o.pr(f"  파일명   : {fname}")
    o.pr(f"  인코딩   : {encoding}")
    o.pr(f"  데이터   : {date_min.date()} ~ {date_max.date()} ({len(date_range)}일)")
    o.pr(f"  총 레코드: {len(df):,}건")
    o.pr(f"  sApt     : {', '.join(apts)}")
    o.pr(f"  sHome    : {len(homes)}개")
    o.pr(f"  분석시각 : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ════════════════════════════════════════════
    # [ 1 ] sHome 종류 및 개수
    # ════════════════════════════════════════════
    o.pr()
    o.pr(sep("-"))
    o.pr("  [ 1 ]  sHome 종류 및 총 개수")
    o.pr(sep("-"))
    o.pr(f"  총 계량 대상 수 : {len(homes)}개")
    o.pr()

    rows = []
    for i, h in enumerate(homes, 1):
        cnt      = len(df[df["sHome"] == h])
        apt_list = sorted(df[df["sHome"] == h]["sApt"].unique())
        rows.append([str(i), h, f"{cnt:,}", ", ".join(apt_list)])
    o.table(
        ["No.", "sHome", "레코드수", "소속 sApt"],
        rows,
        col_widths=[5, 28, 9, 30],
        aligns=[">", "<", ">", "<"]
    )

    # ════════════════════════════════════════════
    # [ 2 ] 결측치 분석
    # ════════════════════════════════════════════
    o.pr()
    o.pr(sep("-"))
    o.pr("  [ 2 ]  결측치 분석")
    o.pr(sep("-"))

    # ── 2-1. 시간 누락 ──
    o.pr()
    o.pr("  ▶ 2-1. 시간 누락")

    first_apt  = apts[0]
    first_home = sorted(df[df["sApt"] == first_apt]["sHome"].unique())[0]
    sub0       = df[(df["sApt"] == first_apt) & (df["sHome"] == first_home)].set_index(["sDate", "sHour"])
    expected   = pd.MultiIndex.from_product([date_range, list(range(24))], names=["sDate", "sHour"])
    miss0      = sorted(expected.difference(sub0.index).tolist())

    if len(miss0) == 0:
        o.pr("  시간 누락 없음 (완전 수집)")
    else:
        # 패턴 동일 여부
        all_same   = True
        diff_items = []
        for apt in apts:
            for home in sorted(df[df["sApt"] == apt]["sHome"].unique()):
                sub  = df[(df["sApt"] == apt) & (df["sHome"] == home)].set_index(["sDate", "sHour"])
                miss = sorted(expected.difference(sub.index).tolist())
                if miss != miss0:
                    all_same = False
                    diff_items.append((apt, home, miss))

        if all_same:
            o.pr(f"  전체 {len(homes)}개 계량 대상 공통 누락: {len(miss0)}개 시간대")
        else:
            o.pr(f"  대표({first_apt}/{first_home}) 누락: {len(miss0)}건")
            o.pr(f"  패턴이 다른 항목: {len(diff_items)}건 (아래 참조)")

        # 3열 출력
        o.pr()
        padded = miss0 + [("", "")] * ((3 - len(miss0) % 3) % 3)
        header_row = f"  {'날짜·시각':<18}  {'날짜·시각':<18}  {'날짜·시각':<18}"
        divider_row = f"  {'─'*18}  {'─'*18}  {'─'*18}"
        o.pr(header_row)
        o.pr(divider_row)
        for i in range(0, len(padded), 3):
            cols = []
            for j in range(3):
                d, h = padded[i + j]
                if d == "":
                    cols.append(f"{'':18}")
                else:
                    cols.append(f"{str(pd.Timestamp(d).date())} {str(h).zfill(2)+':00':<7}")
            o.pr("  " + "  ".join(cols))

        if not all_same:
            o.pr()
            o.pr("  패턴이 다른 항목:")
            for apt, home, miss in diff_items:
                o.pr(f"    [{apt} / {home}]  누락 {len(miss)}건  →  {[str(pd.Timestamp(d).date())+' '+str(h).zfill(2)+':00' for d,h in miss]}")

    # ── 2-2. 누적값 역전 ──
    o.pr()
    o.pr("  ▶ 2-2. 누적값 역전")

    rev_summary = []
    rev_detail  = []

    for apt in apts:
        for home in sorted(df[df["sApt"] == apt]["sHome"].unique()):
            sub = df[(df["sApt"] == apt) & (df["sHome"] == home)].sort_values(["sDate", "sHour"]).reset_index(drop=True)
            for col in ECOLS:
                diff = sub[col].diff()
                bad  = diff[diff < 0]
                if len(bad) == 0:
                    continue
                hrs = sorted(set(int(sub.loc[i, "sHour"]) for i in bad.index))
                rev_summary.append({
                    "동": apt, "sHome": home, "항목": f"{EKOR[col]}({col})",
                    "건수": len(bad), "발생시각": ", ".join(f"{h:02d}:00" for h in hrs)
                })
                for idx in bad.index:
                    prev = sub.loc[idx - 1]
                    curr = sub.loc[idx]
                    rev_detail.append({
                        "동": apt, "sHome": home, "항목": col,
                        "이전시각": f"{str(prev['sDate'].date())} {int(prev['sHour']):02d}:00",
                        "이전값":   round(prev[col], 3),
                        "현재시각": f"{str(curr['sDate'].date())} {int(curr['sHour']):02d}:00",
                        "현재값":   round(curr[col], 3),
                        "감소량":   round(diff[idx], 3)
                    })

    if len(rev_summary) == 0:
        o.pr("  누적값 역전 없음")
    else:
        total_rev = sum(r["건수"] for r in rev_summary)
        patterns  = set(r["발생시각"] for r in rev_summary)
        o.pr(f"  총 역전 건수: {total_rev:,}건  |  영향 항목 수: {len(rev_summary)}개")
        if len(patterns) == 1:
            o.pr(f"  ※ 전체 공통 발생 시각 패턴: {list(patterns)[0]}")
        o.pr()
        rows2 = [[r["동"], r["sHome"], r["항목"], str(r["건수"]), r["발생시각"]] for r in rev_summary]
        o.table(
            ["동", "sHome", "항목", "건수", "발생시각패턴"],
            rows2,
            col_widths=[8, 24, 22, 6, 22],
            aligns=["^", "<", "<", ">", "<"]
        )

        if reversal_detail:
            o.pr()
            o.pr("  ── 역전 개별 발생 위치 상세 ──")
            o.pr()
            rows3 = [
                [r["동"], r["sHome"], r["항목"],
                 r["이전시각"], f"{r['이전값']:,.3f}",
                 r["현재시각"], f"{r['현재값']:,.3f}",
                 f"{r['감소량']:,.3f}"]
                for r in rev_detail
            ]
            o.table(
                ["동", "sHome", "항목", "이전 시각", "이전값", "현재 시각", "현재값", "감소량"],
                rows3,
                col_widths=[8, 22, 14, 18, 14, 18, 14, 10],
                aligns=["^", "<", "<", "<", ">", "<", ">", ">"]
            )

    # ── 2-3. 전체 0 항목 ──
    o.pr()
    o.pr("  ▶ 2-3. 에너지 항목별 전체 0 여부")
    for col in ECOLS:
        all_zero = (df[col] == 0).all()
        status = "전체 0  ← 미계량 또는 미사용 여부 확인 필요" if all_zero else "정상 (비零 값 존재)"
        o.pr(f"  {EKOR[col]:5s}({col:10s}) : {status}")

    # ════════════════════════════════════════════
    # [ 3 ] 에너지 사용량
    # ════════════════════════════════════════════
    o.pr()
    o.pr(sep("-"))
    o.pr("  [ 3 ]  기간 에너지 사용량")
    o.pr(sep("-"))

    has_reversal = len(rev_summary) > 0
    method = "양수 증분 합산 (역전 오류 보정)" if has_reversal else "최종 누적값 − 최초 누적값"
    o.pr(f"  산출 방식: {method}")
    o.pr(f"  기간: {date_min.date()} {df[df['sDate']==date_min]['sHour'].min():02d}:00 ~ {date_max.date()} {df[df['sDate']==date_max]['sHour'].max():02d}:00")

    # 사용량 산출
    results = []
    for apt in apts:
        for home in sorted(df[df["sApt"] == apt]["sHome"].unique()):
            sub = df[(df["sApt"] == apt) & (df["sHome"] == home)].sort_values(["sDate", "sHour"])
            row = {"동": apt, "sHome": home}
            for col in ECOLS:
                if has_reversal:
                    row[col] = round(sub[col].diff().clip(lower=0).sum(), 3)
                else:
                    row[col] = round(sub[col].iloc[-1] - sub[col].iloc[0], 3)
            results.append(row)
    rdf = pd.DataFrame(results)

    # ── 3-1. 전체 합계 ──
    o.pr()
    o.pr("  ▶ 3-1. 전체 합계")
    totals = rdf[ECOLS].sum().round(3)
    for col in ECOLS:
        o.pr(f"  {EKOR[col]:5s}({col:10s}): {totals[col]:>15,.3f}  {EUNIT[col]}")

    # ── 3-2. sApt별 합계 ──
    o.pr()
    o.pr("  ▶ 3-2. sApt(동)별 합계")
    apt_sum = rdf.groupby("동")[ECOLS].sum().round(3)
    rows_apt = [[apt] + [f"{apt_sum.loc[apt, c]:,.3f}" for c in ECOLS] for apt in apt_sum.index]
    o.table(
        ["동"] + [f"{EKOR[c]}({EUNIT[c]})" for c in ECOLS],
        rows_apt,
        col_widths=[10, 14, 10, 10, 12, 12],
        aligns=["<", ">", ">", ">", ">", ">"]
    )

    # ── 3-3. 계량 대상별 상세 ──
    o.pr()
    o.pr("  ▶ 3-3. 계량 대상별 상세 사용량")
    for apt in apts:
        o.pr(f"\n  [ {apt} ]")
        sub_rdf = rdf[rdf["동"] == apt]
        rows_sub = [
            [row["sHome"]] + [f"{row[c]:,.3f}" for c in ECOLS]
            for _, row in sub_rdf.iterrows()
        ]
        o.table(
            ["sHome"] + [f"{EKOR[c]}({EUNIT[c]})" for c in ECOLS],
            rows_sub,
            col_widths=[26, 14, 10, 10, 12, 12],
            aligns=["<", ">", ">", ">", ">", ">"]
        )

    # ── 완료 ──
    o.pr()
    o.pr(sep())
    o.pr("  분석 완료")
    o.pr(sep())
    o.pr()
    o.close()

    if output_file:
        print(f"\n  결과 저장 완료: {output_file}")


# ─────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="공용부 에너지 데이터 분석",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("filepath", help="분석할 CSV 파일 경로")
    parser.add_argument("--reversal-detail", action="store_true",
                        help="역전 개별 발생 위치 전체 출력")
    parser.add_argument("--encoding", default=None,
                        help="파일 인코딩 (기본: 자동 감지)")
    parser.add_argument("--output", default=None,
                        help="결과를 텍스트 파일로 저장할 경로")
    args = parser.parse_args()

    analyze(
        filepath=args.filepath,
        reversal_detail=args.reversal_detail,
        encoding=args.encoding,
        output_file=args.output
    )


if __name__ == "__main__":
    main()
