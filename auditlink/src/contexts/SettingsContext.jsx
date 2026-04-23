import { createContext, useContext, useState, useEffect, useCallback } from "react";
import api from "../api";

const SettingsContext = createContext(null);

const STORAGE_KEY = "auditlink_settings";
const DEFAULTS = {
  activeFY: "FY2025",
  userName: "",
  userTitle: "",
  userFirm: "",
};

export function SettingsProvider({ children }) {
  const [settings, setSettings] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? { ...DEFAULTS, ...JSON.parse(stored) } : DEFAULTS;
    } catch { return DEFAULTS; }
  });

  // Load from API on mount
  useEffect(() => {
    api.getSettings().then((apiSettings) => {
      if (apiSettings && Object.keys(apiSettings).length) {
        const parsed = {};
        for (const [k, v] of Object.entries(apiSettings)) {
          try { parsed[k] = JSON.parse(v); } catch { parsed[k] = v; }
        }
        setSettings((prev) => ({ ...prev, ...parsed }));
      }
    }).catch(() => {});
  }, []);

  // Persist to localStorage whenever settings change
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(settings)); } catch {}
  }, [settings]);

  const updateSettings = useCallback((patch) => {
    setSettings((prev) => ({ ...prev, ...patch }));
  }, []);

  return (
    <SettingsContext.Provider value={{ settings, updateSettings }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error("useSettings must be used within SettingsProvider");
  return ctx;
}
