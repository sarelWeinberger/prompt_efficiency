#!/usr/bin/env node
// Dual-purpose logging reverse proxy for benchmark capture.
// Logs every request body and response body (buffering SSE) as JSONL, redacted.
//
// Usage: node capture-proxy.js <listenPort> <targetBaseUrl> <logFile> [label]
// Example (Together-facing):  node capture-proxy.js 8901 https://api.together.xyz  together_capture.jsonl together
// Example (Anthropic-facing): node capture-proxy.js 8903 http://127.0.0.1:4000     gateway_inbound.jsonl  anthropic
const http = require("http");
const fs = require("fs");
const path = require("path");
const { Readable } = require("stream");

const [PORT, TARGET, LOGFILE, LABEL = "capture"] = process.argv.slice(2);
if (!PORT || !TARGET || !LOGFILE) {
  console.error("usage: capture-proxy.js <port> <target> <logfile> [label]");
  process.exit(1);
}

// Secrets to redact: every value found in these env vars plus common key patterns.
const SECRETS = [
  process.env.TOGETHER_API_KEY,
  process.env.ANTHROPIC_AUTH_TOKEN,
  process.env.CAPTURE_EXTRA_SECRET,
].filter(Boolean);

function redact(text) {
  let out = text;
  for (const s of SECRETS) out = out.split(s).join("[REDACTED]");
  out = out.replace(/(tgp_v1_|sk-ant-|sk-|github_pat_|ghp_)[A-Za-z0-9_\-]{8,}/g, "$1[REDACTED]");
  return out;
}

function redactHeaders(h) {
  const out = { ...h };
  for (const k of ["authorization", "x-api-key", "cookie", "set-cookie", "proxy-authorization"]) {
    if (out[k]) out[k] = "[REDACTED]";
  }
  return out;
}

fs.mkdirSync(path.dirname(path.resolve(LOGFILE)), { recursive: true });
const logStream = fs.createWriteStream(LOGFILE, { flags: "a" });
function logEntry(obj) {
  logStream.write(redact(JSON.stringify(obj)) + "\n");
}

function tryJson(s) {
  try { return JSON.parse(s); } catch { return undefined; }
}

// Extract the terminal usage object from a buffered SSE stream (OpenAI or Anthropic shape).
function extractSseUsage(sseText) {
  const usages = [];
  const events = [];
  for (const line of sseText.split("\n")) {
    if (!line.startsWith("data:")) continue;
    const payload = line.slice(5).trim();
    if (payload === "[DONE]") continue;
    const j = tryJson(payload);
    if (!j) continue;
    if (j.usage) usages.push(j.usage);
    if (j.type === "message_delta" && j.usage) usages.push(j.usage);
    if (j.type === "message_start" && j.message && j.message.usage) usages.push(j.message.usage);
    // OpenAI Responses API stream: terminal event carries usage under response.usage
    if (j.response && j.response.usage) usages.push(j.response.usage);
    if (j.type) events.push(j.type);
    if (j.choices && j.choices[0] && j.choices[0].finish_reason) {
      events.push("finish:" + j.choices[0].finish_reason);
    }
  }
  return { usages, eventTypes: events };
}

let seq = 0;
http
  .createServer((req, res) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", async () => {
      const id = ++seq;
      const t0 = Date.now();
      const body = Buffer.concat(chunks);
      const parsedBody = tryJson(body.toString()) ?? body.toString().slice(0, 4000);
      logEntry({
        label: LABEL, kind: "request", seq: id, ts: new Date().toISOString(),
        method: req.method, url: req.url, headers: redactHeaders(req.headers),
        body: parsedBody,
      });
      try {
        const headers = { ...req.headers };
        delete headers.host;
        delete headers["content-length"];
        const upstream = await fetch(TARGET + req.url, {
          method: req.method,
          headers,
          body: body.length ? body : undefined,
        });
        const respHeaders = Object.fromEntries(upstream.headers);
        const isSse = (respHeaders["content-type"] || "").includes("event-stream");
        delete respHeaders["content-encoding"];
        delete respHeaders["content-length"];
        delete respHeaders["transfer-encoding"];
        res.writeHead(upstream.status, respHeaders);

        // Tee the response: stream to client while buffering for the log.
        const buf = [];
        if (upstream.body) {
          const reader = upstream.body.getReader();
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buf.push(Buffer.from(value));
            res.write(Buffer.from(value));
          }
        }
        res.end();
        const respText = Buffer.concat(buf).toString();
        const entry = {
          label: LABEL, kind: "response", seq: id, ts: new Date().toISOString(),
          status: upstream.status, elapsed_ms: Date.now() - t0, sse: isSse,
        };
        if (isSse) {
          const { usages, eventTypes } = extractSseUsage(respText);
          entry.usages = usages;
          entry.event_types_sample = eventTypes.slice(0, 40);
          entry.event_count = eventTypes.length;
          entry.bytes = respText.length;
          if (process.env.CAPTURE_FULL_SSE === "1") entry.sse_body = respText.slice(0, 500000);
        } else {
          entry.body = tryJson(respText) ?? respText.slice(0, 20000);
        }
        logEntry(entry);
      } catch (err) {
        logEntry({ label: LABEL, kind: "proxy_error", seq: id, error: String(err) });
        try {
          res.writeHead(502, { "content-type": "application/json" });
          res.end(JSON.stringify({ error: "capture_proxy: " + String(err) }));
        } catch {}
      }
    });
  })
  .listen(Number(PORT), () => console.log(`[capture-proxy:${LABEL}] :${PORT} -> ${TARGET} log=${LOGFILE}`));
