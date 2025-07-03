# db_schema.py
from sqlalchemy import (
    create_engine, MetaData, Table,
    Column, String, DateTime, Date, ForeignKey, select
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base, selectinload, selectin_polymorphic
import sqlalchemy.orm.query as query
from datetime import datetime
from typing import Optional, Sequence
import datetime

from models import Habit, DailyHabit, WeeklyHabit, HabitInstance, Base




engine   = create_engine("sqlite:///./habits.db", echo=False)

Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)


def save_habit(engine: Engine, habit: Habit) -> None:
    with Session(engine) as session:
        session.add(habit)
        session.commit()
        session.refresh(habit)
        return habit.id
        

def save_instance(engine: Engine, instance: HabitInstance) -> None:
    with Session(engine) as session:
            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance.id
        
def complete_task(name: str, date : Optional[datetime.date] = None) -> None:
    """
    Mark a habit instance as completed by updating the completed_at field.
    """
    
    if date is None:
        date = datetime.date.today()
    
    with SessionLocal() as session:     
        
        habit_id = select(Habit.id).where(Habit.name==name)
        habit_id = session.execute(habit_id).scalar_one_or_none()
        if not habit_id:
            raise ValueError(f"No habit named {name!r}")
        instance_id = select(HabitInstance.id).where(HabitInstance.habit_id==habit_id).where(HabitInstance.period_start==date)
        instance_id = session.execute(instance_id).scalar_one_or_none()
        if not instance_id:
            raise ValueError(f"No instance for '{name}' on {date}")
        
        instance = session.get(HabitInstance, instance_id)
        if not instance:
            raise ValueError(f"No HabitInstance with id={instance_id!r}")
        elif instance.is_completed():
            raise ValueError(f"HabitInstance with id={instance_id!r} is already completed")
        else:
            instance.mark_completed()                   # sets completed_at = now()
            session.commit()
            session.refresh(instance)
            
            new_instance = HabitInstance(
            habit=instance.habit,
            period_start=instance.habit.next_period_start(instance.period_start)  # get next period start
            )
            save_instance(engine, new_instance) 
        
def get_all_habits(period: Optional[str] = "all") -> list[Habit]:
    """
    :param period:
      - "daily"  → only daily
      - "weekly" → only weekly
      - anything else (including None) → all
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
    stmt = select(HabitInstance).options(selectinload(HabitInstance.habit), selectin_polymorphic(Habit, [WeeklyHabit]))
    
    with SessionLocal() as session:
        return session.scalars(stmt).all()
    