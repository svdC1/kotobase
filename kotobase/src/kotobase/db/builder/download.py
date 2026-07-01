"""
Defines helpers to download the upstream sources used in the
[`Build Pipeline`][kotobase.db.builder.build], and the pre-built
`kotobase` database

Fetches raw upstream source files and saves them in the `raw` per-user cache
directory (See The [`cofig`][kotobase.db.builder.config] Module)

Downloads are written to a temporary `.part` file and moved into place only on
succes, so an interrupted run never leaves a truncated file that a later run
would mistake for a complete download

Except for the kotobase databases which are decompressed as they are
downloaded, files are downloaded in their compressed form and left untouched

info: Supported Sources
    - Plain Direct URL To Asset File

    - GitHub Release Asset, Resolved From The Latest Release Of A Repo
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import requests
import zstandard

from ...exceptions import DatabaseExistsError, DownloadError
from ...terminal_output import THEMED_CONSOLE, download_progress_bar
from .config import (
    AUDIO_ASSET,
    DB_ASSET,
    RELEASE_REPO,
    SOURCES,
    USER_AGENT,
    Source,
    audio_db_path,
    db_path,
    ensure_dirs,
    raw_dir,
)


def _session() -> requests.Session:
    """
    Builds a `requests` session with the `kotobase` user agent

    When a `GITHUB_TOKEN` environment variable is present, it is sent as a
    bearer token, which raises the GitHub API rate limit for release lookups

    Returns:
        A configured requests session
    """
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})
    return session


def _get_github_asset_url(
    repo: str,
    asset: str | None,
    use_regex: bool = False,
    tag: str | None = None,
    session: requests.Session | None = None,
) -> tuple[str, str]:
    """
    Resolves a GitHub Release Asset to its download URL

    When a `GITHUB_TOKEN` environment variable is present, it is sent as a
    bearer token, which raises the GitHub API rate limit for release lookups

    Args:
        repo (str): GitHub repository in `owner/name` form
        asset (str | None): Exact asset filename to download, a regex
            expression matching the desired asset filename to download when
            `use_regex=True`, or `None` for the first asset returned by the API
        use_regex (bool): When `True`, treats `asset` as a regex expression. If
            there's more than one match, the first one will be used
        tag (str | None): Release tag to use, or `None` for the latest release
        session (requests.Session | None): Optional session to use for the
            request

    Returns:
        Tuple containing the name of the assets and its download URL

    Raises:
        DownloadError: If the GitHub API request fails, if `asset` is not
            present on the `tag` / latest release, if the `asset` regex
            expression (when `regex=True`) has no matches in the `tag` / latest
            release, if the tag / latest release of `repo` has no assets, or if
            the api's `JSON` response is malformed
    """

    # Resolve Tag
    if tag is not None:
        api = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    else:
        api = f"https://api.github.com/repos/{repo}/releases/latest"

    # Resolve Token
    token = os.environ.get("GITHUB_TOKEN")

    # Get Available Assets
    if session is not None:
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
        session.headers.update({"User-Agent": USER_AGENT})
        response = session.get(
            api,
            headers={"Accept": "application/vnd.github+json"},
            timeout=30,
        )
    else:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = requests.get(
            api,
            headers=headers,
            timeout=30,
        )

    try:
        response.raise_for_status()
    except requests.RequestException as e:
        raise DownloadError(
            f"GitHub API Request Failed For '{api}' : {e}"
        ) from e
    try:
        resp_json: dict[str, Any] = response.json()
    except ValueError as e:
        raise DownloadError(f"Received Malformed API Response : {e}") from e

    if not isinstance(resp_json, dict):
        raise DownloadError("Received Malformed API Response")

    if "assets" not in resp_json:
        raise DownloadError(f"Release '{api}' Has No Assets")

    if asset is None:
        first = resp_json["assets"][0]
        return first["name"], first["browser_download_url"]

    if use_regex:
        pattern = re.compile(asset)
        chosen = next(
            (a for a in resp_json["assets"] if pattern.fullmatch(a["name"])),
            None,
        )
        if chosen is None:
            raise DownloadError(
                f"No Matching Release Asset Found For '{asset!r}' In "
                f"'{api}' Release"
            )
        return chosen["name"], chosen["browser_download_url"]
    else:
        chosen = next(
            (a for a in resp_json["assets"] if a["name"] == asset), None
        )
        if chosen is None:
            raise DownloadError(
                f"No Matching Release Asset Found For '{asset}' In "
                f"'{api}' Release"
            )
        return chosen["name"], chosen["browser_download_url"]


def resolve_upstream_source(
    source: Source, session: requests.Session
) -> tuple[str, str]:
    """
    Resolves an upstream source to a concrete filename and download URL

    info: Resolution
        - Direct sources names resolve to the final path segment of their URL

        - GitHub release sources are resolved against the latest release,
          selecting the asset by exact name or by regular expression pattern

    Args:
        source (Source): The source to resolve
        session (requests.Session): Session used for any GitHub API lookup

    Returns:
        A tuple of the local filename to save under and the URL to fetch

    Raises:
        DownloadError: If the source has neither a URL nor a GitHub repository,
            or if a matching GitHub release asset cannot be found
    """
    if source.url:
        name = source.url.split("?")[0].rstrip("/").split("/")[-1]
        if "." not in name:
            name = f"{source.key}.tar.gz"
        return name, source.url

    if not source.github_repo:
        raise DownloadError(
            f"Source '{source.key!r}' Has No `url` or `github_repo`"
        )
    if source.asset_pattern:
        return _get_github_asset_url(
            source.github_repo,
            source.asset_pattern,
            use_regex=True,
            session=session,
        )
    return _get_github_asset_url(
        source.github_repo,
        source.asset,
        session=session,
    )


def _download_stream(
    url: str,
    dest: Path,
    session: requests.Session,
    label: str,
    clear: bool = True,
) -> None:
    """
    Streams the download of a file URL to a destination file path with a
    `rich` progress bar

    The body is written to a sibling `.part` file and atomically moved onto
    `dest` once the transfer completes

    Args:
        url (str): The URL to download
        dest (Path): The final destination path
        session (requests.Session): Session used for the request
        label (str): Short label shown on the progress bar
        clear (bool): Whether to set `visible=False` on the `rich.Progress`
            task when download end

    Raises:
        DownloadError: If the download fails for any reason
    """
    part = dest.with_name(dest.name + ".part")
    try:
        with session.get(url, stream=True, timeout=120) as response:
            response.raise_for_status()
            # Get File Size
            total = int(response.headers.get("content-length", 0)) or None
            with download_progress_bar() as progress:
                task = progress.add_task(label, total=total)
                with open(part, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=65536):
                        handle.write(chunk)
                        progress.update(task, advance=len(chunk))
                if clear:
                    progress.update(task, visible=False)
        part.replace(dest)
    except Exception as e:
        part.unlink(missing_ok=True)
        raise DownloadError(
            f"Couldn't Download File At '{url}' : '{e}'"
        ) from e


def download(
    source: Source,
    *,
    force: bool = False,
    session: requests.Session | None = None,
) -> Path:
    """
    Downloads a single upstream source into the per-user cache raw directory

    Args:
        source (Source): The source to download
        force (bool): When True, re download even if the file already exists
        session (requests.Session | None): Optional shared session, a new one
            is created when omitted

    Raises:
        DownloadError: If the download fails for any reason

    Returns:
        The path of the downloaded file
    """
    session = session or _session()
    ensure_dirs()
    name, url = resolve_upstream_source(source, session)
    dest = raw_dir() / name
    if dest.exists() and dest.stat().st_size > 0 and not force:
        THEMED_CONSOLE.print(
            f"[success]Using Cached[/] -> [info]{source.key} ({name})[/]"
        )
        return dest
    _download_stream(
        url,
        dest,
        session,
        f"Downloading {source.key}",
    )
    return dest


def download_all(
    keys: list[str] | None = None,
    *,
    force: bool = False,
    include_optional: bool = True,
    session: requests.Session | None = None,
) -> dict[str, Path]:
    """
    Downloads a set of upstream sources listed in the
    [`SOURCES`][kotobase.db.builder.config.SOURCES] dictionary

    Optional sources that fail to download are skipped with a warning rather
    than aborting the whole run. A failure of a required source is raised

    Args:
        keys (list[str] | None): Source keys to download, or None for every
            source in [`SOURCES`][kotobase.db.builder.config.SOURCES]
        force (bool): When True, re download even if files already exist
        include_optional (bool): When False, optional sources are skipped
        session (requests.Session | None): Optional shared session, a new one
            is created when omitted

    Returns:
        A mapping of source keys to their downloaded file path, with optional
            sources that failed left out

    Raises:
        DownloadError: If a required source fails to download
    """
    session = session or _session()
    if keys is None:
        keys = [k for k, source in SOURCES.items() if not source.optional]
        if include_optional:
            keys += [k for k, source in SOURCES.items() if source.optional]

    result: dict[str, Path] = {}
    for key in keys:
        source = SOURCES[key]
        try:
            result[key] = download(source, force=force, session=session)
        except DownloadError as e:
            if source.optional:
                THEMED_CONSOLE.print(
                    f"[warning]Skipping Optional Source Failure[/] For [info]"
                    f"{key}[/]: [danger]{e}[/]"
                )
                continue
            raise
    return result


def _download_and_decompress(url: str, destination: Path, label: str) -> None:
    """
    Streams a zstandard-compressed asset and decompresses it onto a destination
    path

    The download chunks are decompressed as they are pulled and saved to a
    temporary `.part` file which is moved into place only on success

    Args:
        url (str): The asset download URL
        destination (Path): The final decompressed file path
        label (str): Short label shown on the progress bar

    Raises:
        DownloadError: If the download request fails,
            or any I/O or network error occurs
    """
    part = destination.with_name(destination.name + ".part")
    decompressor = zstandard.ZstdDecompressor()

    try:
        with requests.get(
            url,
            stream=True,
            timeout=120,
            headers={"User-Agent": USER_AGENT},
        ) as response:
            response.raise_for_status()
            total_download = (
                int(response.headers.get("content-length", 0)) or None
            )
            total_uncompressed_written = 0

            with (
                download_progress_bar() as progress,
                open(part, "wb") as handler,
                decompressor.stream_writer(handler) as writer,
            ):
                task = progress.add_task(label, total=total_download)
                # Iterate over the compressed network chunks
                chunk: bytes
                for chunk in response.iter_content(chunk_size=65536):
                    # Decompresses the compressed chunks and writes them to
                    # part which results in a bigger `written` chunk
                    total_uncompressed_written += writer.write(chunk)
                    written_mb = total_uncompressed_written / (1024 * 1024)
                    # Updates the progress bar based on the size of the
                    # compressed chunks pulled from the network
                    progress.update(
                        task,
                        description=f"{label} ({written_mb:.2f}MB)",
                        advance=len(chunk),
                    )

        part.replace(destination)

    except Exception as e:
        # All context managers are closed here, freeing file write locks
        part.unlink(missing_ok=True)
        raise DownloadError(f"Failed To Download {url} : {e}") from e


def pull_db(*, tag: str | None = None, force: bool = False) -> Path:
    """
    Downloads and decompresses the prebuilt core database

    Args:
        tag (str | None): Release tag to pull from, or None for the latest
        force (bool): When True, download even if the database already exists

    Returns:
        The path of the decompressed database

    Raises:
        DatabaseExistsError: If the database already exists and `force` is
            False
    """
    ensure_dirs()
    destination = db_path()
    if destination.exists() and not force:
        raise DatabaseExistsError(
            f"Core Database Already Exists At '{destination}',"
            f" Pass Force To Replace"
        )
    _name, url = _get_github_asset_url(
        RELEASE_REPO, DB_ASSET, tag=tag, session=_session()
    )
    _download_and_decompress(url, destination, "Downloading Core Database")
    return destination


def pull_audio(*, tag: str | None = None, force: bool = False) -> Path:
    """
    Download and decompress the optional audio pack database

    Args:
        tag (str | None): Release tag to pull from, or None for the latest
        force (bool): When True, download even if the audio pack already exists

    Returns:
        The path of the decompressed audio pack

    Raises:
        DatabaseExistsError: If the audio pack already exists and `force` is
            False
    """
    ensure_dirs()
    destination = audio_db_path()
    if destination.exists() and not force:
        raise DatabaseExistsError(
            f"Audio Pack Database Already Exists At '{destination}', Pass"
            f" Force To Replace"
        )
    _name, url = _get_github_asset_url(
        RELEASE_REPO, AUDIO_ASSET, tag=tag, session=_session()
    )
    _download_and_decompress(url, destination, "Downloading Audio Database")
    return destination
