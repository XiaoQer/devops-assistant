import type { Router } from 'vue-router'

const isSafePath = (value: string) =>
  value.startsWith('/')
  && !value.includes('//')
  && !value.includes('\\')
  && !/[\u0000-\u001f\u007f]/.test(value)

export const resolveSafeRedirect = (
  router: Router,
  candidate: unknown,
  fallback = '/portal',
) => {
  if (typeof candidate !== 'string' || !isSafePath(candidate)) return fallback

  try {
    const resolved = router.resolve(candidate)
    if (
      resolved.matched.length === 0
      || !isSafePath(resolved.href)
      || !isSafePath(resolved.fullPath)
    ) {
      return fallback
    }
    return resolved.fullPath
  } catch {
    return fallback
  }
}
