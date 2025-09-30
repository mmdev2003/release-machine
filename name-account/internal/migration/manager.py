import importlib
from pathlib import Path
from typing import Optional

from internal import interface, model
from internal.migration.base import Migration


class MigrationManager:
    def __init__(self, db: interface.IDB):
        print("🔧 MigrationManager: Инициализация...", flush=True)
        self.db = db
        self.migrations = self._load_migrations()
        print(f"✅ MigrationManager: Загружено {len(self.migrations)} миграций", flush=True)

    def _load_migrations(self) -> dict[str, Migration]:
        print("📂 MigrationManager: Загрузка миграций...", flush=True)
        try:
            migrations = {}
            migration_dir = Path(__file__).parent / 'version'
            print(f"📁 MigrationManager: Директория миграций: {migration_dir}", flush=True)

            for file_path in sorted(migration_dir.glob('v*.py')):
                if file_path.stem == '__init__':
                    continue

                print(f"📄 MigrationManager: Обработка файла {file_path.stem}", flush=True)
                module = importlib.import_module(f"internal.migration.version.{file_path.stem}")

                for attr in dir(module):
                    obj = getattr(module, attr)
                    if (isinstance(obj, type) and
                            issubclass(obj, Migration) and
                            obj != Migration):
                        migration = obj()
                        migrations[migration.info.version] = migration
                        print(
                            f"✅ MigrationManager: Добавлена миграция {migration.info.version} - {migration.info.name}",
                            flush=True)
                        break

            print(f"📋 MigrationManager: Все миграции: {list(migrations.keys())}", flush=True)
            return migrations
        except Exception as e:
            print(f"❌ MigrationManager: ОШИБКА загрузки миграций: {e}", flush=True)
            return {}

    async def _ensure_history_table(self):
        print("🗄️  MigrationManager: Проверка таблицы migration_history...", flush=True)
        query = """
                CREATE TABLE IF NOT EXISTS migration_history \
                ( \
                    id
                    SERIAL
                    PRIMARY
                    KEY,
                    version
                    TEXT,
                    name
                    TEXT
                    NOT
                    NULL,
                    applied_at
                    TIMESTAMP
                    DEFAULT
                    CURRENT_TIMESTAMP
                )
                """
        await self.db.multi_query([query])
        print("✅ MigrationManager: Таблица migration_history готова", flush=True)

    async def _get_applied_versions(self) -> set[str]:
        print("🔍 MigrationManager: Получение примененных версий...", flush=True)
        try:
            rows = await self.db.select(
                "SELECT version FROM migration_history ORDER BY version",
                {}
            )
            applied = {row[0] for row in rows}
            print(f"📊 MigrationManager: Применённые версии: {applied if applied else 'нет'}", flush=True)
            return applied
        except Exception as e:
            print(f"ℹ️  MigrationManager: Примененных версий пока нет (таблица не существует?): {e}", flush=True)
            return set()

    async def _mark_applied(self, migration: Migration):
        print(f"💾 MigrationManager: Отметка миграции {migration.info.version} как примененной...", flush=True)
        await self.db.insert(
            "INSERT INTO migration_history (version, name) VALUES (:version, :name) RETURNING id",
            {'version': migration.info.version, 'name': migration.info.name}
        )
        print(f"✅ MigrationManager: Миграция {migration.info.version} отмечена как примененная", flush=True)

    async def _mark_rolled_back(self, version: str):
        print(f"🔙 MigrationManager: Отметка миграции {version} как откаченной...", flush=True)
        await self.db.delete(
            "DELETE FROM migration_history WHERE version = :version",
            {'version': version}
        )
        print(f"✅ MigrationManager: Миграция {version} откачена", flush=True)

    def _version_key(self, version: str) -> tuple:
        key = tuple(map(int, version.lstrip('v').split('_')))
        print(f"🔑 MigrationManager: Ключ версии для {version}: {key}", flush=True)
        return key

    async def migrate(self) -> int:
        print("", flush=True)
        print("═══════════════════════════════════════════════════════════", flush=True)
        print("🚀 MigrationManager: Начало процесса миграции", flush=True)
        print("═══════════════════════════════════════════════════════════", flush=True)
        try:
            await self._ensure_history_table()

            if not self.migrations:
                print("⚠️  MigrationManager: Нет доступных миграций для применения", flush=True)
                return 0

            latest_version = max(self.migrations.keys(), key=self._version_key)
            print(f"🎯 MigrationManager: Последняя доступная версия: {latest_version}", flush=True)

            applied = await self._get_applied_versions()

            # Определяем какие миграции нужно применить
            to_apply = []
            target_key = self._version_key(latest_version)
            print(f"🎯 MigrationManager: Целевой ключ версии: {target_key}", flush=True)

            for version in sorted(self.migrations.keys(), key=self._version_key):
                if (self._version_key(version) <= target_key and
                        version not in applied):
                    to_apply.append(version)
                    print(f"📌 MigrationManager: Будет применена миграция {version}", flush=True)

            if not to_apply:
                print("✅ MigrationManager: Все миграции уже применены, нечего делать", flush=True)
                return 0

            print(f"📊 MigrationManager: Всего миграций к применению: {len(to_apply)}", flush=True)
            print("", flush=True)

            # Применяем миграции по порядку
            count = 0
            for version in to_apply:
                migration = self.migrations[version]
                print(f"⬆️  MigrationManager: Применение миграции {version} ({count + 1}/{len(to_apply)})...",
                      flush=True)

                # Проверяем зависимости
                if migration.info.depends_on and migration.info.depends_on not in applied:
                    print(
                        f"⏭️  MigrationManager: Пропуск {version} - зависимость {migration.info.depends_on} не выполнена",
                        flush=True)
                    continue

                await migration.up(self.db)
                await self._mark_applied(migration)
                applied.add(version)
                count += 1
                print(f"✅ MigrationManager: Миграция {version} успешно применена", flush=True)
                print("", flush=True)

            print("═══════════════════════════════════════════════════════════", flush=True)
            print(f"🎉 MigrationManager: Миграция завершена. Применено {count} миграций", flush=True)
            print("═══════════════════════════════════════════════════════════", flush=True)
            print("", flush=True)
            return count
        except Exception as e:
            print("", flush=True)
            print("═══════════════════════════════════════════════════════════", flush=True)
            print(f"❌ MigrationManager: ОШИБКА во время миграции: {e}", flush=True)
            print("═══════════════════════════════════════════════════════════", flush=True)
            print("", flush=True)
            import traceback
            print(f"🔍 Traceback:\n{traceback.format_exc()}", flush=True)
            return 0

    async def rollback_to_version(self, target_version: Optional[str] = None) -> int:
        print("", flush=True)
        print("═══════════════════════════════════════════════════════════", flush=True)
        print(
            f"🔙 MigrationManager: Начало отката к версии {target_version if target_version else 'начальному состоянию'}",
            flush=True)
        print("═══════════════════════════════════════════════════════════", flush=True)
        try:
            await self._ensure_history_table()
            applied = await self._get_applied_versions()

            if not applied:
                print("ℹ️  MigrationManager: Нет миграций для отката", flush=True)
                return 0

            # Определяем какие миграции откатить
            to_rollback = []

            if target_version is None:
                print("⚠️  MigrationManager: Откат ВСЕХ миграций", flush=True)
                to_rollback = sorted(applied, key=self._version_key, reverse=True)
            else:
                print(f"🎯 MigrationManager: Откат к версии {target_version}", flush=True)
                target_key = self._version_key(target_version)
                for version in sorted(applied, key=self._version_key, reverse=True):
                    if self._version_key(version) > target_key:
                        to_rollback.append(version)
                        print(f"📌 MigrationManager: Будет откачена миграция {version}", flush=True)

            if not to_rollback:
                print("✅ MigrationManager: Нет миграций для отката (уже на целевой версии или ниже)", flush=True)
                return 0

            print(f"📊 MigrationManager: Всего миграций к откату: {len(to_rollback)}", flush=True)
            print("", flush=True)

            # Откатываем миграции в обратном порядке
            count = 0
            for version in to_rollback:
                if version in self.migrations:
                    print(f"⬇️  MigrationManager: Откат миграции {version} ({count + 1}/{len(to_rollback)})...",
                          flush=True)
                    migration = self.migrations[version]
                    await migration.down(self.db)
                    await self._mark_rolled_back(version)
                    count += 1
                    print(f"✅ MigrationManager: Миграция {version} успешно откачена", flush=True)
                    print("", flush=True)
                else:
                    print(
                        f"⚠️  MigrationManager: ПРЕДУПРЕЖДЕНИЕ - Миграция {version} не найдена в загруженных миграциях",
                        flush=True)

            print("═══════════════════════════════════════════════════════════", flush=True)
            print(f"🎉 MigrationManager: Откат завершен. Откачено {count} миграций", flush=True)
            print("═══════════════════════════════════════════════════════════", flush=True)
            print("", flush=True)
            return count
        except Exception as e:
            print("", flush=True)
            print("═══════════════════════════════════════════════════════════", flush=True)
            print(f"❌ MigrationManager: ОШИБКА во время отката: {e}", flush=True)
            print("═══════════════════════════════════════════════════════════", flush=True)
            print("", flush=True)
            import traceback
            print(f"🔍 Traceback:\n{traceback.format_exc()}", flush=True)
            return 0

    async def drop_tables(self):
        print("", flush=True)
        print("═══════════════════════════════════════════════════════════", flush=True)
        print("🗑️  MigrationManager: Удаление всех таблиц...", flush=True)
        print("═══════════════════════════════════════════════════════════", flush=True)
        try:
            drop_migration_history_table = "DROP TABLE IF EXISTS migration_history;"
            await self.db.multi_query([*model.drop_queries, drop_migration_history_table])
            print("✅ MigrationManager: Все таблицы успешно удалены", flush=True)
            print("═══════════════════════════════════════════════════════════", flush=True)
            print("", flush=True)
        except Exception as e:
            print(f"❌ MigrationManager: ОШИБКА удаления таблиц: {e}", flush=True)
            print("═══════════════════════════════════════════════════════════", flush=True)
            print("", flush=True)
            import traceback
            print(f"🔍 Traceback:\n{traceback.format_exc()}", flush=True)