import { useEffect, useMemo, useState } from "react";

import { api } from "./api";
import type { ResultRow, ScanStatus, Settings, Target } from "./types";

type Tab = "dashboard" | "targets" | "results" | "settings";

const DEFAULT_SETTINGS: Settings = {
  general_discord_webhook: "",
  failed_discord_webhook: "",
  scan_interval_seconds: "3600",
  video_extensions: ".mp4,.mkv,.avi,.mov,.flv,.wmv",
};

export default function App() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [targets, setTargets] = useState<Target[]>([]);
  const [results, setResults] = useState<ResultRow[]>([]);
  const [scanStatus, setScanStatus] = useState<ScanStatus>({
    running: false,
    last_started: null,
    last_completed: null,
    last_summary: {},
  });
  const [summary, setSummary] = useState<Record<string, Record<string, number>>>({});
  const [newLabel, setNewLabel] = useState("");
  const [newPath, setNewPath] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [browserOpen, setBrowserOpen] = useState(false);
  const [browserPath, setBrowserPath] = useState("/media");
  const [browserDirs, setBrowserDirs] = useState<{ name: string; path: string }[]>([]);
  const [browserParent, setBrowserParent] = useState("/media");

  async function refreshAll() {
    const [settingsData, targetsData, resultsData, statusData, summaryData] = await Promise.all([
      api.getSettings(),
      api.getTargets(),
      api.getResults(),
      api.getScanStatus(),
      api.getSummary(),
    ]);
    setSettings({ ...DEFAULT_SETTINGS, ...settingsData });
    setTargets(targetsData);
    setResults(resultsData);
    setScanStatus(statusData);
    setSummary(summaryData.by_target || {});
  }

  useEffect(() => {
    refreshAll().catch(() => setMessage("Failed to load data"));
    const interval = setInterval(() => {
      api.getScanStatus().then(setScanStatus).catch(() => undefined);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const errorCount = useMemo(
    () => results.filter((item) => item.status !== "OK").length,
    [results]
  );
  const hasMediaTarget = useMemo(
    () => targets.some((target) => target.path === "/media" || target.path.startsWith("/media/")),
    [targets]
  );
  const showMediaWarning = targets.length === 0 || !hasMediaTarget;

  async function saveSettings() {
    setSaving(true);
    setMessage("");
    try {
      await api.updateSettings({
        general_discord_webhook: settings.general_discord_webhook,
        failed_discord_webhook: settings.failed_discord_webhook,
        scan_interval_seconds: Number(settings.scan_interval_seconds || "3600"),
        video_extensions: settings.video_extensions,
      });
      setMessage("Settings saved");
      await refreshAll();
    } catch {
      setMessage("Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  async function addTarget() {
    if (!newLabel.trim() || !newPath.trim()) {
      return;
    }
    await api.createTarget({ label: newLabel.trim(), path: newPath.trim(), enabled: true });
    setNewLabel("");
    setNewPath("");
    await refreshAll();
  }

  async function toggleTarget(target: Target) {
    await api.updateTarget(target.id, {
      label: target.label,
      path: target.path,
      enabled: !target.enabled,
    });
    await refreshAll();
  }

  async function removeTarget(id: number) {
    await api.deleteTarget(id);
    await refreshAll();
  }

  async function runScan() {
    await api.triggerScan();
    setMessage("Scan trigger submitted");
    setTimeout(() => {
      refreshAll().catch(() => undefined);
    }, 2000);
  }

  async function openBrowser(path = "/media") {
    try {
      const data = await api.browseTargets(path);
      setBrowserPath(data.path);
      setBrowserParent(data.parent);
      setBrowserDirs(data.directories);
      setBrowserOpen(true);
    } catch {
      setMessage("Unable to browse folders. Check /media mount and permissions.");
    }
  }

  return (
    <div className="page">
      <header className="header">
        <h1>Video Error Checker</h1>
        <button onClick={runScan} disabled={scanStatus.running}>
          {scanStatus.running ? "Scan Running" : "Run Scan Now"}
        </button>
      </header>

      <nav className="tabs">
        <button className={tab === "dashboard" ? "active" : ""} onClick={() => setTab("dashboard")}>Dashboard</button>
        <button className={tab === "targets" ? "active" : ""} onClick={() => setTab("targets")}>Scan Targets</button>
        <button className={tab === "results" ? "active" : ""} onClick={() => setTab("results")}>Results</button>
        <button className={tab === "settings" ? "active" : ""} onClick={() => setTab("settings")}>Settings</button>
      </nav>

      {message ? <p className="message">{message}</p> : null}
      {showMediaWarning ? (
        <p className="warning">
          Add at least one scan target under /media (for example: /media/tv or /media/movies).
        </p>
      ) : null}

      {tab === "dashboard" && (
        <section className="card-grid">
          <div className="card">
            <h3>Total Results</h3>
            <p>{results.length}</p>
          </div>
          <div className="card">
            <h3>Errors</h3>
            <p>{errorCount}</p>
          </div>
          <div className="card">
            <h3>Last Completed</h3>
            <p>{scanStatus.last_completed || "Never"}</p>
          </div>
          <div className="card full">
            <h3>Per Target Summary</h3>
            <pre>{JSON.stringify(summary, null, 2)}</pre>
          </div>
        </section>
      )}

      {tab === "targets" && (
        <section className="card">
          <h3>Add Target</h3>
          <div className="row">
            <input value={newLabel} onChange={(e) => setNewLabel(e.target.value)} placeholder="Label (e.g. TV)" />
            <input value={newPath} onChange={(e) => setNewPath(e.target.value)} placeholder="Path (e.g. /media/tv)" />
            <div className="row-actions">
              <button onClick={() => openBrowser(newPath || "/media")}>Browse</button>
              <button onClick={addTarget}>Add</button>
            </div>
          </div>
          {browserOpen ? (
            <div className="browser">
              <div className="browser-header">
                <strong>{browserPath}</strong>
                <div className="row-actions">
                  <button onClick={() => openBrowser(browserParent)}>Up</button>
                  <button
                    onClick={() => {
                      setNewPath(browserPath);
                      setBrowserOpen(false);
                    }}
                  >
                    Use This Folder
                  </button>
                  <button onClick={() => setBrowserOpen(false)}>Close</button>
                </div>
              </div>
              <div className="browser-list">
                {browserDirs.length === 0 ? (
                  <p>No subfolders found.</p>
                ) : (
                  browserDirs.map((directory) => (
                    <button key={directory.path} onClick={() => openBrowser(directory.path)}>
                      {directory.name}
                    </button>
                  ))
                )}
              </div>
            </div>
          ) : null}
          <table>
            <thead>
              <tr>
                <th>Label</th>
                <th>Path</th>
                <th>Enabled</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {targets.map((target) => (
                <tr key={target.id}>
                  <td>{target.label}</td>
                  <td>{target.path}</td>
                  <td>{String(target.enabled)}</td>
                  <td>
                    <button onClick={() => toggleTarget(target)}>
                      {target.enabled ? "Disable" : "Enable"}
                    </button>
                    <button onClick={() => removeTarget(target.id)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {tab === "results" && (
        <section className="card">
          <h3>Recent Results</h3>
          <table>
            <thead>
              <tr>
                <th>Target</th>
                <th>File</th>
                <th>Status</th>
                <th>Duration (s)</th>
                <th>Scanned At</th>
              </tr>
            </thead>
            <tbody>
              {results.map((result) => (
                <tr key={result.id}>
                  <td>{result.label}</td>
                  <td className="path">{result.file_path}</td>
                  <td className={result.status === "OK" ? "ok" : "error"}>{result.status}</td>
                  <td>{result.scan_duration_seconds.toFixed(2)}</td>
                  <td>{result.scanned_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {tab === "settings" && (
        <section className="card form">
          <label>
            General Discord Webhook
            <input
              value={settings.general_discord_webhook}
              onChange={(e) =>
                setSettings((prev) => ({ ...prev, general_discord_webhook: e.target.value }))
              }
            />
          </label>
          <label>
            Failed Check Webhook
            <input
              value={settings.failed_discord_webhook}
              onChange={(e) =>
                setSettings((prev) => ({ ...prev, failed_discord_webhook: e.target.value }))
              }
            />
          </label>
          <label>
            Scan Interval Seconds
            <input
              value={settings.scan_interval_seconds}
              onChange={(e) =>
                setSettings((prev) => ({ ...prev, scan_interval_seconds: e.target.value }))
              }
            />
          </label>
          <label>
            Video Extensions (comma separated)
            <input
              value={settings.video_extensions}
              onChange={(e) =>
                setSettings((prev) => ({ ...prev, video_extensions: e.target.value }))
              }
            />
          </label>
          <button onClick={saveSettings} disabled={saving}>
            {saving ? "Saving..." : "Save Settings"}
          </button>
        </section>
      )}
    </div>
  );
}
