"""
This module defines the click command which pulls a pre-built
database from a public Google Drive folder.
"""

import gdown
import click
import sys
from kotobase.db_builder.config import DATABASE_PATH, DB_BUILD_LOG_PATH

# The ID of the Google Drive file for the database
DRIVE_FILE_ID = "1Ejio0X_tcSszt_0nIhJsBqdi-sKfbKqq"

# The ID of the Google Drive file for the database log
DRIVE_LOG_FILE_ID = "12BG6KIueRFETqbVcwDQtLi5aQWsX7MMj"


@click.command('pull-db')
@click.option('--force',
              is_flag=True,
              help="Force re-download even if the file exists."
              )
def pull_db(force):
    """
    Downloads the latest Kotobase database from Google Drive.
    """

    if DATABASE_PATH.exists() and not force:
        click.echo("Database file already exists. Use --force to re-download.")
        return
    elif DATABASE_PATH.exists() and force:
        try:
            DATABASE_PATH.unlink()
            DB_BUILD_LOG_PATH.unlink(missing_ok=True)
            click.secho("Deleted Old Database File", fg="green")

        except FileNotFoundError:
            click.secho("Database File Doesn't Exist, Remove '--force' flag.",
                        fg="red",
                        err=True
                        )
            sys.exit(1)
        except PermissionError:
            click.secho("No Permission To Delete Database File",
                        fg="red",
                        err=True
                        )
            sys.exit(1)
        except Exception as e:
            click.secho(
                f"Unexpected Error While Deleting Database File: {e}",
                fg="red",
                err=True
                )
            sys.exit(1)

    click.secho("Pulling Latest From Drive...",
                fg="blue")

    try:
        # Use the file ID directly
        gdown.download(id=DRIVE_FILE_ID,
                       output=str(DATABASE_PATH),
                       quiet=False)
        click.secho("Pulling Build Log...")
        # Also pull build log
        gdown.download(id=DRIVE_LOG_FILE_ID,
                       output=str(DB_BUILD_LOG_PATH),
                       quiet=False)
        click.secho("Database downloaded successfully.", fg="green")
    except Exception as e:
        click.secho(f"An error occurred: {e}", fg="red")
        click.echo("Please try building the \
            database manually with 'kotobase build'.")


__all__ = ["DRIVE_FILE_ID", "pull_db"]
