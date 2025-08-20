# Habit Tracker – OOP & Functional Programming

This project is a **Habit Tracker** written in Python as part of a portfolio project at **IU International University**. It demonstrates both **Object-Oriented Programming (OOP)** and **Functional Programming (FP)** in a practical context.

## Core functionality
- Access via CLI 
- Creating and deleting habits
- Managing habits
- Analyzing habits

## Getting Started

### Prerequisites

- Python 3.x
- pip

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-username/habit-tracker.git
    ```
2.  Navigate to the project directory:
    ```bash
    cd habit-tracker
    ```
3.  It is recommended to use a virtual environment to manage dependencies. You can use `venv` or `conda`.

    **Using `venv`:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

    **Using `conda`:**
    ```bash
    conda create --name habit-tracker python=3.9
    conda activate habit-tracker
    ```
4.  Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

To run the application, use the following command:

```bash
python Source/main.py [COMMAND]
```

## Usage

The application is controlled via a command-line interface. The following commands are available:

### `add-habit`

Adds a new habit to the database.

**Usage:**

```bash
python Source/main.py add-habit [OPTIONS] NAME
```

**Options:**

-   `--start-date, -s`: The date when the first instance should start (YYYY-MM-DD). Default is today.
-   `--period, -p`: The habit's periodicity (`daily` or `weekly`). Default is `daily`.
-   `--description, -d`: An optional description of the habit.
-   `--weekday, -w`: The weekday for weekly habits (0=Monday, 6=Sunday). Only used for weekly habits.

### `list-all-habits`

Retrieves all habits from the database.

**Usage:**

```bash
python Source/main.py list-all-habits [OPTIONS]
```

**Options:**

-   `--type, -t`: Filter habits by type (`all`, `daily`, or `weekly`). Default is `all`.

### `list-all-active-habits`

Retrieves all active habit instances and prints them as a table.

**Usage:**

```bash
python Source/main.py list-all-active-habits [OPTIONS]
```

**Options:**

-   `--name, -n`: An optional name to filter active habits.

### `complete-task`

Marks a habit instance as completed.

**Usage:**

```bash
python Source/main.py complete-task [OPTIONS] NAME
```

**Options:**

-   `--date, -d`: An optional date to complete tasks.

### `show-longest-streak`

Shows the longest streak for a habit or the best streak of all habits.

**Usage:**

```bash
python Source/main.py show-longest-streak [OPTIONS]
```

**Options:**

-   `--name, -n`: An optional name to filter habits for the longest streak. If not provided, shows the overall best streak.

### `delete-habit`

Deletes a habit from the database.

**Usage:**

```bash
python Source/main.py delete-habit HABIT_ID
```

### Help

You can always just use
```bash
python Source/main.py --help
```
or 
```bash
python Source/main.py [COMMAND] --help
```
to open the help menu for the application or command.

## Testing

To run the automated tests, make sure you have `pytest` installed (it's included in `requirements.txt`). Then, run the following command from the project's root directory:

```bash
pytest
```

This will discover and run all the tests in the `Source/test_project.py` file.

## Project Phases 

### Conception Phase 

- Developing concepts for the app
- Folder "Conception Phase" includes all relevant information and files related to the phase.

### Development Phase 

- Start of implementing components
- Folder "Development Phase" includes all relevant information and files related to the phase.
    - Project Presentation 

### Finalization Phase 

- Improvement and refinement of concept and design, implementation and documentation.
- Folder "Finalization Phase" includes all relevant information and files related to the phase.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
