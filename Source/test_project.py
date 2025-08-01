import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, DailyHabit, WeeklyHabit, HabitInstance, Habit
import database
import datetime
import os

# Use an in-memory SQLite database for testing
TEST_DB_PATH = "test_habits.db"

@pytest.fixture(scope="session")
def engine():
    return create_engine(f"sqlite:///{TEST_DB_PATH}")

@pytest.fixture(scope="session")
def tables(engine):
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

@pytest.fixture
def db_session(engine, tables, monkeypatch):
    """
    Returns an sqlalchemy session, and after the test tears down everything properly.
    It also patches the database.SessionLocal to use the test database.
    """
    # Patch the database module's engine and SessionLocal
    monkeypatch.setattr(database, "engine", engine)
    
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(database, "SessionLocal", TestSessionLocal)

    connection = engine.connect()
    transaction = connection.begin()
    
    session = TestSessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


def test_create_daily_habit(db_session):
    habit = DailyHabit(name="Read a book", description="Read 20 pages of a book every day")
    database.save_habit(habit)
    
    retrieved_habit = database.get_habit_by_name("Read a book")
    assert retrieved_habit is not None
    assert retrieved_habit.name == "Read a book"
    assert retrieved_habit.description == "Read 20 pages of a book every day"
    assert isinstance(retrieved_habit, DailyHabit)

def test_create_weekly_habit(db_session):
    habit = WeeklyHabit(name="Go to the gym", description="Go to the gym every Monday", weekday=0)
    database.save_habit(habit)
    
    retrieved_habit = database.get_habit_by_name("Go to the gym")
    assert retrieved_habit is not None
    assert retrieved_habit.name == "Go to the gym"
    assert retrieved_habit.description == "Go to the gym every Monday"
    assert isinstance(retrieved_habit, WeeklyHabit)
    assert retrieved_habit.weekday == 0

def test_prevent_duplicate_habit(db_session):
    habit = DailyHabit(name="Duplicate Habit", description="A habit to test duplication.")
    database.save_habit(habit)
    
    with pytest.raises(ValueError, match="A habit named 'Duplicate Habit' already exists."):
        duplicate_habit = DailyHabit(name="Duplicate Habit", description="Another one")
        database.save_habit(duplicate_habit)

def test_complete_task(db_session):
    habit = DailyHabit(name="Drink water", description="Drink 8 glasses of water every day")
    database.save_habit(habit)
    
    # Create a habit instance for today
    instance = HabitInstance(habit=habit, period_start=datetime.date.today())
    database.save_instance(instance)

    database.complete_task("Drink water", datetime.date.today())
    
    # Re-fetch the instance to check its state
    completed_instance = db_session.query(HabitInstance).filter(HabitInstance.habit_id == habit.id, HabitInstance.period_start == datetime.date.today()).one()
    assert completed_instance.is_completed()

def test_get_all_habits(db_session):
    # Clear existing habits to ensure a clean slate
    db_session.query(Habit).delete()
    db_session.commit()
    
    habit1 = DailyHabit(name="Habit 1", description="Daily habit 1")
    habit2 = WeeklyHabit(name="Habit 2", description="Weekly habit 2", weekday=1)
    database.save_habit(habit1)
    database.save_habit(habit2)
    
    habits = database.get_all_habits()
    assert len(habits) == 2

def test_get_daily_habits(db_session):
    db_session.query(Habit).delete()
    db_session.commit()
    
    habit1 = DailyHabit(name="Habit 3", description="Daily habit 3")
    habit2 = WeeklyHabit(name="Habit 4", description="Weekly habit 4", weekday=2)
    database.save_habit(habit1)
    database.save_habit(habit2)
    
    habits = database.get_all_habits("daily")
    assert len(habits) == 1
    assert habits[0].name == "Habit 3"

def test_get_weekly_habits(db_session):
    db_session.query(Habit).delete()
    db_session.commit()

    habit1 = DailyHabit(name="Habit 5", description="Daily habit 5")
    habit2 = WeeklyHabit(name="Habit 6", description="Weekly habit 6", weekday=3)
    database.save_habit(habit1)
    database.save_habit(habit2)
    
    habits = database.get_all_habits("weekly")
    assert len(habits) == 1
    assert habits[0].name == "Habit 6"

def test_delete_habit(db_session):
    db_session.query(Habit).delete()
    db_session.query(HabitInstance).delete()
    db_session.commit()

    habit = DailyHabit(name="To Be Deleted", description="This habit will be deleted.")
    database.save_habit(habit)
    habit_id = habit.id
    
    instance = HabitInstance(habit=habit, period_start=datetime.date.today())
    database.save_instance(instance)
    
    database.delete_habit_by_id(habit_id)
    
    assert database.get_habit_by_name("To Be Deleted") is None
    
    instances = db_session.query(HabitInstance).filter(HabitInstance.habit_id == habit_id).all()
    assert len(instances) == 0

def test_current_streak(db_session):
    db_session.query(Habit).delete()
    db_session.query(HabitInstance).delete()
    db_session.commit()

    habit = DailyHabit(name="Streak Test", description="Test current streak.")
    database.save_habit(habit)
    
    # Create a streak of 3
    today = datetime.date.today()
    for i in range(3):
        instance_date = today - datetime.timedelta(days=i)
        instance = HabitInstance(habit=habit, period_start=instance_date)
        database.save_instance(instance)
        database.complete_task(habit.name, instance_date)
        
    # Add an uncompleted task, which should not break the streak calculation for completed tasks
    uncompleted_instance = HabitInstance(habit=habit, period_start=today - datetime.timedelta(days=3))
    database.save_instance(uncompleted_instance)

    streak = database.current_streak_for_habit(habit)
    assert streak == 3

