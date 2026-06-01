from app.db.session import get_session_factory, get_engine, Base, init_db, init_db_engine

# Provide lazy-access getters for backward compatibility
def __getattr__(name):
    if name == "SessionLocal":
        return get_session_factory()
    elif name == "engine":
        return get_engine()
    raise AttributeError(f"module 'app.db' has no attribute '{name}'")

__all__ = ["get_session_factory", "get_engine", "Base", "init_db", "init_db_engine"]
