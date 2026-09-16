import os

# Must be set before importing app.main, which creates the SQLAlchemy engine.
os.environ["DATABASE_URL"] = "sqlite:///./test_medtrace.db"
os.environ["JWT_SECRET"] = "test-only-secret"
