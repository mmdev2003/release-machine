import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent.parent.parent))

from infrastructure.pg.pg import PG
from infrastructure.telemetry.telemetry import Telemetry
from internal.config.config import Config
from internal.migration.manager import MigrationManager


async def main():
    cfg = Config()

    tel = Telemetry(
        cfg.log_level,
        cfg.root_path,
        cfg.environment,
        cfg.service_name + "-migration",
        cfg.service_version,
        cfg.otlp_host,
        cfg.otlp_port,
        None
    )

    db = PG(tel, cfg.db_user, cfg.db_pass, cfg.db_host, cfg.db_port, cfg.db_name)
    manager = MigrationManager(db)

    import argparse

    parser = argparse.ArgumentParser(description='Управление миграциями БД')
    parser.add_argument('env', choices=['stage', 'prod'], help='Команда: stage или prod')
    parser.add_argument('--command', choices=['up', 'down'], help='Команда: up или down')
    parser.add_argument('--version', help='Версия миграции (например, v1.0.1)')

    args = parser.parse_args()

    if args.env == "stage":
        if args.command == "down":
            version = args.version
            if not version:
                print("Для нужно указать версию: --version v1.0.1")
                sys.exit(1)
            version = version.replace(".", "_")

            await manager.rollback_to_version(version)
        else:
            await manager.drop_tables()
            await manager.migrate()

    if args.env == "prod":
        if args.command == "up":
            await manager.migrate()

        if args.command == "down":
            version = args.version
            if not version:
                print("Для нужно указать версию: --version v1.0.1")
                sys.exit(1)
            version = version.replace(".", "_")

            await manager.rollback_to_version(version)


if __name__ == "__main__":
    asyncio.run(main())