# app/db/database.py
from __future__ import annotations

import logging
import re
from typing import Any, Mapping, Optional, Sequence, Tuple, List, AsyncIterator

import asyncpg  # in requirements aufnehmen (z.B. asyncpg>=0.29)

logger = logging.getLogger(__name__)

# :named_param → für unsere SQL-Queries in den Repositories
_PARAM_PATTERN = re.compile(r":([a-zA-Z_][a-zA-Z0-9_]*)")


class Database:
    """
    Leichter Wrapper um asyncpg für Supabase/Postgres.

    Erwartete DSN (z.B. aus Settings / ENV):
        postgresql://user:password@host:5432/dbname
        oder
        postgres://...

    Unterstützt benannte Parameter im Stil :param_name, wie in deinen Repos.
    """

    def __init__(
        self,
        dsn: str,
        *,
        min_size: int = 1,
        max_size: int = 10,
    ) -> None:
        self._dsn = dsn
        self._min_size = min_size
        self._max_size = max_size
        self._pool: Optional[asyncpg.Pool] = None

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    async def connect(self) -> None:
        """
        Erstellt den Connection-Pool, falls noch nicht vorhanden.
        """
        if self._pool is not None:
            logger.debug("Database.connect() aufgerufen, Pool existiert bereits.")
            return

        logger.info(
            "Erzeuge asyncpg-Pool (min_size=%s, max_size=%s)...",
            self._min_size,
            self._max_size,
        )
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            min_size=self._min_size,
            max_size=self._max_size,
        )
        logger.info("DB-Pool initialisiert.")

    async def disconnect(self) -> None:
        """
        Schließt den Connection-Pool.
        """
        if self._pool is None:
            logger.debug("Database.disconnect() aufgerufen, aber kein Pool vorhanden.")
            return

        await self._pool.close()
        self._pool = None
        logger.info("DB-Pool geschlossen.")

    # ------------------------------------------------------------------ #
    # Public Query-API
    # ------------------------------------------------------------------ #

    async def fetch_one(
        self,
        query: str,
        params: Optional[Mapping[str, Any]] = None,
    ) -> Optional[Mapping[str, Any]]:
        """
        SELECT, der genau einen Datensatz oder None zurückgibt.
        """
        sql, args = self._compile_query(query, params)

        async with self._acquire_conn() as conn:
            row = await conn.fetchrow(sql, *args)
            return dict(row) if row is not None else None

    async def fetch_all(
        self,
        query: str,
        params: Optional[Mapping[str, Any]] = None,
    ) -> Sequence[Mapping[str, Any]]:
        """
        SELECT, der alle Datensätze als Liste von Dicts zurückgibt.
        """
        sql, args = self._compile_query(query, params)

        async with self._acquire_conn() as conn:
            rows = await conn.fetch(sql, *args)
            return [dict(r) for r in rows]

    async def execute(
        self,
        query: str,
        params: Optional[Mapping[str, Any]] = None,
    ) -> str:
        """
        INSERT/UPDATE/DELETE – gibt das Ergebnis-Tag von asyncpg zurück.
        """
        sql, args = self._compile_query(query, params)

        async with self._acquire_conn() as conn:
            result = await conn.execute(sql, *args)
            return result

    async def execute_many(
        self,
        query: str,
        params_seq: Sequence[Mapping[str, Any]],
    ) -> None:
        """
        Mehrere Execute-Aufrufe innerhalb einer Transaktion.
        """
        if not params_seq:
            return

        sql_template = query
        pool = self._ensure_pool()

        async with pool.acquire() as conn:
            async with conn.transaction():
                for params in params_seq:
                    sql, args = self._compile_query(sql_template, params)
                    await conn.execute(sql, *args)

    # ------------------------------------------------------------------ #
    # Transaktionen – für komplexere Use-Cases
    # ------------------------------------------------------------------ #

    class _TransactionContext:
        def __init__(self, conn: asyncpg.Connection):
            self._conn = conn
            self._trx: Optional[asyncpg.Transaction] = None

        async def __aenter__(self) -> asyncpg.Connection:
            self._trx = self._conn.transaction()
            await self._trx.__aenter__()
            return self._conn

        async def __aexit__(self, exc_type, exc, tb) -> None:
            assert self._trx is not None
            await self._trx.__aexit__(exc_type, exc, tb)

    async def transaction(self) -> AsyncIterator[asyncpg.Connection]:
        """
        Async-Context-Manager für manuelle Transaktionen:

            async with db.transaction() as conn:
                await conn.execute(...)
                await conn.execute(...)

        ACHTUNG: Hier arbeitest du direkt mit asyncpg.Connection.
        """
        pool = self._ensure_pool()
        conn = await pool.acquire()
        try:
            async with self._TransactionContext(conn) as trx_conn:
                yield trx_conn
        finally:
            await pool.release(conn)

    # ------------------------------------------------------------------ #
    # Intern: Pool / Param-Rewriting
    # ------------------------------------------------------------------ #

    def _ensure_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError(
                "Database-Pool ist noch nicht initialisiert. "
                "Hast du Database.connect() im Startup aufgerufen?"
            )
        return self._pool

    def _compile_query(
        self,
        query: str,
        params: Optional[Mapping[str, Any]],
    ) -> Tuple[str, List[Any]]:
        """
        Wandelt :named_parameter in $1, $2, ... um und liefert
        (compiled_sql, args_list) zurück.
        """
        if not params:
            return query, []

        used_keys: List[str] = []

        def replacer(match: re.Match) -> str:
            key = match.group(1)
            if key not in params:
                raise KeyError(f"Missing query parameter: {key}")

            if key not in used_keys:
                used_keys.append(key)
            index = used_keys.index(key) + 1  # asyncpg ist 1-basiert: $1, $2, ...

            return f"${index}"

        compiled = _PARAM_PATTERN.sub(replacer, query)
        args = [params[k] for k in used_keys]
        return compiled, args

    class _ConnectionContext:
        """
        Kleiner Context-Manager um pool.acquire()/release() zu kapseln.
        """

        def __init__(self, pool: asyncpg.Pool):
            self._pool = pool
            self._conn: Optional[asyncpg.Connection] = None

        async def __aenter__(self) -> asyncpg.Connection:
            self._conn = await self._pool.acquire()
            return self._conn

        async def __aexit__(self, exc_type, exc, tb) -> None:
            assert self._conn is not None
            await self._pool.release(self._conn)

    def _acquire_conn(self) -> "Database._ConnectionContext":
        pool = self._ensure_pool()
        return Database._ConnectionContext(pool)
