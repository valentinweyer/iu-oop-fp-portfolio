import click
from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session


from models import DailyHabit, WeeklyHabit, HabitInstance, Habit
import database


@click.group()
def cli():
    """
    📝 Habit Tracker CLI"""
    pass

def ensure_up_to_date(f):
    @click.pass_context
    def wrapper(ctx, *args, **kwargs):
        database.backfill_instances()
        return ctx.invoke(f, *args, **kwargs)
    return wrapper

@cli.command("add-habit")
@click.argument("name", metavar="NAME")
@click.option(
    "--start-date", "-s",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=date.today().isoformat(),
    show_default=True,
    help="When the first instance should start (YYYY-MM-DD). Default is today."
)
@click.option(
    "--period", "-p",
    "period_type",
    type=click.Choice(["daily", "weekly"], case_sensitive=False),
    default="daily",
    show_default=True,
    help="Habit periodicity"
)
@click.option(
    "--description", "-d",
    default=None,
    help="Optional description of the habit"
)
@click.option(
    "--weekday", "-w",
    default=None,
    help="Optional weekday for weekly habits (0=Monday, 6=Sunday). Only used for weekly habits."
)
def add_habit(name : str, start_date : date, period_type : str, description : str=None, weekday: Optional[int] = None):
    """
    Add a new habit to the database.    
    """
    
    if period_type == 'daily':
        habit = DailyHabit(name=name, description=description)                      # create a daily habit
    elif period_type == 'weekly':
        habit = WeeklyHabit(name=name, description=description, weekday=weekday)    # create a weekly habit with optional weekday
    
    database.save_habit(database.engine, habit)                                     # save the habit to the database
    
    if weekday is not None and period_type == "weekly":
        start_date = habit.first_period_start(after=start_date)                     # calculate the first period start for weekly habits    
        
    habit_instance = HabitInstance(habit=habit, period_start=start_date)            # create a habit instance with the habit and the start date
    database.save_instance(database.engine, habit_instance)                         # save the habit instance to the database
    click.echo(f'Habit "{name}" added successfully!')
    
    
    
@cli.command("list-all-habits")
@click.option(
    "--type", "-t",
    "habit_type",
    type=click.Choice(["all", "daily", "weekly"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Filter habits by type (all, daily, weekly)"
)
@ensure_up_to_date
def list_all_habits(habit_type: str = "all"):
    """
    Retrieve all habits from the database.
    """
    p = None if habit_type == "all" else habit_type.lower()     # Filter by type"      
    habits = database.get_all_habits(period=p)
    if not habits:
        click.echo("No habits found.")
        return
    click.echo("📋 Habits:")
    for h in habits:
        click.echo(f"  • [{h.id}] {h.name} ({h.type}), created {h.date_created.date()}")
       
@cli.command("list-all-active-habits")
@click.option(
    "--name", "-n",
    default=None,
    show_default=True,
    help="Optional name to filter active habits."
)
@ensure_up_to_date
def list_all_active_habits(name : str = None):
    """
    Retrieve all habit instances and print as a table.
    """
    instances = database.get_all_active_habits(name=name)  # Get all active habit instances, optionally filtered by name
    # Sort by the date (earliest first)
    instances.sort(key=lambda inst: inst.period_start)
    
    if not instances:
        click.echo("No active habits found.")
        return

    # Prepare the rows
    rows = []
    for instance in instances:
        done = (
            instance.completed_at.strftime("%Y-%m-%d %H:%M")
            if instance.completed_at else "Not completed"
        )
        rows.append({
            "id":           str(instance.id),
            "name":         instance.habit.name,
            "type":         instance.habit.type,
            "weekday":      # coerce to str or "N/A"
                str(instance.habit.weekday)
                if isinstance(instance.habit, WeeklyHabit) and instance.habit.weekday is not None
                else "N/A",
            "period_start": instance.period_start.strftime("%Y-%m-%d"),
            "due":          instance.due_date.strftime("%Y-%m-%d") if instance.due_date else "No due date",
            "completed":    done
        })

    # Compute column widths
    cols = ["id","name","type", "weekday", "period_start","due","completed"]
    widths = { c: max(len(r[c]) for r in rows + [{c:c.upper()}]) for c in cols }

    # Print header
    header = "  ".join(f"{c.upper():{widths[c]}}" for c in cols)
    click.echo(header)
    click.echo("-" * len(header))

    # Print rows
    for r in rows:
        line = "  ".join(f"{r[c]:{widths[c]}}" for c in cols)
        click.echo(line)

@cli.command("complete-task")
@click.argument("name", metavar="NAME")
@click.option(
    "--date", "-d",
    default=None,
    help="Optional date to complete tasks."
)
@ensure_up_to_date
def complete_task(name: str = None, date : Optional[date] = None):
    """
    Mark a habit instance as completed.
    """
    if not name:
        click.echo("Please provide a habit instance ID to complete.")
        return
    
    try:
        database.complete_task(name, date)
        click.echo(f"Habit instance {name} marked as completed!")
    except ValueError as e:
        click.echo(f"Error: {e}")



    
@cli.command("show-longest-streak-for-habit")
@click.argument("name", metavar="NAME")
def show_longest_streak_for_habit(name: str = None):
    """
    Show the longest streak for a habit.
    """
    if not name:
        click.echo("Please provide a habit name to show the longest streak.")
        return
    
    habit = database.get_habit_by_name(name)
    
    try:
        streak = database.current_streak_for_habit(habit=habit)               # database.longest_streak_for_habit(instances=database.get_all_active_habits(), habit=habit)
        click.echo(f"Longest streak for '{name}': {streak} days")
    except ValueError as e:
        click.echo(f"Error: {e}")
        
@cli.command("show-longest-streak")
@ensure_up_to_date
def show_longest_streak():
    """
    Show the longest streak for all habits.
    """

    habits      = database.get_all_habits()
    instances   = database.get_all_active_habits()

    result = database.longest_streak_all(habits, instances)
    click.echo(f"Overall best streak: {result['max_of_all']}")
    for h, s in result["per_habit"].items():
        click.echo(f"  • {h}: {s}")
        
        
@cli.command("delete-habit")
@click.argument("habit_id")
def delete_habit_cli(habit_id):
    database.delete_habit_by_id(habit_id)
    click.echo(f"Deleted habit {habit_id}")

    
