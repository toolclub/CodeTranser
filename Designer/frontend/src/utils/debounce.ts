export function debounce<TArgs extends unknown[]>(
  fn: (...args: TArgs) => void | Promise<void>,
  ms: number,
): (...args: TArgs) => void {
  let timer: number | null = null
  return (...args: TArgs) => {
    if (timer !== null) clearTimeout(timer)
    timer = window.setTimeout(() => {
      timer = null
      void fn(...args)
    }, ms)
  }
}
