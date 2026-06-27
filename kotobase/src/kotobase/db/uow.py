"""
Defines a `Unit Of Work` exposing the [`Repos`][kotobase.db.repos] that
abstract queries for kotobase's database

info: UOW
    - The [`UnitOfWork`][kotobase.db.uow.UnitOfWork] owns a single database
      session for the duration of a `with` block and hands off that session
      for the repositories to use

    - Repositories never open their own session, they share the one held
      by the unit of work, which keeps every query in an operation within a
      single consistent read
"""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

from .connection import get_sessionmaker
from .repos import (
    AudioRepo,
    FuriganaRepo,
    JLPTRepo,
    JMDictRepo,
    JMNeDictRepo,
    KanjiRepo,
    RadicalRepo,
    SentenceRepo,
    TagRepo,
)


class UnitOfWork:
    """
    Context manager that holds one session and its repositories

    Attributes:
        session (Session | None): The active session inside the `with` block,
            or None outside of it
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        """
        Create a unit of work

        Args:
            session_factory (sessionmaker[Session] | None): Factory used to
                open the session, defaulting to the shared read-only factory
        """
        self._session_factory = session_factory or get_sessionmaker()
        self.session: Session | None = None

    def __enter__(self) -> UnitOfWork:
        """
        Open the session and enter the context

        Returns:
            The unit of work itself
        """
        self.session = self._session_factory()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """
        Close the session and leave the context

        Args:
            exc_type (type[BaseException] | None): Exception type if one was
                raised inside the context
            exc (BaseException | None): Exception instance if one was raised
            traceback (TracebackType | None): Traceback if one was raised
        """
        if self.session is not None:
            self.session.close()
            self.session = None

    @property
    def _bound_session(self) -> Session:
        """
        Return the active session or fail if the context is not open

        Returns:
            The active session

        Raises:
            RuntimeError: If accessed outside of a `with` block
        """
        if self.session is None:
            raise RuntimeError(
                "UnitOfWork Is Not Active, Use It Inside A With Block"
            )
        return self.session

    @property
    def jmdict(self) -> JMDictRepo:
        """
        Repository for JMdict entries

        Returns:
            A JMdict repository bound to the active session
        """
        return JMDictRepo(self._bound_session)

    @property
    def jmnedict(self) -> JMNeDictRepo:
        """
        Repository for JMnedict proper names

        Returns:
            A JMnedict repository bound to the active session
        """
        return JMNeDictRepo(self._bound_session)

    @property
    def kanji(self) -> KanjiRepo:
        """
        Repository for kanji

        Returns:
            A kanji repository bound to the active session
        """
        return KanjiRepo(self._bound_session)

    @property
    def radicals(self) -> RadicalRepo:
        """
        Repository for radicals and radical search

        Returns:
            A radical repository bound to the active session
        """
        return RadicalRepo(self._bound_session)

    @property
    def furigana(self) -> FuriganaRepo:
        """
        Repository for furigana segmentation

        Returns:
            A furigana repository bound to the active session
        """
        return FuriganaRepo(self._bound_session)

    @property
    def sentences(self) -> SentenceRepo:
        """
        Repository for Tatoeba example sentences

        Returns:
            A sentence repository bound to the active session
        """
        return SentenceRepo(self._bound_session)

    @property
    def jlpt(self) -> JLPTRepo:
        """
        Repository for the Tanos JLPT lists

        Returns:
            A JLPT repository bound to the active session
        """
        return JLPTRepo(self._bound_session)

    @property
    def tags(self) -> TagRepo:
        """
        Repository for the tag dictionary

        Returns:
            A tag repository bound to the active session
        """
        return TagRepo(self._bound_session)

    @property
    def audio(self) -> AudioRepo:
        """
        Repository for pronunciation audio

        Returns:
            An audio repository bound to the active session
        """
        return AudioRepo(self._bound_session)
