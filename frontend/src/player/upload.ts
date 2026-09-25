import { api } from "../api";

const SIZE = 512;

/** Canvas → 512px JPEG → presigned PUT → submit (contracts/api.md). */
export async function submitDrawing(canvas: HTMLCanvasElement, code: string, playerId: string) {
  const small = document.createElement("canvas");
  small.width = small.height = SIZE;
  const ctx = small.getContext("2d")!;
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, SIZE, SIZE);
  ctx.drawImage(canvas, 0, 0, SIZE, SIZE);
  const image = await new Promise<Blob>((resolve, reject) =>
    small.toBlob((b) => (b ? resolve(b) : reject(new Error("Could not export drawing"))), "image/jpeg", 0.85),
  );

  const { url, key } = await api.uploadUrl(code, playerId);
  await api.putDrawing(url, image);
  await api.submit(code, playerId, key);
}
