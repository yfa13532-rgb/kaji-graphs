# --------------------------------------------------
# ステップ1：ライブラリの準備とデータ読み込み
# --------------------------------------------------
import pandas as pd
import plotly.express as px
import os

week_no = int(os.environ.get("WEEK_NO", "60"))

sheet_id = "1986ombf3LAKeA4y_3aq_hQFvc2iUVWIhCpHEZQh_-aE"
gid = "0"

url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
df = pd.read_csv(url)

df["date"] = pd.to_datetime(df["date"])

# time_minを数値として扱う
# 子ども担当の行は空欄なのでNaNになる
df["time_min"] = pd.to_numeric(
    df["time_min"],
    errors="coerce"
)

# 担当者の余分な空白を削除
df["担当者"] = (
    df["担当者"]
    .astype("string")
    .str.strip()
)


# --------------------------------------------------
# ステップ2：週番号を指定
# --------------------------------------------------

df_week = df[
    df["week_no"] == week_no
].copy()

# 指定した週のデータがない場合は停止
if df_week.empty:
    raise ValueError(
        f"第{week_no}週のデータが見つかりません。"
    )


# --------------------------------------------------
# ステップ3：自分と子どもの家事を分ける
# --------------------------------------------------

# 自分が担当した家事
df_self = df_week[
    df_week["担当者"] == "自分"
].copy()

# 子どもが担当した家事
df_child = df_week[
    df_week["担当者"].notna()
    & (df_week["担当者"] != "自分")
].copy()


# --------------------------------------------------
# ステップ4：公開用の名前に変換
# --------------------------------------------------

# スプレッドシートでは実名のまま管理し、
# ブログ公開用グラフだけ匿名化する
name_map = {
    "なお": "子A",
    "しん": "子B"
}

df_child["公開名"] = (
    df_child["担当者"]
    .map(name_map)
    .fillna("子ども")
)

# 公開用グラフには実名列を渡さない
# → HTMLファイルにも実名を含めない
df_child_public = df_child[
    ["date", "task", "公開名"]
].copy()


# ==================================================
# グラフ1：日ごとの合計家事時間
# 自分が担当した家事のみ
# ==================================================

daily_total = (
    df_self
    .groupby("date")["time_min"]
    .sum()
    .reset_index()
)

# 自分の家事が0分の日も表示できるようにする
all_dates = pd.DataFrame({
    "date": sorted(
        df_week["date"]
        .dropna()
        .unique()
    )
})

daily_total = pd.merge(
    all_dates,
    daily_total,
    on="date",
    how="left"
)

daily_total["time_min"] = (
    daily_total["time_min"]
    .fillna(0)
)

daily_total["time_hour"] = (
    daily_total["time_min"] / 60
)

fig_daily = px.bar(
    daily_total,
    x="date",
    y="time_hour",
    title=f"第{week_no}週：日ごとの合計家事時間",
    labels={
        "date": "日付",
        "time_hour": "合計時間（時間）"
    },
    text=daily_total["time_hour"].round(1),
    height=500
)

max_val = daily_total["time_hour"].max()

fig_daily.update_traces(
    textposition="outside"
)

fig_daily.update_layout(
    title_x=0.5,
    margin=dict(t=80),
    yaxis=dict(
        range=[0, max_val + 1]
    )
)

fig_daily.update_xaxes(
    tickformat="%m/%d",
    dtick=24 * 60 * 60 * 1000
)


# ==================================================
# グラフ2：子どもが担当した家事
# 子どもの家事がある週だけ作成
# ==================================================

fig_child = None

