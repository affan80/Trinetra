import type { NextApiRequest, NextApiResponse } from "next";

const base = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const path = req.query.path;
  if (!Array.isArray(path) || !["GET", "POST"].includes(req.method || "")) {
    return res.status(405).json({ detail: "Method not allowed" });
  }
  const route = path.join("/");
  if (!/^(overview(?:\/lineage\/[^/]+)?|incidents\/[^/]+|source-audit(?:\/(?:outputs|map))?|auth\/(?:login|register)|watchlists|collection-jobs)$/.test(route)) {
    return res.status(404).json({ detail: "Route not found" });
  }
  try {
    const query = new URLSearchParams(Object.entries(req.query).filter(([key]) => key !== "path").flatMap(([key, value]) => Array.isArray(value) ? value.map(item => [key, item]) : value === undefined ? [] : [[key, value]])).toString();
    const response = await fetch(`${base}/api/v1/${path.map(encodeURIComponent).join("/")}${query ? `?${query}` : ""}`, {
      method: req.method,
      headers: {
        ...(typeof req.headers.authorization === "string" ? { Authorization: req.headers.authorization } : {}),
        ...(req.method === "POST" ? { "Content-Type": "application/json" } : {}),
      },
      body: req.method === "POST" ? JSON.stringify(req.body) : undefined,
      cache: "no-store",
    });
    res.setHeader("Cache-Control", "no-store");
    res.status(response.status).send(await response.text());
  } catch {
    res.status(502).json({ detail: "Backend unavailable" });
  }
}
