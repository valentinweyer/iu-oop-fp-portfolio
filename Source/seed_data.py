
from datetime import date, timedelta
from rich.console import Console
from database import engine, SessionLocal, Base
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

    # Seed habits and create historical instances
    with SessionLocal() as session:
        # add habits
        for habit in sample_habits:
            session.add(habit)
        session.commit()

        # create instances with specific streak patterns
        for habit in session.query(Habit).all():
            # Calculate start date to create a pattern leading up to the current date
            if isinstance(habit, WeeklyHabit):
                today = date.today()
                # Find the start of the current week's period
                days_since_period_start = (today.weekday() - habit.weekday + 7) % 7
                current_period_start = today - timedelta(days=days_since_period_start)
                # Start 3 periods (weeks) before the current one
                start = current_period_start - timedelta(weeks=3)
            else:  # DailyHabit
                # Start 3 days ago to create a 4-day history including today
                start = date.today() - timedelta(days=3)

            current = start

            # Build custom completion patterns:
            # The last element corresponds to the current period, which should be open.
            pattern = []
            if habit.name == "Brush Teeth":
                # Active streak of 3, task for today is open
                pattern = [True, True, True, False]
            elif habit.name == "Meditate":
                # Broken streak
                pattern = [True, True, False, False]
            elif habit.name == "Water Plants":
                # Active streak of 3 weeks, task for this week is open
                pattern = [True, True, True, False]
            else:  # Grocery Shopping, Review Goals
                pattern = [True, False, True, False]


            # create four consecutive periods
            for completed_flag in pattern:
                # Check if an instance for this period already exists from the backfill
                inst = session.query(HabitInstance).filter_by(habit_id=habit.id, period_start=current).first()
                if not inst:
                    inst = HabitInstance(habit=habit, period_start=current)
                    session.add(inst)

                if completed_flag:
                    inst.mark_completed(current)

                # advance to next period
                current = habit.next_period_start(current)

        session.commit()

    console.print("[bold green]Database seeded with sample habits, instances, and streak patterns.[/bold green]")