if not df_child_public.empty:

    fig_child = px.scatter(
        df_child_public,
        x="date",
        y="task",
        color="公開名",
        title=f"第{week_no}週：子どもが担当した家事",
        labels={
            "date": "日付",
            "task": "家事項目",
            "公開名": "担当者"
        },
        height=500
    )

    fig_child.update_traces(
        marker=dict(
            size=16
        )
    )

    fig_child.update_layout(
        title_x=0.5
    )

    # その週の全日付が横軸に出るようにする
    min_date = df_week["date"].min()
    max_date = df_week["date"].max()

    fig_child.update_xaxes(
        tickformat="%m/%d",
        dtick=24 * 60 * 60 * 1000,
        range=[
            min_date - pd.Timedelta(hours=12),
            max_date + pd.Timedelta(hours=12)
        ]
    )


# ==================================================
# グラフ3：家事1回あたりの平均時間＋回数
# 自分が担当した家事のみ
# ==================================================

average_time = (
    df_self
    .groupby("task")["time_min"]
    .mean()
    .reset_index()
)

task_count = (
    df_self
    .groupby("task")
    .size()
    .reset_index(name="count")
)

merged = pd.merge(
    average_time,
    task_count,
    on="task"
)

merged = merged.sort_values(
    "time_min",
    ascending=True
)

merged["label"] = (
    merged["time_min"]
    .round(1)
    .astype(str)
    + "分（"
    + merged["count"]
    .astype(str)
    + "回）"
)

fig_average = px.bar(
    merged,
    x="time_min",
    y="task",
    orientation="h",
    title=f"第{week_no}週：家事1回当たりの平均時間",
    labels={
        "task": "家事の種類",
        "time_min": "平均時間（分）"
    },
    text="label",
    height=500
)

fig_average.update_traces(
    textposition="outside"
)

fig_average.update_layout(
    title_x=0.5,
    xaxis=dict(
        range=[
            0,
            merged["time_min"].max() + 10
        ]
    )
)


# ==================================================
# グラフ4：家事時間の内訳
# 自分が担当した家事のみ
# ==================================================

total_time_per_task = (
    df_self
    .groupby("task")["time_min"]
    .sum()
    .reset_index()
)

fig_pie = px.pie(
    total_time_per_task,
    names="task",
    values="time_min",
    title=f"第{week_no}週：家事時間の内訳（割合）",
    hole=0.4,
    height=500
)

fig_pie.update_traces(
    textposition="inside",
    textinfo="percent+label",
    sort=True,
    direction="clockwise"
)

fig_pie.update_layout(
    title_x=0.5
)


# ==================================================
# グラフを画面で確認
# ==================================================

# 1. 自分の日別家事時間
fig_daily.show()

# 2. 子どもの担当家事
# 子どもの家事がない週は自動で飛ばす
if fig_child is not None:
    fig_child.show()

# 3. 家事1回あたりの平均時間
fig_average.show()

# 4. 家事時間の内訳
fig_pie.show()


# --------------------------------------------------
# 確認用
# --------------------------------------------------

print(
    f"自分が担当した家事：{len(df_self)}件"
)

print(
    f"子どもが担当した家事：{len(df_child)}件"
)

if not df_child.empty:
    print("\n公開用の担当者別件数")
    print(
        df_child["公開名"]
        .value_counts()
    )

# ==================================================
# HTMLファイル出力
# ==================================================

# 出力するグラフを記事掲載順に並べる
graphs = [
    ("daily_total", fig_daily)
]

# 子どもの家事がある週だけ追加
if fig_child is not None:
    graphs.append(
        ("child_tasks", fig_child)
    )

graphs.extend([
    ("average_time", fig_average),
    ("pie_chart", fig_pie)
])


# グラフ番号を1から順番に自動で付ける
for graph_no, (name, fig) in enumerate(
    graphs,
    start=1
):

    filename = (
        f"week{week_no}_"
        f"graph{graph_no}_"
        f"{name}.html"
    )

    output_dir = f"week{week_no}"
    os.makedirs(output_dir, exist_ok=True)

    fig.write_html(
        os.path.join(output_dir, filename),
        full_html=False,
        include_plotlyjs="cdn"
    )

    print(filename)


print("HTMLファイルを作成しました。")
