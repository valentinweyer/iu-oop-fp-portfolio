from cli import cli
import database
import seed_data

@cli.command("seed-db")
def seed_db():
    """📊 Seeds the database with some sample data."""
    database.create_db_and_tables()
    seed_data.seed_data()

if __name__ == "__main__":
    cli()
