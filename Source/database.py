# db_schema.py
from sqlalchemy import create_engine, select, delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    Session, sessionmaker, selectinload, selectin_polymorphic
)
from typing import Optional
import datetime
from operator import itemgetter
from functools import reduce
from datetime import date
import os
from pathlib import Path

from models import Habit, DailyHabit, WeeklyHabit, HabitInstance, Base


# Find this file’s directory
BASE_DIR = Path(__file__).resolve().parent

# Build the DB path relative to it
DB_PATH = BASE_DIR / "habits.db"

# Create the engine using that absolute path
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
)
print("🔍 Using SQLite file:", engine.url)

Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)


def save_habit(habit: Habit) -> None:
    """
    Saves a Habit to the database.
    Returns the ID of the saved habit.
    """
    with SessionLocal() as session:
        exists = session.execute(
            select(Habit.id).where(Habit.name == habit.name)
        ).scalar_one_or_none()
        if exists:
            raise ValueError(f"A habit named {habit.name!r} already exists.")

        session.add(habit)
        session.commit()
        session.refresh(habit)
        return habit.id
        

def save_instance(instance: HabitInstance) -> None:
    """
    Saves a HabitInstance to the database.
    Returns the ID of the saved instance.
    """
    with SessionLocal() as session:
        # 1) Look for an existing instance in the *habit_instances* table
        stmt = (
            select(HabitInstance.id)
            .where(
                HabitInstance.habit_id     == str(instance.habit_id),
                HabitInstance.period_start == instance.period_start
            )
        )
        existing_id = session.execute(stmt).scalar_one_or_none()
        if existing_id is not None:
            return existing_id

        # 2) Otherwise insert
        session.add(instance)
        session.commit()
        session.refresh(instance)
        return instance.id
        
def complete_task(name: str, date : Optional[datetime.date] = None) -> None:
    """
    Mark a habit instance as completed and create the following instance.
    """
    
    if date is None:
        date = datetime.date.today()
    
    with SessionLocal() as session:     
        # get habit id by name
        stmt = select(Habit.id).where(Habit.name==name)
        habit_id = session.execute(stmt).scalar_one_or_none()       
        if not habit_id:
            raise ValueError(f"No habit named {name!r}")
        
        # get instance id by habit_id and date
        stmt = select(HabitInstance.id).where(HabitInstance.habit_id==habit_id).where(HabitInstance.period_start==date)
        instance_id = session.execute(stmt).scalar_one_or_none()
        if not instance_id:
            raise ValueError(f"No instance for '{name}' on {date}")
        
        # get the HabitInstance by id
        instance = session.get(HabitInstance, instance_id)
        
        if not instance:
            raise ValueError(f"No HabitInstance with id={instance_id!r}")
        elif instance.is_completed():
            raise ValueError(f"HabitInstance with id={instance_id!r} is already completed")
        else:
            # sets completed_at = now()
            instance.mark_completed()                   
            session.commit()
            session.refresh(instance)
            
            instance_id = select(HabitInstance.id).where(HabitInstance.habit_id==habit_id).where(HabitInstance.period_start==date)
            
            period_start = instance.habit.next_period_start(instance.period_start)
            habit = instance.habit
            
            
            # Compute the next period (may be a datetime.datetime)
            raw_next = instance.habit.next_period_start(instance.period_start)

            # Normalize to a pure date for the SQL comparison:
            if isinstance(raw_next, datetime.datetime):
                lookup_date = raw_next.date()
            else:
                lookup_date = raw_next
            
            stmt = select(HabitInstance.id).where(HabitInstance.habit_id==habit_id).where(HabitInstance.period_start==lookup_date)
            instance_id = session.execute(stmt).scalar_one_or_none()
            
            print(instance_id)

            if instance_id is None:
                print(instance_id)
                # create the following habit instance
                new_instance = HabitInstance(
                habit=habit,
                period_start=period_start  # get next period start
                )
                save_instance(new_instance) 
                print("Created new instance for folling day")
        
def get_all_habits(period: Optional[str] = "all") -> list[Habit]:
    """
    Get all habits [optionally filtered by type].

    :param period:
      - "daily"  → only daily
      - "weekly" → only weekly
      - anything else (including None) → all (Default)
    """
    # Normalize to a real string
    period_str = (period or "all").lower()

    if period_str == "daily":
        stmt = select(Habit).where(Habit.type == "daily")
    elif period_str == "weekly":
        stmt = select(Habit).where(Habit.type == "weekly")
    else:
        stmt = select(Habit)

    stmt = stmt.order_by(Habit.name)

    with SessionLocal() as session:
        return session.scalars(stmt).all()
        
