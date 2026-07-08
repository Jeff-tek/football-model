import os
from datetime import datetime, timezone
from sqlalchemy import (create_engine, String, Float, Boolean, DateTime,
                        Integer, UniqueConstraint, Index)
from sqlalchemy.orm import (DeclarativeBase, Mapped, mapped_column, sessionmaker)
from sqlalchemy.dialects.postgresql import insert as pg_insert
try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass

engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def _now():
    return datetime.now(timezone.utc)


class Match(Base):
    __tablename__ = "matches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    understat_match_id: Mapped[str] = mapped_column(String, nullable=False)
    league: Mapped[str] = mapped_column(String, nullable=False)
    season: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    home_team: Mapped[str] = mapped_column(String, nullable=False)
    away_team: Mapped[str] = mapped_column(String, nullable=False)
    home_goals: Mapped[float | None] = mapped_column(Float)
    away_goals: Mapped[float | None] = mapped_column(Float)
    home_xg: Mapped[float | None] = mapped_column(Float)
    away_xg: Mapped[float | None] = mapped_column(Float)
    home_ppda: Mapped[float | None] = mapped_column(Float)
    away_ppda: Mapped[float | None] = mapped_column(Float)
    played: Mapped[bool] = mapped_column(Boolean, default=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    __table_args__ = (
        UniqueConstraint("understat_match_id", name="uq_match_understat_id"),
        Index("ix_match_league_season", "league", "season"),
        Index("ix_match_date", "date"),
    )


class TeamMatch(Base):
    __tablename__ = "team_matches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[str] = mapped_column(String, nullable=False)
    team: Mapped[str | None] = mapped_column(String)
    league: Mapped[str | None] = mapped_column(String)
    season: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[str] = mapped_column(String, nullable=False)
    venue: Mapped[str | None] = mapped_column(String)
    opponent: Mapped[str] = mapped_column(String, nullable=False)
    gf: Mapped[int | None] = mapped_column(Integer)
    ga: Mapped[int | None] = mapped_column(Integer)
    result: Mapped[str | None] = mapped_column(String)
    xg_for: Mapped[float | None] = mapped_column(Float)
    xg_against: Mapped[float | None] = mapped_column(Float)
    ppda: Mapped[float | None] = mapped_column(Float)
    possession: Mapped[float | None] = mapped_column(Float)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    __table_args__ = (
        UniqueConstraint("team_id", "date", "opponent", name="uq_teammatch"),
        Index("ix_teammatch_team_date", "team_id", "date"),
    )


class Standing(Base):
    __tablename__ = "standings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    league: Mapped[str] = mapped_column(String, nullable=False)
    season: Mapped[str] = mapped_column(String, nullable=False)
    team: Mapped[str] = mapped_column(String, nullable=False)
    team_id: Mapped[str | None] = mapped_column(String)
    rank: Mapped[int | None] = mapped_column(Integer)
    matches_played: Mapped[int | None] = mapped_column(Integer)
    xg_for: Mapped[float | None] = mapped_column(Float)
    xg_against: Mapped[float | None] = mapped_column(Float)
    xga_per_game: Mapped[float | None] = mapped_column(Float)
    points: Mapped[int | None] = mapped_column(Integer)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    __table_args__ = (
        UniqueConstraint("league", "season", "team", name="uq_standing_team"),
        Index("ix_standing_league_season", "league", "season"),
    )


class LeagueDistribution(Base):
    __tablename__ = "league_distributions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    league: Mapped[str] = mapped_column(String, nullable=False)
    season: Mapped[str] = mapped_column(String, nullable=False)
    field: Mapped[str] = mapped_column(String, nullable=False)
    mean: Mapped[float | None] = mapped_column(Float)
    std: Mapped[float | None] = mapped_column(Float)
    n: Mapped[int | None] = mapped_column(Integer)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    __table_args__ = (UniqueConstraint("league", "season", "field", name="uq_dist_field"),)


class Injury(Base):
    __tablename__ = "injuries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    league: Mapped[str] = mapped_column(String, nullable=False)
    team: Mapped[str] = mapped_column(String, nullable=False)
    player: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str | None] = mapped_column(String)
    chance_of_playing: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("team", "player", name="uq_injury_team_player"),)


