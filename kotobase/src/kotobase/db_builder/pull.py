import gdown
import click
from kotobase.db_builder.config import DATABASE_PATH

# The ID of the Google Drive file for the database
DRIVE_FILE_ID = "1Ejio0X_tcSszt_0nIhJsBqdi-sKfbKqq"


@click.command('pull-db')
@click.option('--force',
              is_flag=True,
              help="Force re-download even if the file exists.")
def pull_db(force):
    """Downloads the latest Kotobase database from Google Drive."""

    if DATABASE_PATH.exists() and not force:
        click.echo("Database file already exists. Use --force to re-download.")
        return

    click.echo("Downloading the latest database from Google Drive...")

    try:
        # Use the file ID directly for a reliable download
        gdown.download(id=DRIVE_FILE_ID,
                       output=str(DATABASE_PATH),
                       quiet=False)
        click.secho("Database downloaded successfully.", fg="green")
    except Exception as e:
        click.secho(f"An error occurred: {e}", fg="red")
        click.echo("Please try building the \
            database manually with 'kotobase build'.")


__all__ = ["DRIVE_FILE_ID", "pull_db"]
