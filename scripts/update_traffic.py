import os
import json
from datetime import datetime
from collections import defaultdict

import requests
import matplotlib.pyplot as plt


# ---------------------------------------------------------
# 여기를 너의 GitHub 계정 / 리포 이름으로 맞게 수정
# ---------------------------------------------------------
OWNER = "SungHunYang"          # GitHub 사용자명
REPO = "SungHunYang.github.io" # 이 리포 이름
# ---------------------------------------------------------


def fetch_github_traffic(token: str):
    """
    GitHub 트래픽 API에서 최근 14일의 일일 트래픽 가져오기
    """
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/traffic/views?per=day"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()["views"]  # list of {timestamp, count, uniques}


def load_json(path: str):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def aggregate_stats(traffic_dict: dict):
    """
    전체 히스토리(history.json)를 기반으로
    daily / weekly / monthly 데이터 생성
    """
    if not traffic_dict:
        return [], [], [], [], [], []

    dates = sorted(traffic_dict.keys())

    # daily
    daily_dates = dates
    daily_uniques = [traffic_dict[d]["uniques"] for d in dates]

    # weekly
    week_totals = defaultdict(int)
    for d in dates:
        dt = datetime.fromisoformat(d)
        week_key = f"{dt.isocalendar().year}-W{dt.isocalendar().week:02d}"
        week_totals[week_key] += traffic_dict[d]["uniques"]

    weekly_keys = sorted(week_totals.keys())
    weekly_vals = [week_totals[w] for w in weekly_keys]

    # monthly
    month_totals = defaultdict(int)
    for d in dates:
        dt = datetime.fromisoformat(d)
        month_key = f"{dt.year}-{dt.month:02d}"
        month_totals[month_key] += traffic_dict[d]["uniques"]

    monthly_keys = sorted(month_totals.keys())
    monthly_vals = [month_totals[m] for m in monthly_keys]

    return (
        daily_dates,
        daily_uniques,
        weekly_keys,
        weekly_vals,
        monthly_keys,
        monthly_vals,
    )


def plot_line(x, y, title, path, xlabel="date", ylabel="unique visitors"):
    """
    다크 테마 + Flat UI blue + 투명 배경 + annotation 스타일 그래프
    """
    if not x or not y:
        # 데이터가 아직 없으면 그래프 안 만듦
        return

    # 다크모드 테마
    plt.style.use("dark_background")

    # 투명 배경
    fig = plt.figure(figsize=(8, 3))
    fig.patch.set_alpha(0.0)
    ax = fig.add_subplot(111)

    # 색상 설정 (Flat UI)
    line_color = "#3498db"   # 파란색
    marker_color = "#5dade2" # 밝은 파란색
    text_color = "#ecf0f1"   # 밝은 회색

    # 굵은 선 + 마커
    ax.plot(
        x,
        y,
        color=line_color,
        linewidth=2.5,
        marker="o",
        markersize=6,
        markerfacecolor=marker_color,
    )

    # 각 점 위에 숫자 annotation
    for i, value in enumerate(y):
        ax.text(
            x[i],
            value,
            str(value),
            color=text_color,
            fontsize=8,
            ha="center",
            va="bottom",
        )

    # 제목 / 라벨
    ax.set_title(title, color=text_color, fontsize=12, pad=10)
    ax.set_xlabel(xlabel, color=text_color)
    ax.set_ylabel(ylabel, color=text_color)

    # 축 눈금 색상 및 회전
    plt.xticks(rotation=45, ha="right", color=text_color, fontsize=8)
    plt.yticks(color=text_color, fontsize=8)

    # 축 배경 투명
    ax.patch.set_alpha(0.0)

    # 얇은 grid
    ax.grid(
        True,
        linestyle="-",
        linewidth=0.3,
        color="#555555",
        alpha=0.4,
    )

    plt.tight_layout()

    # 투명 배경 PNG 저장
    os.makedirs(os.path.dirname(path), exist_ok=True)
    plt.savefig(path, transparent=True, dpi=200)
    plt.close()


def main():
    # GitHub Actions 또는 로컬에서 환경변수 GH_TOKEN 으로 토큰 제공
    token = os.environ["GH_TOKEN"]

    # 1) GitHub에서 최근 14일 트래픽 가져오기
    views = fetch_github_traffic(token)

    # -----------------------------
    # 2) DAILY: 최근 14일만 저장
    # -----------------------------
    daily_path = "stats/traffic.json"
    daily_stats = {}

    for v in views:
        day = v["timestamp"][:10]  # YYYY-MM-DD
        daily_stats[day] = {
            "count": v["count"],
            "uniques": v["uniques"],
        }

    # 정렬 후 14일만 유지
    sorted_days = sorted(daily_stats.keys())
    recent_days = sorted_days[-14:]
    daily_stats = {d: daily_stats[d] for d in recent_days}

    save_json(daily_path, daily_stats)

    # -----------------------------
    # 3) HISTORY: 모든 날짜 누적 저장
    # -----------------------------
    history_path = "stats/traffic_history.json"
    history = load_json(history_path)

    for v in views:
        day = v["timestamp"][:10]
        history[day] = {
            "count": v["count"],
            "uniques": v["uniques"],
        }

    save_json(history_path, history)

    # -----------------------------
    # 4) 그래프 생성
    #    - Daily 그래프: 최근 14일만
    #    - Weekly / Monthly: 전체 history 기반
    # -----------------------------
    (
        _daily_dates_all,
        _daily_vals_all,
        weekly_keys,
        weekly_vals,
        monthly_keys,
        monthly_vals,
    ) = aggregate_stats(history)

    # Daily (last 14 days)
    recent_daily_dates = sorted(daily_stats.keys())
    recent_daily_vals = [daily_stats[d]["uniques"] for d in recent_daily_dates]

    plot_line(
        recent_daily_dates,
        recent_daily_vals,
        "Daily Unique Visitors (last 14 days)",
        "stats/traffic_daily.png",
    )

    # Weekly
    plot_line(
        weekly_keys,
        weekly_vals,
        "Weekly Unique Visitors",
        "stats/traffic_weekly.png",
        xlabel="week",
    )

    # Monthly
    plot_line(
        monthly_keys,
        monthly_vals,
        "Monthly Unique Visitors",
        "stats/traffic_monthly.png",
        xlabel="month",
    )


if __name__ == "__main__":
    main()
