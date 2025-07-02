import click
from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session

from models import DailyHabit, WeeklyHabit, HabitInstance, Habit
import database


@click.group()
def cli():
    """📝 Habit Tracker CLI"""
    pass

@cli.command("add-habit")
@click.argument("name", metavar="NAME")
@click.option(
    "--start-date", "-s",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=date.today().isoformat(),
    show_default=True,
    help="When the first instance should start (YYYY-MM-DD)"
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

def add_habit(name : str, start_date : date, period_type : str, description : str=None,):
    if period_type == 'daily':
        habit = DailyHabit(name=name, description=description)
    elif period_type == 'weekly':
        habit = WeeklyHabit(name=name, description=description)
    
    database.save_habit(database.engine, habit)
        
    habit_instance = HabitInstance(habit=habit, period_start=start_date)
    database.save_instance(database.engine, habit_instance)
    click.echo(f'Habit "{name}" added successfully!')
    
    
    
@cli.command("list-all-habits")
def list_all_habits(habit_type: str = "all"):
    """Retrieve all habits from the database."""
    # Normalize
    p = None if habit_type == "all" else habit_type.lower()
    habits = database.get_all_habits(period=p)
    if not habits:
        click.echo("No habits found.")
        return
    click.echo("📋 Habits:")
    for h in habits:
        click.echo(f"  • [{h.id}] {h.name} ({h.type}), created {h.date_created.date()}")
       
@cli.command("list-all-active-habits")
def list_all_active_habits():
    """Retrieve all active habit instances and print in a neat table."""
    insts = database.get_all_active_habits()
    if not insts:
        click.echo("No active habits found.")
        return

    # Prepare the rows
    rows = []
    for inst in insts:
        done = (
            inst.completed_at.strftime("%Y-%m-%d %H:%M")
            if inst.completed_at else "Not completed"
        )
        rows.append({
            "id":           str(inst.id),
            "name":         inst.habit.name,
            "type":         inst.habit.type,
            "period_start": inst.period_start.strftime("%Y-%m-%d"),
            "due":        inst.due_date.strftime("%Y-%m-%d") if inst.due_date else "No due date",
            "completed":    done
        })

    # Compute column widths
    cols = ["id","name","type","period_start","due","completed"]
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
def complete_task(name: str = None, date : Optional[date] = None):
    """Mark a habit instance as completed."""
    if not name:
        click.echo("Please provide a habit instance ID to complete.")
        return
    
    try:
        database.complete_task(name, date)
        click.echo(f"Habit instance {name} marked as completed!")
    except ValueError as e:
        click.echo(f"Error: {e}")

if __name__ == "__main__":
    #complete_task(name="Touch grass")
    cli()

'''
                f"  • [{h.id}] 
                {h.habit_id}
                completed at: {h.completed_at.strftime("%Y-%m-%d %H:%M") if h.completed_at is not None else 'Not completed'}"
                )
        '''
