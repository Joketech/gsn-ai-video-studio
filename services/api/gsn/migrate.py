"""Initial schema migration. Future schema changes require explicit versioned migrations."""
from .db import Base, engine

if __name__ == '__main__':
    Base.metadata.create_all(engine)
    print('Phase 1 initial schema ready')
