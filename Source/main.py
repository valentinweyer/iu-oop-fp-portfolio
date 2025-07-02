from datetime import date

from models import DailyHabit, WeeklyHabit, HabitInstance
from database import engine, save_habit, save_instance, complete_task

       
habit_daily = DailyHabit(name="er", description="ererer")

habit_instance = HabitInstance(habit=habit_daily, period_start=date.today())
habit_instance.is_completed()

habit_weekly = WeeklyHabit(name="Weekly Habit", description="This is a weekly habit")
habit_instance = HabitInstance(habit=habit_weekly, period_start=date.today())
habit_instance.is_completed()


save_habit(engine, habit_weekly)

save_instance(engine, habit_instance)

complete_task(engine, "df3d7a9b-6d26-4a6c-a7da-73e195f84770")



