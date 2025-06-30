# db_schema.py
from sqlalchemy import (
    create_engine, MetaData, Table,
    Column, String, DateTime, Date, ForeignKey, insert
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import session
import sqlalchemy.orm.query as query
from datetime import datetime
from habit import Habit, HabitInstance  # your pure-Python classes


engine   = create_engine("sqlite:///./habit.db", echo=True)
metadata = MetaData()

habits_table = Table(
    "habits", metadata,
    Column("id",           String, primary_key=True),
    Column("name",         String, nullable=False),
    Column("description",  String),
    Column("date_created", DateTime, default=datetime.now()),
)

instances_table = Table(
    "habit_instances", metadata,
    Column("id",           String, primary_key=True),
    Column("habit_id",     String, ForeignKey("habits.id"), nullable=False),
    Column("period_start", Date, nullable=False),
    Column("completed_at", DateTime),
)

metadata.create_all(engine)

def save_habit(engine: Engine, habit: Habit) -> None:
    stmt = insert(habits_table).values(
        id           = str(habit.id),
        name         = habit.name,
        description  = habit.description,
        date_created = habit.date_created,
    )
    with engine.begin() as connection:
        connection.execute(stmt)

def save_instance(engine: Engine, instance: HabitInstance) -> None:
    stmt = insert(instances_table).values(
        id           = str(instance.id),
        habit_id     = str(instance.habit_id),
        period_start = instance.period_start,
        completed_at = instance.completed_at,
    )
    with engine.begin() as connection:
        connection.execute(stmt)
        
def complete_task(engine: Engine, instance_id: str) -> None:
    """
    Mark a habit instance as completed by updating the completed_at field.
    """
    pass
    