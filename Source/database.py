# db_schema.py
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    Session, sessionmaker, selectinload, selectin_polymorphic
)
from datetime import datetime
from typing import Optional, Sequence
import datetime
from operator import itemgetter
from functools import reduce
from datetime import date

from models import Habit, DailyHabit, WeeklyHabit, HabitInstance, Base


engine   = create_engine("sqlite:///./habits.db", echo=False)

Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)


def save_habit(engine: Engine, habit: Habit) -> None:
    """
    Saves a Habit to the database.
    Returns the ID of the saved habit.
    """
    with Session(engine) as session:
        session.add(habit)
        session.commit()
        session.refresh(habit)
        return habit.id
        

def save_instance(engine: Engine, instance: HabitInstance) -> None:
    """
    Saves a HabitInstance to the database.
    Returns the ID of the saved instance.
    """
    with Session(engine) as session:
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
        habit_id = select(Habit.id).where(Habit.name==name)
        habit_id = session.execute(habit_id).scalar_one_or_none()       
        if not habit_id:
            raise ValueError(f"No habit named {name!r}")
        
        # get instance id by habit_id and date
        instance_id = select(HabitInstance.id).where(HabitInstance.habit_id==habit_id).where(HabitInstance.period_start==date)
        instance_id = session.execute(instance_id).scalar_one_or_none()
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
            
            # create the following habit instance
            new_instance = HabitInstance(
            habit=instance.habit,
            period_start=instance.habit.next_period_start(instance.period_start)  # get next period start
            )
            save_instance(engine, new_instance) 
        
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
        
def get_all_active_habits(Name = Optional[str]) -> list[Habit]:
    """
    Get all active habits [optionally by name].
    """
    # Build a query to fetch all HabitInstance rows, eagerly loading each instance’s related Habit 
    # plus any subclass‐specific columns for WeeklyHabit in a single round‐trip.
    stmt = select(HabitInstance).options(selectinload(HabitInstance.habit), selectin_polymorphic(Habit, [WeeklyHabit]))
    
    with SessionLocal() as session:
        return session.scalars(stmt).all()
    
    
def longest_streak_for_habit(instances: list[HabitInstance], habit: WeeklyHabit|DailyHabit) -> int:
    """
    Given a sorted list of all HabitInstance for one habit,
    return its maximum consecutive‐period streak.
    """
    # 1) Filter only completed instances
    completed = list(filter(lambda inst: inst.is_completed(), instances))

    # 2) Map each to its period_start date
    dates = list(map(itemgetter("period_start"), map(lambda i: {"period_start": i.period_start}, completed)))

    # 3) Reduce over runs: compare each to the previous-next via habit.next_period_start()
    def reducer(acc, current):
        max_streak, last_date, cur_streak = acc
        if last_date and current == habit.next_period_start(last_date):
            cur_streak += 1
        else:
            cur_streak = 1
        return (max(max_streak, cur_streak), current, cur_streak)

    # Start with (max_streak=0, last_date=None, cur_streak=0)
    max_streak, _, _ = reduce(reducer, dates, (0, None, 0))
    return max_streak


def get_habit_by_name(name: str) -> Optional[Habit]:
    """
    Get a habit by its name.
    """
    with SessionLocal() as session:
        stmt = select(Habit).where(Habit.name == name)
        return session.execute(stmt).scalar_one_or_none()
    
def backfill_instances():
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
        insts = sorted(
            filter(lambda i: i.habit_id == habit.id, all_instances),
            key=lambda i: i.period_start
        )
        return (habit.name, longest_streak_for_habit(insts, habit))

    # Map each habit to its streak, then pick the max
    streaks = dict(map(streak_for, habits))
    overall_max = max(streaks.values(), default=0)
    return {"per_habit": streaks, "max_of_all": overall_max}