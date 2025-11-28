import os
import json
from datetime import datetime
from collections import defaultdict

import requests
import matplotlib.pyplot as plt


# ---------------------------------------------------------
# 설정 (너의 GitHub USER/REPO 로 바꾸기)
# ---------------------------------------------------------
OWNER = "SungHunYang"          # GitHub 사용자명
REPO = "SungHunYang.github.io" # 이 repo 이름
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


def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def aggregate_stats(traffic_dict):
    """
    전체 히스토리(history.json)를 기반으로
    daily / weekly / monthly 데이터 생성
    """
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

    return (daily_dates, daily_uniques,
            weekly_keys, weekly_vals,
            monthly_keys, monthly_vals)


def plot_line(x, y, title, path, xlabel="date", ylabel="unique visitors"):
    if not x:
        return

    plt.figure(figsize=(8, 3))
    plt.plot(x, y, marker="o")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    os.makedirs(os.path.dirname(path), exist_ok=True)
    plt.savefig(path)
    plt.close()


def main():
    token = os.environ["GH_TOKEN"]

    # GitHub에서 최근 14일 트래픽 가져오기
    views = fetch_github_traffic(token)

    # -----------------------------
    # DAILY: 최근 14일만 저장
    # -----------------------------
    daily_path = "stats/traffic.json"
    daily_stats = {}

    for v in views:
        day = v["timestamp"][:10]
        daily_stats[day] = {
            "count": v["count"],
            "uniques": v["uniques"],
        }

    # 정렬 후 14일만 유지
    sorted_days = sorted(daily_stats.keys())
    recent_days = sorted_days[-14:]  # 최근 14일
    daily_stats = {d: daily_stats[d] for d in recent_days}

    save_json(daily_path, daily_stats)

    # -----------------------------
    # HISTORY: 모든 날짜 누적 저장
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
    # 그래프 생성 (weekly / monthly = history 기반)
    # -----------------------------
    (
        daily_dates, daily_vals,
        weekly_keys, weekly_vals,
        monthly_keys, monthly_vals
    ) = aggregate_stats(history)

    # Daily는 최근 14일만 따로 plot
    recent_daily_dates = sorted(daily_stats.keys())
    recent_daily_vals = [daily_stats[d]["uniques"] for d in recent_daily_dates]

    plot_line(recent_daily_dates, recent_daily_vals,
              "Daily Unique Visitors (last 14 days)",
              "stats/traffic_daily.png")

    plot_line(weekly_keys, weekly_vals,
              "Weekly Unique Visitors",
              "stats/traffic_weekly.png",
              xlabel="week")

    plot_line(monthly_keys, monthly_vals,
              "Monthly Unique Visitors",
              "stats/traffic_monthly.png",
              xlabel="month")


if __name__ == "__main__":
    main()
