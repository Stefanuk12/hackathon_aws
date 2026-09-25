import { api, MOCK } from "../api";

/** Canvas → 512px JPEG → presigned PUT → submit. */
export async function submitDrawing(canvas: HTMLCanvasElement, code: string, playerId: string) {
  const small = document.createElement("canvas");
  small.width = small.height = 512;
  small.getContext("2d")!.drawImage(canvas, 0, 0, 512, 512);
  const blob = await new Promise<Blob>((ok) => small.toBlob((b) => ok(b!), "image/jpeg", 0.85));

  const { url, key } = await api.uploadUrl(code, playerId);
  if (!MOCK) {
    const res = await fetch(url, { method: "PUT", headers: { "Content-Type": "image/jpeg" }, body: blob });
    if (!res.ok) throw new Error(`upload failed: ${res.status}`);
  }
  await api.submit(code, playerId, key);
}
