import click
from datetime import date
from typing import Optional
import sqlalchemy
from rich.console import Console
from rich.table import Table
import wcwidth


from models import DailyHabit, WeeklyHabit, HabitInstance
import database

# ---------- display-width helpers (emoji-aware) ----------
try:
    from wcwidth import wcwidth
except ImportError:
    def wcwidth(c):
        return 1  # naive fallback if wcwidth isn't installed

def display_len(s: str) -> int:
    return sum(max(wcwidth(c), 0) for c in s)

def pad_display(s: str, target: int) -> str:
    pad = target - display_len(s)
    return s + (" " * pad if pad > 0 else "")

# ---------- custom group with fixed column alignment ----------
class FixedWidthGroup(click.Group):
    EMOJI_PREFIXES = {"✨", "✅", "🗑️", "𝌵", "📋", "📊", "🏆"}

    def format_commands(self, ctx, formatter):
        rows = []  # each entry: (name, emoji, rest_of_help)
        for name in self.list_commands(ctx):
            cmd = self.get_command(ctx, name)
            if cmd is None:
                continue
            short_help = cmd.get_short_help_str(limit=1000) or ""
            short_help = " ".join(short_help.split())  # collapse internal whitespace/newlines

            emoji = ""
            rest = short_help
            if short_help:
                first_part, *rest_parts = short_help.split(" ", 1)
                if first_part in self.EMOJI_PREFIXES:
                    emoji = first_part
                    rest = rest_parts[0] if rest_parts else ""
            rows.append((name, emoji, rest))

        if not rows:
            return

        max_name_width = max(display_len(name) for name, _, _ in rows)
        max_emoji_width = max(display_len(emoji) for _, emoji, _ in rows) if any(e for _, e, _ in rows) else 0

        with formatter.section("Commands"):
            for name, emoji, rest in rows:
                name_padded = pad_display(name, max_name_width)
                if emoji:
                    emoji_padded = pad_display(emoji, max_emoji_width)
                    line = f"  {name_padded}  {emoji_padded}  {rest}"
                else:
                    # no emoji, align as if empty column
                    spacer = " " * (max_emoji_width + 2) if max_emoji_width else ""
                    line = f"  {name_padded}{spacer}  {rest}"
                formatter.write_text(line)

# ---------- CLI definition ----------
CONTEXT_SETTINGS = {"max_content_width": 160}

@click.group(
    cls=FixedWidthGroup,
    context_settings=CONTEXT_SETTINGS,
    help="📝 Habit Tracker CLI"
)
def cli():
    """📝 Habit Tracker CLI"""
    pass



console = Console()

def ensure_up_to_date(f):
    @click.pass_context
    def wrapper(ctx, *args, **kwargs):
        database.backfill_instances()
        return ctx.invoke(f, *args, **kwargs)
    return wrapper

@cli.command("add-habit", short_help="✨ Adds a new habit to the database.")
@click.argument("name", metavar="NAME")
@click.option(
    "--start-date", "-s",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=date.today().isoformat(),
    show_default=True,
    help="The date when the first habit instance should begin (YYYY-MM-DD). Defaults to today."
)
@click.option(
    "--period", "-p",
    "period_type",
    type=click.Choice(["daily", "weekly"], case_sensitive=False),
    default="daily",
    show_default=True,
    help="The periodicity of the habit, either 'daily' or 'weekly'."
)
@click.option(
    "--description", "-d",
    default=None,
    help="An optional description for the habit."
)
@click.option(
    "--weekday", "-w",
    default=None,
    help="For weekly habits, the day of the week (0=Monday, 6=Sunday). Defaults to None for daily habits.",
)
def add_habit(name : str, start_date : date, period_type : str, description : str=None, weekday: Optional[int] = None):
    
    if period_type == 'daily':
        habit = DailyHabit(name=name, description=description)                      # create a daily habit
    elif period_type == 'weekly':
        habit = WeeklyHabit(name=name, description=description, weekday=weekday)    # create a weekly habit with optional weekday
    
    database.save_habit(habit)                                     # save the habit to the database
    
    if weekday is not None and period_type == "weekly":
        start_date = habit.first_period_start(after=start_date)                     # calculate the first period start for weekly habits    
        
    habit_instance = HabitInstance(habit=habit, period_start=start_date)            # create a habit instance with the habit and the start date
    database.save_instance(habit_instance)                         # save the habit instance to the database
    console.print(f'Habit "[bold green]{name}[/bold green]" added successfully!')
    
    
    
