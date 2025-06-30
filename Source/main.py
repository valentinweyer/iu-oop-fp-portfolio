from habit import DailyHabit, HabitInstance
from datetime import date
from database import engine, save_habit, save_instance

       
habit_daily = DailyHabit(name="Mit Frauen sprechen Üben", description="Das ist ehrlich traurig")
habit_daily.get_data()

habit_instance = HabitInstance(habit=habit_daily, period_start=date.today())
habit_instance.get_data()
habit_instance.mark_completed()
habit_instance.get_data()
habit_instance.is_completed()
    


save_habit(engine, habit_daily)

save_instance(engine, habit_instance)



