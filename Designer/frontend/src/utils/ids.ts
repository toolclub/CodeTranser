/** uuid4 前 N 位十六进制。对齐后端 new_id 语义。 */
export function newHex(short = 8): string {
  const bytes = new Uint8Array(short)
  ;(globalThis.crypto ?? window.crypto).getRandomValues(bytes)
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0'))
    .join('')
    .slice(0, short)
}

export const newInstanceId = () => `n_${newHex(8)}`
export const newEdgeId = () => `e_${newHex(8)}`
export const newBundleId = () => `bnd_${newHex(8)}`
