from datetime import datetime, date, timedelta
from uuid import uuid4
from typing import Optional
from sqlalchemy import (
    Column, String, DateTime, Date, ForeignKey, Integer, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Habit(Base):
    """
    Base class representing a habit.
    """
    
    __tablename__ = 'habits'
    
    id              = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name            = Column(String, nullable=False)
    description     = Column(String, nullable=True)
    date_created    = Column(DateTime, default=datetime.utcnow)
    type            = Column(String, nullable=False)   # discriminator
    weekday         = Column(Integer, nullable=True)

    
    __mapper_args__ = {
        'polymorphic_identity': 'habit',
        'polymorphic_on': type 
    }
    
    instances = relationship("HabitInstance", back_populates="habit")
    
    
    def __init__(self, name: str, description: Optional[str]):
        self.id = str(uuid4())
        self.name = name
        self.description = description
        self.date_created = datetime.now()  
        
    def next_period_start(self, after: date) -> date:
        """
        Calculate the start of the next period for the habit after a given date.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("This method should be implemented by subclasses")
    
    def get_data(self) -> dict:
        """
        Get the data representation of the habit.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("This method should be implemented by subclasses")
    
class DailyHabit(Habit):
    """
    Subclass representing a daily habit.
    """
    __mapper_args__ = {
        'polymorphic_identity': 'daily',
    }
    
    def __init__(self, name: str, description: Optional[str]):
        super().__init__(name, description)
        
    def next_period_start(self, after: date) -> date:
        """
        Calculate the start of the next period for the habit after a given date. 
        For this habit type, it is always the next day.
        """
        next_day = after + timedelta(days=1)
        return datetime.combine(next_day, datetime.min.time())
    
    def get_data(self) -> dict:
        """
        Get the data representation of the daily habit as a dict.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "date_created": self.date_created.isoformat()
        }
   
    
class WeeklyHabit(Habit):
    __mapper_args__ = {
        'polymorphic_identity': 'weekly',
    }
    
    def __init__(self, name: str, description: Optional[str], weekday: Optional[int] = None):
        super().__init__(name, description)
        self.weekday = weekday
        
        
    def first_period_start(self, after: date) -> date:
        """
        Calculate the start of the first period for the habit after a given date.
        """
        current = after.weekday()   
        weekday = 0 if self.weekday is None else self.weekday                       # preventing NoneType error
        days_ahead = (weekday - current + 7) % 7 if weekday is not current else 0   # calculate the days to advance | zero if weekday is today
        return after + timedelta(days=days_ahead)
    
    def next_period_start(self, after: date) -> date:
        """
        Calculate the start of the next period for the habit after a given date.
        """
        current = after.weekday() 
        weekday = 0 if self.weekday is None else self.weekday                       # preventing NoneType error   
        # advance to next `weekday` (e.g. 2 for Wednesday), at least 1 day ahead
        days_ahead = (weekday - current + 7) % 7 if weekday is not current else 7   # calculate the days to advance | 7 if weekday is today to have habit next week
        return after + timedelta(days=days_ahead)

    def get_data(self) -> dict:
        """
        Get the data representation of the daily habit as a dict.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "date_created": self.date_created.isoformat()
        }
    
class HabitInstance(Base):
    """
    Represents an instance of a habit on a specific date.
    """
    
    __tablename__ = "habit_instances"
    __table_args__ = (
      UniqueConstraint("habit_id", "period_start", name="uix_habit_period"),
    )

    id           = Column(String, primary_key=True, default=lambda: str(uuid4()))
    habit_id     = Column(String, ForeignKey("habits.id"), nullable=False)
    period_start = Column(Date, nullable=False)
    due_date     = Column(Date, nullable=True)  # Optional due date for the habit
    completed_at = Column(DateTime, nullable=True)
    
    habit = relationship("Habit", back_populates="instances")
 
    
    def __init__(self, habit: Habit, period_start: date):
        self.id = str(uuid4())
        self.habit_id = str(habit.id)
        self.period_start = period_start
        self.due_date = period_start if habit.type == 'daily' or (habit.type=="weekly" and habit.weekday is not None) else period_start + timedelta(days=6 - period_start.weekday()) if habit.type == 'weekly' else None
        self.completed_at: Optional[datetime] = None
        
    def is_completed(self) -> bool:
        """
        Check if the habit instance is completed.
        """
        return self.completed_at is not None
        
    def mark_completed(self):
        """
        Mark the habit instance as completed.
        """
        self.completed_at = datetime.now()
        
        
    def get_data(self) -> dict:
        """
        Get the data representation of the habit instance as a dict.
        """
        return {
            "id": str(self.id),
            "habit_id": str(self.habit_id),
            "period_start": self.period_start.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }        
    
 




