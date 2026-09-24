import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const tile = req.query.tile;
  if (req.method !== "GET" || !Array.isArray(tile) || tile.length !== 4) return res.status(404).end();
  const [style, z, x, yFile] = tile;
  const match = /^(\d+)\.(png|jpg)$/.exec(yFile);
  if (!match || !/^(dark|street|satellite)$/.test(style) || !/^\d+$/.test(z) || !/^\d+$/.test(x)) return res.status(404).end();
  const zoom = Number(z), column = Number(x), row = Number(match[1]);
  if (zoom < 0 || zoom > 18 || column >= 2 ** zoom || row >= 2 ** zoom ||
      (style === "satellite") !== (match[2] === "jpg")) return res.status(404).end();
  const url = style === "satellite"
    ? `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${zoom}/${row}/${column}`
    : `https://a.tile.openstreetmap.fr/osmfr/${zoom}/${column}/${row}.png`;
  try {
    const upstream = await fetch(url, { signal: AbortSignal.timeout(8000), headers: { "User-Agent": "Trinetra/1.0 (local analyst map)" } });
    const contentType = upstream.headers.get("content-type") || "";
    if (!upstream.ok || !contentType.startsWith("image/")) return res.status(502).end();
    res.setHeader("Content-Type", contentType);
    res.setHeader("Cache-Control", "public, max-age=86400");
    return res.status(200).send(Buffer.from(await upstream.arrayBuffer()));
  } catch {
    return res.status(502).end();
  }
}