class Manager(Base):
    __tablename__ = "managers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    appointed_on: Mapped[str | None] = mapped_column(String)
    is_caretaker: Mapped[bool] = mapped_column(Boolean, default=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("team", "name", name="uq_manager_team_name"),)


class Odds(Base):
    __tablename__ = "odds"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    understat_match_id: Mapped[str | None] = mapped_column(String)
    market: Mapped[str] = mapped_column(String)
    selection: Mapped[str] = mapped_column(String)
    decimal_odds: Mapped[float] = mapped_column(Float)
    bookmaker: Mapped[str] = mapped_column(String)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (Index("ix_odds_match_market", "understat_match_id", "market"),)


def init_db():
    Base.metadata.create_all(engine)


def _upsert(model, rows, index_elements, update_cols):
    if not rows:
        return
    with SessionLocal() as s:
        for r in rows:
            payload = {c.name: r[c.name] for c in model.__table__.columns if c.name in r}
            if "updated_at" in model.__table__.columns.keys():
                payload.setdefault("updated_at", _now())
            stmt = pg_insert(model).values(**payload)
            stmt = stmt.on_conflict_do_update(
                index_elements=index_elements,
                set_={c: getattr(stmt.excluded, c) for c in update_cols if c in payload})
            s.execute(stmt)
        s.commit()


def upsert_matches(rows):
    _upsert(Match, rows, ["understat_match_id"],
            ["home_goals", "away_goals", "home_xg", "away_xg",
             "home_ppda", "away_ppda", "played", "updated_at"])


def upsert_team_matches(rows):
    _upsert(TeamMatch, rows, ["team_id", "date", "opponent"],
            ["venue", "gf", "ga", "result", "xg_for", "xg_against",
             "ppda", "possession", "team", "league", "updated_at"])


def upsert_standings(rows):
    _upsert(Standing, rows, ["league", "season", "team"],
            ["team_id", "rank", "matches_played", "xg_for", "xg_against",
             "xga_per_game", "points", "updated_at"])


def upsert_distribution(league, season, field, dist):
    with SessionLocal() as s:
        stmt = pg_insert(LeagueDistribution).values(
            league=league, season=season, field=field,
            mean=dist["mean"], std=dist["std"], n=dist["n"], computed_at=_now())
        stmt = stmt.on_conflict_do_update(
            index_elements=["league", "season", "field"],
            set_={"mean": stmt.excluded.mean, "std": stmt.excluded.std,
                  "n": stmt.excluded.n, "computed_at": stmt.excluded.computed_at})
        s.execute(stmt); s.commit()


def get_distribution(league, season, field):
    with SessionLocal() as s:
        row = s.query(LeagueDistribution).filter_by(
            league=league, season=season, field=field).one_or_none()
        return {"mean": row.mean, "std": row.std, "n": row.n} if row else None


def upsert_injuries(rows, replace_source=None):
    if replace_source:
        with SessionLocal() as s:
            s.query(Injury).filter(Injury.source == replace_source).delete()
            s.commit()
    _upsert(Injury, rows, ["team", "player"],
            ["status", "chance_of_playing", "league", "source", "scraped_at"])


def upsert_managers(rows):
    _upsert(Manager, rows, ["team", "name"],
            ["appointed_on", "is_caretaker", "scraped_at"])


def team_matchlog(team_id, before_date=None, limit=10):
    with SessionLocal() as s:
        q = s.query(TeamMatch).filter(TeamMatch.team_id == team_id)
        if before_date:
            q = q.filter(TeamMatch.date < before_date)
        return list(reversed(q.order_by(TeamMatch.date.desc()).limit(limit).all()))


def opponent_form_as_of(team_id, as_of_date, last_n=5):
    rows = team_matchlog(team_id, before_date=as_of_date, limit=last_n)
    if not rows:
        return {"form": None, "xga_trend": None, "n": 0}
    form = "".join((m.result or "")[:1] for m in rows)
    xgas = [m.xg_against for m in rows if m.xg_against is not None]
    return {"form": form, "xga_trend": (sum(xgas) / len(xgas)) if xgas else None,
            "n": len(rows)}
