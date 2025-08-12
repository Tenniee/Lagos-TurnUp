from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context
from app.core.database import Base

# --- Logging setup ---
if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)

# --- Target metadata for autogenerate ---
target_metadata = Base.metadata

# --- Database URL (no configparser interpolation) ---
db_url = (
    "mysql+pymysql://teniola-b8a0e:92%29v9urhUh6dGM3H4%40hF~@"
    "svc-3482219c-a389-4079-b18b-d50662524e8a-shared-dml.aws-virginia-6.svc.singlestore.com:3333/"
    "db_82eda"
    "?ssl_ca=C:/Users/H%20P/Desktop/LagosTurnUp/certs/lagos-cert.pem"
)

# --- Migration runners ---
def run_migrations_offline():
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = create_engine(db_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

# --- Entrypoint ---
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
