"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const CORE_API_URL = process.env.NEXT_PUBLIC_CORE_API_URL || "http://localhost:8000";

export interface Option {
  id: number;
  label: string;
  value: number;
  extra?: { code?: string; displacement?: number; fuel?: string; power_hp?: number };
}

export interface VehicleState {
  make: Option | null;
  model: Option | null;
  year: number | null;
  engine: Option | null;
}

export function useVehicleSelector() {
  const [vehicle, setVehicle] = useState<VehicleState>({
    make: null,
    model: null,
    year: null,
    engine: null,
  });

  const [options, setOptions] = useState<{
    makes: Option[];
    models: Option[];
    years: Option[];
    engines: Option[];
  }>({
    makes: [],
    models: [],
    years: [],
    engines: [],
  });

  const [loading, setLoading] = useState({
    makes: false,
    models: false,
    years: false,
    engines: false,
  });

  const [errors, setErrors] = useState({
    makes: "",
    models: "",
    years: "",
    engines: "",
  });

  const cache = useRef<Record<string, Option[]>>({});

  const fetchWithCache = useCallback(async (url: string, key: string): Promise<Option[]> => {
    if (cache.current[key]) return cache.current[key];
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data && typeof data === "object" && "error" in data && data.error === "catalog_empty") {
      throw new Error("Каталог не загружен");
    }
    if (!Array.isArray(data)) throw new Error("Неверный формат ответа");
    cache.current[key] = data;
    return data;
  }, []);

  useEffect(() => {
    setLoading((l) => ({ ...l, makes: true }));
    setErrors((e) => ({ ...e, makes: "" }));
    fetchWithCache(`${CORE_API_URL}/api/vehicle/makes?limit=200`, "makes")
      .then((data) => {
        setOptions((o) => ({ ...o, makes: data }));
      })
      .catch((err) => {
        setErrors((e) => ({
          ...e,
          makes:
            err.message === "Каталог не загружен"
              ? "Каталог авто не загружен. Обратитесь к администратору."
              : "Не удалось загрузить список марок. Попробуйте обновить страницу.",
        }));
      })
      .finally(() => setLoading((l) => ({ ...l, makes: false })));
  }, [fetchWithCache]);

  const selectMake = useCallback(
    async (make: Option | null) => {
      setVehicle({ make, model: null, year: null, engine: null });
      setOptions((o) => ({ ...o, models: [], years: [], engines: [] }));
      if (!make) return;

      setLoading((l) => ({ ...l, models: true }));
      setErrors((e) => ({ ...e, models: "" }));
      fetchWithCache(
        `${CORE_API_URL}/api/vehicle/models?make_id=${make.id}&limit=200`,
        `models_${make.id}`
      )
        .then((data) => setOptions((o) => ({ ...o, models: data })))
        .catch(() =>
          setErrors((e) => ({ ...e, models: "Не удалось загрузить модели для этой марки." }))
        )
        .finally(() => setLoading((l) => ({ ...l, models: false })));
    },
    [fetchWithCache]
  );

  const selectModel = useCallback(
    async (model: Option | null) => {
      setVehicle((v) => ({ ...v, model, year: null, engine: null }));
      setOptions((o) => ({ ...o, years: [], engines: [] }));
      if (!model) return;

      setLoading((l) => ({ ...l, years: true }));
      setErrors((e) => ({ ...e, years: "" }));
      fetchWithCache(`${CORE_API_URL}/api/vehicle/years?model_id=${model.id}`, `years_${model.id}`)
        .then((data) => setOptions((o) => ({ ...o, years: data })))
        .catch(() =>
          setErrors((e) => ({ ...e, years: "Не удалось загрузить годы выпуска." }))
        )
        .finally(() => setLoading((l) => ({ ...l, years: false })));
    },
    [fetchWithCache]
  );

  const selectYear = useCallback((year: number | null) => {
    setVehicle((v) => ({ ...v, year, engine: null }));
    setOptions((o) => ({ ...o, engines: [] }));
  }, []);

  // Загрузка двигателей при выборе года и модели
  useEffect(() => {
    const modelId = vehicle.model?.id;
    const year = vehicle.year;
    if (!modelId || !year) return;

    setLoading((l) => ({ ...l, engines: true }));
    setErrors((e) => ({ ...e, engines: "" }));
    fetchWithCache(
      `${CORE_API_URL}/api/vehicle/engines?model_id=${modelId}&year=${year}`,
      `engines_${modelId}_${year}`
    )
      .then((data) => setOptions((o) => ({ ...o, engines: data })))
      .catch(() =>
        setErrors((e) => ({ ...e, engines: "Не удалось загрузить список двигателей." }))
      )
      .finally(() => setLoading((l) => ({ ...l, engines: false })));
  }, [vehicle.model?.id, vehicle.year, fetchWithCache]);

  const selectEngine = useCallback((engine: Option | null) => {
    setVehicle((v) => ({ ...v, engine }));
  }, []);

  return {
    vehicle,
    options,
    loading,
    errors,
    selectMake,
    selectModel,
    selectYear,
    selectEngine,
  };
}
