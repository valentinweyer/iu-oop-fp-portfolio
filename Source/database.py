# db_schema.py
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    Session, sessionmaker, selectinload, selectin_polymorphic
)
from datetime import datetime
from typing import Optional, Sequence
import datetime

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
    