@cli.command("list-all-habits", short_help="📋 Retrieves and displays all habits from the database.")
@click.option(
    "--type", "-t",
    "habit_type",
    type=click.Choice(["all", "daily", "weekly"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Filter the habits by their type: 'all', 'daily', or 'weekly'."
)
@ensure_up_to_date
def list_all_habits(habit_type: str = "all"):
    p = None if habit_type == "all" else habit_type.lower()     # Filter by type"      
    habits = database.get_all_habits(period=p)
    if not habits:
        console.print("No habits found.")
        return
    
    table = Table(title="All Habits")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="magenta")
    table.add_column("Type", style="green")
    table.add_column("Date Created", style="blue")

    for h in habits:
        table.add_row(
            str(h.id),
            h.name,
            h.type,
            h.date_created.date().isoformat()
        )
    
    console.print(table)
       
@cli.command("list-all-active-habits", short_help="𝌵 \b Retrieves all active habit instances and displays them in a table.")
@click.option(
    "--name", "-n",
    default=None,
    show_default=True,
    help="Filter the active habits by a specific name."
)
@ensure_up_to_date
def list_all_active_habits(name : str = None):
    instances = database.get_all_active_habits(name=name)  # Get all active habit instances, optionally filtered by name
    # Sort by the date (earliest first)
    instances.sort(key=lambda inst: inst.period_start)
    
    if not instances:
        console.print("No active habits found.")
        return

    table = Table(title="Active Habits")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="magenta")
    table.add_column("Type", style="green")
    table.add_column("Weekday", style="yellow")
    table.add_column("Period Start", style="blue")
    table.add_column("Due", style="red")
    table.add_column("Completed", style="bold green")

    for instance in instances:
        done = (
            instance.completed_at.strftime("%Y-%m-%d %H:%M")
            if instance.completed_at else "[bold red]Not completed[/bold red]"
        )
        weekday = (
            str(instance.habit.weekday)
            if isinstance(instance.habit, WeeklyHabit) and instance.habit.weekday is not None
            else "N/A"
        )
        table.add_row(
            str(instance.id),
            instance.habit.name,
            instance.habit.type,
            weekday,
            instance.period_start.strftime("%Y-%m-%d"),
            instance.due_date.strftime("%Y-%m-%d") if instance.due_date else "No due date",
            done
        )
    
    console.print(table)

@cli.command("complete-task", short_help="✅ Marks a specific habit instance as completed.")
@click.argument("name", metavar="NAME")
@click.option(
    "--date", "-d",
    default=None,
    help="The date for which to mark the habit as completed (YYYY-MM-DD). Defaults to today."
)
@ensure_up_to_date
def complete_task(name: str = None, date : Optional[date] = None):
    if not name:
        console.print("[bold red]Please provide a habit instance ID to complete.[/bold red]")
        return
    
    try:
        database.complete_task(name, date)
        console.print(f"Habit instance [bold green]{name}[/bold green] marked as completed!")
    except ValueError as e:
        # User-facing errors (e.g., "habit not found")
        console.print(f"[bold red]Error: {e}[/bold red]")
    except sqlalchemy.exc.SQLAlchemyError as e:
        # Database-level errors
        console.print(f"[bold red]Database error: Could not complete the operation. Details: {e}[/bold red]")
    except Exception as e:
        # Catch any other unexpected errors
        console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")

        
@cli.command("show-longest-streak", short_help="🏆 Shows the longest streak for a specific habit or the best streak among all habits.")
@click.option(
    "--name", "-n",
    default=None,
    help="The name of the habit to show the longest streak for. If not provided, it shows the best streak among all habits."
)
@ensure_up_to_date
def show_longest_streak(name: str = None):
    if not name:
        habits      = database.get_all_habits()
        instances   = database.get_all_active_habits()

        result = database.longest_streak_all(habits, instances)
        console.print(f"Overall best streak: [bold green]{result['max_of_all']}[/bold green]")
        
        table = Table(title="Streaks Per Habit")
        table.add_column("Habit", style="magenta")
        table.add_column("Streak", style="green")

        for h, s in result["per_habit"].items():
            table.add_row(h, str(s))
        
        console.print(table)
        return
    
    habit = database.get_habit_by_name(name)
    
    try:
        streak = database.current_streak_for_habit(habit=habit)
        console.print(f"Longest streak for '[bold blue]{name}[/bold blue]': [bold green]{streak}[/bold green] days")
    except ValueError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        
        
@cli.command("delete-habit", short_help="🗑️ Deletes a habit from the database.")
@click.argument("name")
def delete_habit_cli(name: str):
    habit = database.get_habit_by_name(name)
    
    if not habit:
        console.print(f"[bold red]Habit '{name}' not found.[/bold red]")
        return
    
    habit_id = habit.id
    
    
    if not click.confirm(f"Are you sure you want to delete the habit '{name}'? This action cannot be undone.", default=False):
        console.print("Deletion cancelled.")
        return
    
    database.delete_habit_by_id(habit_id)
    console.print(f"Deleted habit [bold red]{name}[/bold red]")
