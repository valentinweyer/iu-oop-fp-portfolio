from datetime import date, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base
from models import DailyHabit, WeeklyHabit, HabitInstance, Habit

# Recreate database schema
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# Sample habits
sample_habits = [
    DailyHabit(name="Brush Teeth", description="Morning and night"),
    DailyHabit(name="Meditate", description="10 minutes daily"),
    WeeklyHabit(name="Water Plants", description="Every Monday"),
    WeeklyHabit(name="Grocery Shopping", description="Weekend shopping", weekday=5),  # Friday=4, Saturday=5
    WeeklyHabit(name="Review Goals", description="Every Sunday", weekday=6),
]

# Create habits and 4 weeks of instances
with SessionLocal() as session:
    # add habits
    for habit in sample_habits:
        session.add(habit)
    session.commit()

    # generate instances
    for habit in session.query(Habit).all():
        start = date.today() - timedelta(weeks=4)
        # determine first period start
        if hasattr(habit, 'weekday') and habit.weekday is not None:
            # move to the next matching weekday
            delta = (habit.weekday - start.weekday() + 7) % 7
            current = start + timedelta(days=delta)
        else:
            current = start
        # create 4 consecutive periods
        for _ in range(4):
            inst = HabitInstance(habit=habit, period_start=current)
            # randomly mark some completed
            if _ % 2 == 0:
                inst.mark_completed()
            session.add(inst)
            # advance to next period
            current = habit.next_period_start(current)
    session.commit()

print("Database seeded with sample habits and instances.")