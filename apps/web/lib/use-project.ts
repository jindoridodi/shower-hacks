"use client";

import { useCallback, useEffect, useState } from "react";
import { type Project, ApiError, createProject, getProject } from "./api";

const STORAGE_KEY = "freakypeeky-current-project";

function loadProjectId(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function saveProjectId(id: string | null) {
  try {
    if (id) localStorage.setItem(STORAGE_KEY, id);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {}
}

export function useProject() {
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const id = loadProjectId();
    if (!id) {
      setLoading(false);
      return;
    }
    getProject(id)
      .then((p) => setProject(p))
      .catch(() => {
        saveProjectId(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const create = useCallback(async (name: string, description?: string) => {
    setError(null);
    try {
      const p = await createProject(name, description);
      setProject(p);
      saveProjectId(p.id);
      return p;
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "failed to create project";
      setError(message);
      return null;
    }
  }, []);

  const clear = useCallback(() => {
    setProject(null);
    saveProjectId(null);
  }, []);

  return { project, loading, error, create, clear };
}
