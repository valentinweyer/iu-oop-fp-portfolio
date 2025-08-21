# db_schema.py
from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import (
    sessionmaker, selectinload, selectin_polymorphic
)
from typing import Optional
import datetime

from datetime import date
from pathlib import Path

from models import Habit, DailyHabit, WeeklyHabit, HabitInstance, Base


# Find this file’s directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Build the DB path relative to it
DB_PATH = BASE_DIR / "db/habits.db"

if not DB_PATH.parent.exists():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Create the engine using that absolute path
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
)

Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)


def save_habit(habit: Habit) -> str:
    """
    Saves a Habit to the database.

    Args:
        habit (Habit): The habit object to save.

    Raises:
        ValueError: If a habit with the same name already exists.

    Returns:
        str: The ID of the saved habit.
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
        

def save_instance(instance: HabitInstance) -> str:
    """
    Saves a HabitInstance to the database.

    Args:
        instance (HabitInstance): The habit instance object to save.

    Returns:
        str: The ID of the saved instance.
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
    Marks a habit instance as completed and creates the next one.

    Args:
        name (str): The name of the habit to mark as complete.
        date (Optional[datetime.date], optional): The date of the instance to mark as complete. Defaults to today.

    Raises:
        ValueError: If the habit or instance is not found, or if the instance is already completed.
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

            if instance_id is None:
                # create the following habit instance
                new_instance = HabitInstance(
                habit=habit,
                period_start=period_start  # get next period start
                )
                save_instance(new_instance) 
        
def get_all_habits(period: Optional[str] = "all") -> list[Habit]:
    """
    Retrieves all habits, optionally filtered by period.

    Args:
        period (Optional[str], optional): The period to filter by ('daily' or 'weekly'). 
                                          Defaults to "all".

    Returns:
        list[Habit]: A list of all habits matching the filter.
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
        
def get_all_active_habits(name : str = None) -> list[HabitInstance]:
    """
    Retrieves all active habit instances, optionally filtered by name.

    Args:
        name (str, optional): The name of the habit to filter by. Defaults to None.

    Returns:
        list[HabitInstance]: A list of all active habit instances.
    """
    # Build a query to fetch all HabitInstance rows, eagerly loading each instance’s related Habit
    # plus any subclass‐specific columns for WeeklyHabit in a single round‐trip.
    if name is None:
        stmt = select(HabitInstance).options(selectinload(HabitInstance.habit), selectin_polymorphic(Habit, [WeeklyHabit]))
    else:
        stmt = select(HabitInstance).options(selectinload(HabitInstance.habit), selectin_polymorphic(Habit, [WeeklyHabit])).where(
            HabitInstance.habit_id == get_habit_by_name(name).id
        )
    
    
    with SessionLocal() as session:
        return session.scalars(stmt).all()
    



def prev_period_start(habit: Habit, date: date) -> date:
    """
    Calculates the start of the previous period for a given habit and date.

    Args:
        habit (Habit): The habit to calculate the previous period for.
        date (date): The date to calculate the previous period from.

    Returns:
        date: The start date of the previous period.
    """
    if isinstance(habit, DailyHabit):
        return date - datetime.timedelta(days=1)
    # weekly: go back exactly 7 days
    return date - datetime.timedelta(days=7)


def current_streak_for_habit(habit: Habit, today: Optional[date] = None) -> int:
    """
    Calculates the current streak for a given habit.

    Args:
        habit (Habit): The habit to calculate the streak for.
        today (Optional[date], optional): The date to calculate the streak up to. Defaults to today.

    Returns:
        int: The current streak count.
    """
    if today is None:
        today = date.today()

    with SessionLocal() as session:
        # Get all instances for this habit up to today, in reverse order
        stmt = (
            select(HabitInstance)
            .where(HabitInstance.habit_id == habit.id, HabitInstance.period_start <= today)
            .order_by(HabitInstance.period_start.desc())
        )
        instances = session.scalars(stmt).all()

        if not instances:
            return 0

        streak = 0
        
        # If the most recent instance is today and not completed, check streak from yesterday.
        if instances[0].period_start == today and not instances[0].is_completed():
            instances_to_check = instances[1:]
        else:
            instances_to_check = instances
        
        if not instances_to_check:
            return 0
            
        # The first instance in our list to check is where the streak must begin.
        expected_date = instances_to_check[0].period_start
        
        for instance in instances_to_check:
            if instance.is_completed() and instance.period_start == expected_date:
                streak += 1
                expected_date = prev_period_start(habit, expected_date)
            else:
                # The streak is broken.
                break
                
        return streak


def get_habit_by_name(name: str) -> Optional[Habit]:
    """
    Retrieves a habit by its name.

    Args:
        name (str): The name of the habit to retrieve.

    Returns:
        Optional[Habit]: The habit object if found, otherwise None.
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
                
def longest_streak_all(habits: list[Habit], all_instances: list[HabitInstance]) -> dict:
    """
    Computes the longest streak for each habit and finds the overall maximum.

    Args:
        habits (list[Habit]): A list of all habits.
        all_instances (list[HabitInstance]): A list of all habit instances.

    Returns:
        dict: A dictionary containing the streaks per habit and the maximum overall streak.
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
    Deletes a habit and its instances from the database.

    Args:
        habit_id (str): The ID of the habit to delete.
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
