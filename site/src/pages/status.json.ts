// The status snapshot the pages were rendered from. Every status badge on the
// site carries data-status-host="<slug>", so a later live loader only has to
// fetch a fresher copy of this file and update those elements.
import { statusSnapshot } from '../lib/inventory';

export function GET() {
  return new Response(
    JSON.stringify({ as_of: statusSnapshot.asOf, live: statusSnapshot.live, hosts: statusSnapshot.hosts }, null, 2),
    { headers: { 'Content-Type': 'application/json' } },
  );
}
