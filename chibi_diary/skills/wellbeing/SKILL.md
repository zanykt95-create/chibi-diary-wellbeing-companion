---
name: wellbeing
description: >
  Analyse and surface wellbeing insights from a user's diary history.
  Activate this skill when the user wants to understand their emotional
  patterns, journaling streak, or monthly mood recap. The skill provides
  step-by-step guidance on calling get_mood_trend, get_streak, and
  get_monthly_recap tools and formatting a warm, encouraging summary.
allowed-tools: get_mood_trend get_streak get_monthly_recap get_today_date
---

# Wellbeing Skill — Chibi Diary

## Purpose
This skill guides the Memory Agent in surfacing personalised wellbeing
insights from the user's SQLite diary history.

## When to activate
Activate this skill whenever:
- The user asks about their mood history, emotional trends, or patterns.
- The user asks how many days they have journaled consecutively (streak).
- The user asks for a monthly mood recap or summary.
- The pipeline finishes saving a diary entry and you want to add a
  contextual wellbeing insight in the closing response.

## Step-by-step procedure

### Step A — Get today's date
Call `get_today_date()` first if you don't already have today's date from
the pipeline context.

### Step B — Fetch mood trend
Call `get_mood_trend(days=7)`.
- Returns a list of (date, mood, mood_score) tuples for the past 7 days.
- Identify the dominant mood (most frequent) and whether the trend is
  improving (scores rising) or declining (scores falling).

### Step C — Fetch streak
Call `get_streak()`.
- Returns the current consecutive journaling streak in days.
- If streak >= 3, include a streak celebration in your response.
- If streak == 1, use a gentle encouragement to keep going.

### Step D — Fetch monthly recap (optional)
Call `get_monthly_recap(year=<YYYY>, month=<MM>)` using the current month.
- Returns entry count, mood distribution, and average score for the month.
- Include this if the user specifically asks for a monthly summary, or if
  today is the last day of the month.

### Step E — Format the insight
Write a warm, 2–3 sentence wellbeing insight in the same language as the
user's diary entry. Structure:
1. Dominant emotion observation from trend.
2. Streak acknowledgement (celebrate ≥3 days; encourage at 1 day).
3. One gentle, forward-looking suggestion based on the mood data.

## Output format
Return the insight as plain prose — NO JSON, NO bullet points.
End with a single relevant emoji (🌸 😊 🌟 💛 🌈).

## Example output (English)
"This week your heart has been full of gratitude — a beautiful pattern to
notice! You've journaled 5 days in a row, which is something to be proud of.
Keep leaning into those grateful moments; they're your superpower 🌟"

## Example output (Vietnamese)
"Tuần này tâm trạng của bạn chủ yếu là biết ơn — thật đẹp khi nhận ra điều
đó! Bạn đã ghi nhật ký 5 ngày liên tiếp, hãy tiếp tục nhé. Hãy trân trọng
những khoảnh khắc ấm áp này, chúng là nguồn sức mạnh của bạn 🌸"
