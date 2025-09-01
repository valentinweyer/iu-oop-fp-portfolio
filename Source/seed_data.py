
from datetime import date, timedelta
import random
from rich.console import Console
from database import engine, SessionLocal, Base, backfill_instances
from models import DailyHabit, WeeklyHabit, HabitInstance, Habit

console = Console()

def seed_data():
    # Recreate database schema
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

    with SessionLocal() as session:
        for habit in sample_habits:
            session.add(habit)
        session.commit()

        # 1. Create the very first instance for each habit, 4 weeks ago
        for habit in session.query(Habit).all():
            # Calculate the start date for 4 weeks ago
            if isinstance(habit, WeeklyHabit):
                today = date.today()
                days_since_period_start = (today.weekday() - habit.weekday + 7) % 7
                current_period_start = today - timedelta(days=days_since_period_start)
                start_date = current_period_start - timedelta(weeks=3)
            else:  # DailyHabit
                start_date = date.today() - timedelta(days=27)
            
            # Create the initial instance
            initial_instance = HabitInstance(habit=habit, period_start=start_date)
            session.add(initial_instance)
        session.commit()

    # 2. Backfill all missing instances up to today
    backfill_instances()

    with SessionLocal() as session:
        # 3. Randomly complete instances older than the last 4 periods
        for habit in session.query(Habit).all():
            # Determine the start of the 4-period pattern
            if isinstance(habit, WeeklyHabit):
                today = date.today()
                days_since_period_start = (today.weekday() - habit.weekday + 7) % 7
                current_period_start = today - timedelta(days=days_since_period_start)
                pattern_start_date = current_period_start - timedelta(weeks=3)
            else:  # DailyHabit
                pattern_start_date = date.today() - timedelta(days=3)

            # Get all instances before the pattern starts
            instances_to_randomize = session.query(HabitInstance).filter(
                HabitInstance.habit_id == habit.id,
                HabitInstance.period_start < pattern_start_date
            ).all()

            for inst in instances_to_randomize:
                if random.choice([True, False]):
                    inst.mark_completed()

        session.commit()

        # 4. Apply the specific streak patterns for the last 4 periods
        for habit in session.query(Habit).all():
            # Determine the start date for the pattern
            if isinstance(habit, WeeklyHabit):
                today = date.today()
                days_since_period_start = (today.weekday() - habit.weekday + 7) % 7
                current_period_start = today - timedelta(days=days_since_period_start)
                current = current_period_start - timedelta(weeks=3)
            else:  # DailyHabit
                current = date.today() - timedelta(days=3)

            # Define the pattern for the last 4 periods
            pattern = []
            if habit.name == "Brush Teeth":
                pattern = [True, True, True, False]
            elif habit.name == "Meditate":
                pattern = [True, True, False, False]
            elif habit.name == "Water Plants":
                pattern = [True, True, True, False]
            else:  # Grocery Shopping, Review Goals
                pattern = [True, False, True, False]

            # Apply the pattern
            for completed_flag in pattern:
                inst = session.query(HabitInstance).filter_by(habit_id=habit.id, period_start=current).one()
                if completed_flag:
                    inst.mark_completed()
                current = habit.next_period_start(current)

        session.commit()

    console.print("[bold green]Database seeded with 4 weeks of history and specific streak patterns.[/bold green]")
