from cli import cli

from cli import complete_task
from datetime import date
from database import current_streak_for_habit

if __name__ == "__main__":
    #cli(args=["show-longest-streak-for-habit", "Meditate"])
    cli()
    