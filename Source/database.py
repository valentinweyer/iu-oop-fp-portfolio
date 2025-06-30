# db_schema.py
from sqlalchemy import (
    create_engine, MetaData, Table,
    Column, String, DateTime, Date, ForeignKey
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base
import sqlalchemy.orm.query as query
from datetime import datetime

from models import Habit, HabitInstance, Base



engine   = create_engine("sqlite:///./habits.db", echo=True)

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
        
def complete_task(engine: Engine, instance_id: str) -> None:
    """
    Mark a habit instance as completed by updating the completed_at field.
    """
    with Session(engine) as session:
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
        
        

    