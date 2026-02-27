#!/usr/bin/env python3
"""
Импорт каталога авто из CSV в БД.

Использование (из корня проекта):
    python scripts/import_vehicle_catalog.py
    python scripts/import_vehicle_catalog.py --file demo-data/vehicle_catalog.csv
    python scripts/import_vehicle_catalog.py --clear

Требуется DATABASE_URL или ASYNC_DATABASE_URL в окружении (например из .env).
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import os
import sys
from pathlib import Path

# Путь к app: при scripts/import_vehicle_catalog.py -> services/core-api;
# при /scripts/import_vehicle_catalog.py (Docker) -> /app
_script_dir = Path(__file__).resolve().parent
_suggested = _script_dir.parent / "services" / "core-api"
if Path("/app/app").is_dir():  # Docker
    CORE_API = Path("/app")
elif _suggested.is_dir():
    CORE_API = _suggested
elif (_script_dir.parent / "app").is_dir():  # script in services/core-api/scripts/
    CORE_API = _script_dir.parent
else:
    CORE_API = Path("/app")
sys.path.insert(0, str(CORE_API))
os.chdir(CORE_API)


async def import_catalog(filepath: str, clear: bool = False) -> None:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.session import AsyncSessionLocal
    from app.models import VehicleMake, VehicleModel, VehicleEngine

    makes_cache: dict[str, VehicleMake] = {}
    models_cache: dict[str, VehicleModel] = {}
    imported = {"makes": 0, "models": 0, "engines": 0}

    async with AsyncSessionLocal() as db:
        try:
            if clear:
                print("Очищаем каталог...")
                from sqlalchemy import delete
                await db.execute(delete(VehicleEngine))
                await db.execute(delete(VehicleModel))
                await db.execute(delete(VehicleMake))
                await db.commit()

            with open(filepath, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    make_slug = row["make_slug"].strip()
                    make_name = row["make"].strip()

                    # UPSERT марки
                    if make_slug not in makes_cache:
                        result = await db.execute(
                            select(VehicleMake).where(VehicleMake.slug == make_slug)
                        )
                        make = result.scalar_one_or_none()
                        if not make:
                            make = VehicleMake(name_ru=make_name, slug=make_slug)
                            db.add(make)
                            await db.flush()
                            imported["makes"] += 1
                        makes_cache[make_slug] = make
                    make = makes_cache[make_slug]

                    model_key = f"{make_slug}_{row['model_slug'].strip()}"
                    model_slug = row["model_slug"].strip()

                    # UPSERT модели
                    if model_key not in models_cache:
                        result = await db.execute(
                            select(VehicleModel).where(
                                VehicleModel.make_id == make.id,
                                VehicleModel.slug == model_slug,
                            )
                        )
                        model = result.scalar_one_or_none()
                        if not model:
                            model = VehicleModel(
                                make_id=make.id,
                                name_ru=row["model"].strip(),
                                slug=model_slug,
                                year_from=int(row["year_from"])
                                if row.get("year_from")
                                else None,
                                year_to=int(row["year_to"]) if row.get("year_to") else None,
                            )
                            db.add(model)
                            await db.flush()
                            imported["models"] += 1
                        models_cache[model_key] = model
                    model = models_cache[model_key]

                    # UPSERT двигателя
                    engine_code = row.get("engine_code", "").strip() or None
                    engine_year_from = (
                        int(row["engine_year_from"])
                        if row.get("engine_year_from")
                        else None
                    )

                    result = await db.execute(
                        select(VehicleEngine).where(
                            VehicleEngine.model_id == model.id,
                            VehicleEngine.code == engine_code,
                            VehicleEngine.year_from == engine_year_from,
                        )
                    )
                    existing_engine = result.scalar_one_or_none()

                    if not existing_engine:
                        engine_obj = VehicleEngine(
                            model_id=model.id,
                            name_ru=row["engine_name"].strip(),
                            code=engine_code,
                            displacement=(
                                float(row["displacement"])
                                if row.get("displacement")
                                else None
                            ),
                            fuel=row.get("fuel", "").strip() or None,
                            power_hp=(
                                int(row["power_hp"]) if row.get("power_hp") else None
                            ),
                            year_from=engine_year_from,
                            year_to=(
                                int(row["engine_year_to"])
                                if row.get("engine_year_to")
                                else None
                            ),
                        )
                        db.add(engine_obj)
                        imported["engines"] += 1

            await db.commit()
            print("Импорт завершён:")
            print(f"   Марок: {imported['makes']}")
            print(f"   Моделей: {imported['models']}")
            print(f"   Двигателей: {imported['engines']}")

        except Exception as e:
            await db.rollback()
            print(f"Ошибка импорта: {e}")
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Импорт каталога авто")
    proj_root = _script_dir.parent.parent if _script_dir.name == "scripts" else _script_dir.parent
    default_csv = "/demo-data/vehicle_catalog.csv" if Path("/demo-data/vehicle_catalog.csv").exists() else str(proj_root / "demo-data" / "vehicle_catalog.csv")
    parser.add_argument(
        "--file",
        default=default_csv,
        help="Путь к CSV файлу",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Очистить каталог перед импортом",
    )
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Файл не найден: {args.file}")
        sys.exit(1)

    # Загружаем .env из корня проекта (опционально)
    proj_root = _script_dir.parent.parent if _script_dir.name == "scripts" else Path(".")
    env_path = proj_root / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except ImportError:
            pass

    asyncio.run(import_catalog(args.file, clear=args.clear))


if __name__ == "__main__":
    main()
