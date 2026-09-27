"use client";

import { useCallback, useEffect, useState } from "react";
import { createProject, type Project } from "./api";

const STORAGE_KEY = "freakypeeky-project";

export function useProject() {
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) setProject(JSON.parse(stored));
    } finally {
      setLoading(false);
    }
  }, []);

  const create = useCallback(async (name: string) => {
    const created = await createProject(name);
    setProject(created);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(created));
    return created;
  }, []);

  const clear = useCallback(() => {
    setProject(null);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return { project, loading, create, clear };
}
