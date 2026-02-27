"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export interface SelectOption {
  id: number;
  label: string;
  value: number;
  extra?: Record<string, unknown>;
}

type CustomSelectProps = {
  options: SelectOption[];
  value: SelectOption | null;
  placeholder: string;
  disabled?: boolean;
  loading?: boolean;
  onChange: (opt: SelectOption | null) => void;
};

export function CustomSelect({
  options,
  value,
  placeholder,
  disabled,
  loading,
  onChange,
}: CustomSelectProps) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0, width: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const handleClickOutside = useCallback((e: MouseEvent) => {
    const target = e.target as Node;
    const inTrigger = containerRef.current?.contains(target);
    const inDropdown = dropdownRef.current?.contains(target);
    if (!inTrigger && !inDropdown) {
      setOpen(false);
    }
  }, []);

  const updatePosition = useCallback(() => {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPosition({
        top: rect.bottom + 8,
        left: rect.left,
        width: rect.width,
      });
    }
  }, []);

  useLayoutEffect(() => {
    if (open && triggerRef.current) {
      updatePosition();
      window.addEventListener("scroll", updatePosition, true);
      window.addEventListener("resize", updatePosition);
      return () => {
        window.removeEventListener("scroll", updatePosition, true);
        window.removeEventListener("resize", updatePosition);
      };
    }
  }, [open, updatePosition]);

  useEffect(() => {
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open, handleClickOutside]);

  const handleSelect = useCallback(
    (opt: SelectOption | null) => {
      onChange(opt);
      setOpen(false);
    },
    [onChange]
  );

  const dropdownContent = open && (
    <div
      ref={dropdownRef}
      className="custom-select-dropdown fixed z-[9999] max-h-56 overflow-auto rounded-xl py-1 backdrop-blur-xl"
      style={{
        top: position.top,
        left: position.left,
        width: Math.max(position.width, 160),
        background: "var(--select-dropdown-bg)",
        border: "1px solid var(--select-dropdown-border)",
        boxShadow: "0 16px 48px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.06)",
      }}
    >
          <button
            type="button"
            onClick={() => handleSelect(null)}
            className="custom-select-option custom-select-placeholder w-full px-4 py-2.5 text-left text-sm"
          >
            {placeholder}
          </button>
          {options.length > 0 && <div className="mx-3 my-0.5 border-b border-white/8" role="separator" />}
          {options.map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => handleSelect(opt)}
              className="custom-select-option w-full px-4 py-2.5 text-left text-sm font-medium"
              style={{
                color: "var(--select-option-text)",
                background: value?.id === opt.id ? "var(--select-option-selected)" : "transparent",
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      );

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => {
          if (!disabled && !loading) {
            if (triggerRef.current) {
              const rect = triggerRef.current.getBoundingClientRect();
              setPosition({ top: rect.bottom + 8, left: rect.left, width: rect.width });
            }
            setOpen((o) => !o);
          }
        }}
        disabled={disabled || loading}
        className="custom-select-trigger relative w-full min-w-0 text-left text-sm disabled:cursor-not-allowed disabled:opacity-50"
        style={{
          color: value ? "var(--fg)" : "var(--muted)",
          boxShadow: open ? "0 0 0 1px rgba(255,255,255,0.15)" : undefined,
        }}
      >
        <span className="block truncate pr-8">{value ? value.label : placeholder}</span>
        <span
          className="pointer-events-none absolute inset-y-0 right-3 flex items-center opacity-60"
          aria-hidden
        >
          <svg
            className={`h-4 w-4 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </span>
      </button>

      {typeof document !== "undefined" &&
        createPortal(
          dropdownContent,
          document.body
        )}

      {loading && (
        <div
          className="absolute inset-0 flex items-center justify-center rounded-xl"
          style={{ background: "rgba(255,255,255,0.02)" }}
        >
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-t-transparent" style={{ borderColor: "var(--border)" }} />
        </div>
      )}
    </div>
  );
}
