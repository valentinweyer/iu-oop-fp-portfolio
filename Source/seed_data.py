
from datetime import date, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base
from models import DailyHabit, WeeklyHabit, HabitInstance, Habit

# Recreate database schema
target = "./habits.db"
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# Define sample habits
sample_habits = [
    DailyHabit(name="Brush Teeth", description="Morning and night"),
    DailyHabit(name="Meditate", description="10 minutes daily"),
    WeeklyHabit(name="Water Plants", description="Every Monday", weekday=0),  # Monday
    WeeklyHabit(name="Grocery Shopping", description="Weekend shopping", weekday=5),  # Saturday
    WeeklyHabit(name="Review Goals", description="Every Sunday", weekday=6),
]

# Seed habits and create historical instances
with SessionLocal() as session:
    # add habits
    for habit in sample_habits:
        session.add(habit)
    session.commit()

    # create instances with specific streak patterns
    for habit in session.query(Habit).all():
        # four weeks back from today
        start = date.today() - timedelta(weeks=4)
        # determine first period start
        if hasattr(habit, 'weekday') and habit.weekday is not None:
            delta = (habit.weekday - start.weekday() + 7) % 7
            current = start + timedelta(days=delta)
        else:
            current = start

        # Build custom completion patterns:
        # - For 'Brush Teeth': full streak of 4 days
        # - For 'Meditate': streak of 2, break, then streak of 1, break, then streak of 1
        # - For 'Water Plants': streak of 3 weeks, break, then streak of 1
        # - Others alternate every period
        pattern = []
        if habit.name == "Brush Teeth":
            pattern = [True, True, True, True]
        elif habit.name == "Meditate":
            pattern = [True, True, False, True]
        elif habit.name == "Water Plants":
            pattern = [True, True, True, False]
        else:
            pattern = [i % 2 == 0 for i in range(4)]

        # create four consecutive periods
        for completed_flag in pattern:
            inst = HabitInstance(habit=habit, period_start=current)
            if completed_flag:
                inst.mark_completed()
            session.add(inst)
            # advance to next period
            current = habit.next_period_start(current)

    session.commit()

print("Database seeded with sample habits, instances, and streak patterns.")
