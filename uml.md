classDiagram
    class Habit {
        +id: String
        +name: String
        +description: String
        +date_created: DateTime
        +type: String
        +weekday: Integer
        +next_period_start(after: date) date
        +get_data() dict
    }

    class DailyHabit {
        +next_period_start(after: date) date
        +get_data() dict
    }

    class WeeklyHabit {
        +weekday: Integer
        +first_period_start(after: date) date
        +next_period_start(after: date) date
        +get_data() dict
    }

    class HabitInstance {
        +id: String
        +habit_id: String
        +period_start: Date
        +due_date: Date
        +completed_at: DateTime
        +is_completed() bool
        +mark_completed()
        +get_data() dict
    }

    Habit <|-- DailyHabit
    Habit <|-- WeeklyHabit
    Habit "1" -- "0..*" HabitInstance : has

    class database {
        <<Module>>
        +save_habit(habit: Habit) None
        +save_instance(instance: HabitInstance) None
        +complete_task(name: str, date: date) None
        +get_all_habits(period: str) list[Habit]
        +get_all_active_habits(Name: str) list[Habit]
        +longest_streak_for_habit(instances: list[HabitInstance], habit: Habit) int
        +get_habit_by_name(name: str) Habit
        +backfill_instances() None
        +longest_streak_all(habits: list[Habit], all_instances: list[HabitInstance]) dict
    }

    class cli {
        <<Module>>
        +add_habit(name: str, start_date: date, period_type: str, description: str, weekday: int) None
        +list_all_habits(habit_type: str) None
        +list_all_active_habits() None
        +complete_task(name: str, date: date) None
        +show_longest_streak_for_habit(name: str) None
        +show_longest_streak() None
    }

    cli ..> database : uses
    database ..> Habit : uses
    database ..> DailyHabit : uses
    database ..> WeeklyHabit : uses
    database ..> HabitInstance : uses
