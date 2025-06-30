from datetime import datetime, date, timedelta
from uuid import uuid4
from typing import Optional

class Habit():
    """
    Base class representing a habit.
    """
    
    def __init__(self, name: str, description: Optional[str]):
        self.id = uuid4()
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
        """
        raise NotImplementedError("This method should be implemented by subclasses")
    
class DailyHabit(Habit):
    def __init__(self, name: str, description: Optional[str]):
        super().__init__(name, description)
        
    def next_period_start(self, after: date) -> date:
        """
        Calculate the start of the next period for the habit after a given date.
        """
        next_day = after + timedelta(days=1)
        return datetime.combine(next_day, datetime.min.time())
    
    def get_data(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "date_created": self.date_created.isoformat()
        }
   
    
class WeeklyHabit(Habit):
    def __init__(self, name: str, description: Optional[str]):
        super().__init__(name, description)
    
    def next_period_start(self, after: date) -> date:
        """
        Calculate the start of the next period for the habit after a given date.
        """
        next_day = after + timedelta(days=7)
        return datetime.combine(next_day, datetime.min.time())

    def get_data(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "date_created": self.date_created.isoformat()
        }
    
class HabitInstance:
    """
    Represents an instance of a habit on a specific date.
    """
    
    def __init__(self, habit: Habit, period_start: date):
        self.id = uuid4()
        self.habit_id = habit.id
        self.period_start = period_start
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
        Get the data representation of the habit instance.
        """
        return {
            "id": str(self.id),
            "habit_id": str(self.habit_id),
            "period_start": self.period_start.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }        
    
 