def get_all_active_habits(name : str = None) -> list[Habit]:
    """
    Get all active habits [optionally by name].
    """
    # Build a query to fetch all HabitInstance rows, eagerly loading each instance’s related Habit 
    # plus any subclass‐specific columns for WeeklyHabit in a single round‐trip.
    if name is None:
        print("No name provided, fetching all active habits")
        stmt = select(HabitInstance).options(selectinload(HabitInstance.habit), selectin_polymorphic(Habit, [WeeklyHabit]))
    else:
        print(f"Fetching all active habits with name={name!r}")
        stmt = select(HabitInstance).options(selectinload(HabitInstance.habit), selectin_polymorphic(Habit, [WeeklyHabit])).where(
            HabitInstance.habit_id == get_habit_by_name(name).id
        )
    
    
    with SessionLocal() as session:
        return session.scalars(stmt).all()
    



def prev_period_start(habit, date: date) -> date:
    """
    Return the start of the period immediately before date.
    """
    if isinstance(habit, DailyHabit):
        return date - datetime.timedelta(days=1)
    # weekly: go back exactly 7 days
    return date - datetime.timedelta(days=7)


def current_streak_for_habit(habit: DailyHabit|WeeklyHabit) -> int:
    """
    Return the current streak for a habit.
    """
    with SessionLocal() as session:
        # Get all instances for this habit, ordered by period_start
        today = date.today()
        stmt = (
            select(HabitInstance)
            .where(
                HabitInstance.habit_id == habit.id,
                HabitInstance.period_start <= today
            )
            .order_by(HabitInstance.period_start)
        )
        instances = session.scalars(stmt).all()

        if not instances:
            return 0  # No instances, no streak

        # Get the most recent instance
        last_instance = instances[-1]

        # If the last instance is not completed, return 0
        if not last_instance.is_completed():
            return last_instance.period_start

        # Count how many consecutive completed instances there are from the end
        streak = 0
        expected = instances[-1].period_start if instances else None

        for inst in reversed(instances):
            # stop if unmet expectation or not done
            if inst.period_start != expected or not inst.is_completed():
                break

            # count it, then shift the expectation back one more period
            streak   += 1
            expected  = prev_period_start(habit, expected)

        return streak


def get_habit_by_name(name: str) -> Optional[Habit]:
    """
    Get a habit by its name.
    """
    with SessionLocal() as session:
        stmt = select(Habit).where(Habit.name == name)
        return session.execute(stmt).scalar_one_or_none()
    
def backfill_instances():
    """
    Ensure every habit has a continuous sequence of HabitInstance records
    from its first period up through today.

    For each habit in the database:
      1. Load the most recent HabitInstance (if any).
      2. If no instances exist yet, create the very first one starting at
         the habit's `first_period_start` for today.
      3. Repeatedly generate and persist new instances by calling
         `habit.next_period_start(last.period_start)` until the latest
         instance covers today's period.

    This guarantees there are no gaps in the timeline of instances for any habit,
    which is useful for accurate streak computations and reporting.
    """
    today = date.today()
    with SessionLocal() as session:
        for habit in session.query(Habit).all():
            # find the most‐recent instance (if any)
            last = (
                session.query(HabitInstance)
                        .filter_by(habit_id=habit.id)
                        .order_by(HabitInstance.period_start.desc())
                        .first()
            )
            # if there’s no instance, start one today (or via habit.first_period_start)
            if last is None:
                inst = HabitInstance(habit, habit.first_period_start(date.today()))
                session.add(inst)
                session.commit()
                last = inst

            # now, while last is “behind” today, spawn the next one
            while last.period_start < today:
                nxt = habit.next_period_start(last.period_start)
                inst = HabitInstance(habit, nxt)
                session.add(inst)
                session.commit()
                last = inst
                
def longest_streak_all(habits: list[Habit], all_instances: list[HabitInstance]) -> dict[str,int]:
    """
    Compute the longest streak of each habit, then return the overall best.
    Returns a dict mapping habit.name → its longest streak.
    """
    
    def streak_for(habit):
        raw = current_streak_for_habit(habit)  # date or int

        if isinstance(raw, date):
            delta_days = (date.today() - raw).days
            # convert to periods
            if isinstance(habit, WeeklyHabit):
                # full weeks since that date
                value = delta_days // 7
            else:  # DailyHabit
                value = delta_days
        else:
            # raw is already the active‐streak length in periods
            value = raw

        return (habit.name, value)

    streaks     = dict(map(streak_for, habits))
    overall_max = max(streaks.values(), default=0)
    return {"per_habit": streaks, "max_of_all": overall_max}

def delete_habit_by_id(habit_id: str) -> None:
    """
    Delete the Habit with the given id (and cascade‐delete its instances).
    """
    with SessionLocal() as session:
        session.execute(
            delete(Habit)
            .where(Habit.id == habit_id)
        )
        session.execute(
            delete(HabitInstance)
            .where(HabitInstance.habit_id == habit_id)
        )
        session.commit()
