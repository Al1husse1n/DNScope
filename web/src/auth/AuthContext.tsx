import React, { createContext, useEffect, useState } from 'react';

const STORAGE_KEY = 'dnscope.api_key';

export interface AuthContextType {
  rawKey: string | null;
  setRawKey: (k: string) => void;
  clearKey: () => void;
}

// eslint-disable-next-line react-refresh/only-export-components
export const AuthContext = createContext<AuthContextType>({
  rawKey: null,
  setRawKey: () => {},
  clearKey: () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [rawKey, setRawKeyState] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEY);
  });

  const setRawKey = (key: string) => {
    localStorage.setItem(STORAGE_KEY, key);
    setRawKeyState(key);
  };

  const clearKey = () => {
    localStorage.removeItem(STORAGE_KEY);
    setRawKeyState(null);
  };

  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) {
        setRawKeyState(e.newValue);
      }
    };
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  return (
    <AuthContext.Provider value={{ rawKey, setRawKey, clearKey }}>{children}</AuthContext.Provider>
  );
};
