import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("../", import.meta.url));
const LOG_LINES = 40;
const DATA_DIR = fileURLToPath(new URL("../site_data", import.meta.url));

// Dev-only: adds /__dev/refresh to `astro dev`, which runs the Python export; it never runs in `astro build`
export default function devRefresh() {
  let server;
  // What the one running (or last) job is doing
  let job = { running: false, label: "", exitCode: null, log: [], current: "", done: 0, total: 0 };

  // Start the Python export for a scope: stale games, all games, or one game
  function start(scope, appid) {
    const args = ["run", "python", "src/export.py"];
    if (scope === "all") args.push("--refresh");
    if (scope === "game") args.push("--refresh", String(appid));
    const label = scope === "game" ? `game ${appid}` : scope === "all" ? "all games" : "stale games";
    job = { running: true, label, exitCode: null, log: [], current: "", done: 0, total: 0 };
    // Stop watching site_data while it is rewritten, or every file written reloads the page and closes the dialog
    server.watcher.unwatch(DATA_DIR);
    const child = spawn("uv", args, { cwd: ROOT, env: { ...process.env, PYTHONUNBUFFERED: "1" } });
    const keep = (chunk) => {
      const lines = chunk.toString().split(/\r?\n/).filter(Boolean);
      // export.py prints "[3/100] Game name" as it starts each game, so the games before it are done
      for (const line of lines) {
        const match = line.match(/^\[(\d+)\/(\d+)\] (.*)/);
        if (match) Object.assign(job, { done: Number(match[1]) - 1, total: Number(match[2]), current: match[3] });
      }
      job.log.push(...lines);
      job.log = job.log.slice(-LOG_LINES);
    };
    child.stdout.on("data", keep);
    child.stderr.on("data", keep);
    // Watch again and forget the old data, so the next page load shows the new files
    const finish = (code) => {
      job.running = false;
      job.exitCode = code;
      server.watcher.add(DATA_DIR);
      server.moduleGraph.invalidateAll();
    };
    child.on("error", (error) => { keep(String(error)); finish(-1); });
    child.on("close", finish);
  }

  return {
    name: "dev-refresh",
    hooks: {
      "astro:server:setup": ({ server: devServer }) => {
        server = devServer;
        server.middlewares.use("/__dev/refresh", (req, res) => {
          const send = (status, body) => {
            res.statusCode = status;
            res.setHeader("content-type", "application/json");
            res.end(JSON.stringify(body));
          };

          // Only answer requests that came from this dev page on localhost (blocks other websites and DNS tricks)
          const host = req.headers.host ?? "";
          if (!/^(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$/.test(host)) return send(403, { error: "localhost only" });
          if (req.method === "GET") return send(200, job);
          if (req.method !== "POST") return send(405, { error: "GET or POST only" });
          if (req.headers.origin !== `http://${host}`) return send(403, { error: "wrong origin" });
          if (job.running) return send(409, { error: "a refresh is already running" });

          let body = "";
          req.on("data", (chunk) => { body += chunk; });
          req.on("end", () => {
            let input = {};
            try { input = JSON.parse(body || "{}"); } catch { return send(400, { error: "bad JSON" }); }
            const { scope, appid } = input;
            if (!["stale", "all", "game"].includes(scope)) return send(400, { error: "unknown scope" });
            if (scope === "game" && !Number.isInteger(appid)) return send(400, { error: "appid must be a whole number" });
            start(scope, appid);
            send(202, job);
          });
        });
      },
    },
  };
}
