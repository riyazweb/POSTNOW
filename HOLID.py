import holidays
from datetime import date, timedelta

# 1. Load all Indian holidays for the current year
in_holidays = holidays.IN(years=date.today().year)

# 2. Figure out the dates for "Today" and "7 days from now"
today = date.today()
one_week_later = today + timedelta(days=30)

# 3. Check which holidays fall exactly in this week's window
this_week_holidays = []
for dt, name in sorted(in_holidays.items()):
    if today <= dt <= one_week_later:
        this_week_holidays.append(f"{dt.strftime('%A, %b %d')}: {name}")

# 4. Print the result!
print("Holidays this week:", this_week_holidays)
