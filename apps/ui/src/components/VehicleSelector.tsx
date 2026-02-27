"use client";

import { useEffect } from "react";
import { CustomSelect } from "./CustomSelect";
import { useVehicleSelector, type Option, type VehicleState } from "../hooks/useVehicleSelector";

type VehicleSelectorProps = {
  onChange?: (v: VehicleState) => void;
};

export function VehicleSelector({ onChange }: VehicleSelectorProps) {
  const {
    vehicle,
    options,
    loading,
    errors,
    selectMake,
    selectModel,
    selectYear,
    selectEngine,
  } = useVehicleSelector();

  useEffect(() => {
    onChange?.(vehicle);
  }, [vehicle, onChange]);

  return (
    <>
      {/* Марка */}
      <div className="field">
        <label className="mb-1 block text-xs font-medium" style={{ color: "var(--muted)" }}>
          Марка <span className="text-red-400">*</span>
        </label>
        {loading.makes ? (
          <div className="input h-10 animate-pulse rounded-xl" style={{ background: "rgba(255,255,255,0.05)" }} />
        ) : errors.makes ? (
          <p className="text-xs text-red-400">{errors.makes}</p>
        ) : (
          <CustomSelect
            options={options.makes}
            value={vehicle.make}
            placeholder="Выберите марку..."
            onChange={selectMake}
            loading={loading.makes}
          />
        )}
      </div>

      {/* Модель */}
      <div className="field">
        <label className="mb-1 block text-xs font-medium" style={{ color: "var(--muted)" }}>
          Модель <span className="text-red-400">*</span>
        </label>
        {loading.models ? (
          <div className="input h-10 animate-pulse rounded-xl" style={{ background: "rgba(255,255,255,0.05)" }} />
        ) : (
          <CustomSelect
            options={options.models}
            value={vehicle.model}
            placeholder={vehicle.make ? "Выберите модель..." : "Сначала выберите марку"}
            disabled={!vehicle.make}
            onChange={selectModel}
            loading={loading.models}
          />
        )}
        {errors.models && <p className="mt-1 text-xs text-red-400">{errors.models}</p>}
      </div>

      {/* Год */}
      <div className="field">
        <label className="mb-1 block text-xs font-medium" style={{ color: "var(--muted)" }}>
          Год <span className="text-red-400">*</span>
        </label>
        {loading.years ? (
          <div className="input h-10 animate-pulse rounded-xl" style={{ background: "rgba(255,255,255,0.05)" }} />
        ) : (
          <CustomSelect
            options={options.years}
            value={vehicle.year ? { id: vehicle.year, label: String(vehicle.year), value: vehicle.year } : null}
            placeholder={vehicle.model ? "Выберите год..." : "Сначала выберите модель"}
            disabled={!vehicle.model}
            onChange={(opt) => selectYear(opt?.value ?? null)}
            loading={loading.years}
          />
        )}
        {errors.years && <p className="mt-1 text-xs text-red-400">{errors.years}</p>}
      </div>

      {/* Двигатель (опционально) */}
      {(vehicle.year || loading.engines) && (
        <div className="field">
          <label className="mb-1 block text-xs font-medium" style={{ color: "var(--muted)" }}>
            Двигатель <span className="opacity-70">(необязательно)</span>
          </label>
          {loading.engines ? (
            <div className="input h-10 animate-pulse rounded-xl" style={{ background: "rgba(255,255,255,0.05)" }} />
          ) : options.engines.length === 0 ? (
            <div className="input text-sm opacity-70" style={{ cursor: "default" }}>Нет данных</div>
          ) : (
            <CustomSelect
              options={options.engines}
              value={vehicle.engine}
              placeholder="Выберите двигатель..."
              onChange={selectEngine}
              loading={loading.engines}
            />
          )}
          {errors.engines && <p className="mt-1 text-xs text-red-400">{errors.engines}</p>}
        </div>
      )}
    </>
  );
}
