const BASE = import.meta.env.BASE_URL.replace(/\/$/, '');

/** Site-absolute URL for an internal path, honouring the Pages base path. */
export function url(p = ''): string {
  const clean = p.replace(/^\//, '');
  if (!clean) return `${BASE}/`;
  const [pathPart, ...rest] = clean.split(/(?=[?#])/);
  const needsSlash = pathPart && !pathPart.endsWith('/') && !/\.[a-z0-9]+$/i.test(pathPart);
  return `${BASE}/${pathPart}${needsSlash ? '/' : ''}${rest.join('')}`;
}
