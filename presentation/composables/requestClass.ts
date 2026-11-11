// Six request colors cycle by request number; labels keep ids readable when they repeat.
export function requestClass(id: string): string {
  const number = Number.parseInt(id.replace(/\D/g, ''), 10) || 1
  return `req-${((number - 1) % 6) + 1}`
}
