"""Operator-only Solr index recovery command.

Run inside the private backend container:
    docker compose exec backend /app/.venv/bin/python -m stockpile.reindex
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .main import Settings, SolrIndex


def main() -> None:
    settings = Settings.from_environment()
    if not settings.solr_url:
        raise SystemExit("SOLR_URL is not configured")
    engine = create_engine(settings.database_url)
    with sessionmaker(bind=engine)() as session:
        index = SolrIndex(settings.solr_url)
        index.ensure_schema()
        index.reindex(session)
    print("Solr index rebuilt")


if __name__ == "__main__":
    main()
