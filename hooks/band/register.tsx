// nova-dev band: two rows above the prompt. Row 1 shows the level, project, tests, cost, agent time and tokens.
// Row 2 shows meters for context, plan limit and savings. Buttons: levels, details (opens the session page),
// review and test. Same host API as ponytail's band. Numbers come from statusline.py --band-json.
import type { EngineInterface, Register } from 'claude-code'

const LEVELS = ['off', 'lite', 'full', 'ultra'] as const
const CACHE_MS = 10_000 // the bar redraws often; the numbers change slowly, so reuse them briefly

type Session = {
  input: number
  output: number
  cache_read: number
  cache_create: number
  turns: number
  context: number
  agent_ms: number
} | null
type Summary = {
  tokens7: number
  limit_pct: number | null
  context_pct: number | null
  saved_reads: number
  saved_tokens: number
} | null
type BandData = {
  level: string
  tests: 'pass' | 'fail' | null
  tests_counts: { passed: number; failed: number } | null
  project: string
  summary: Summary
  session: Session
}

const home = async ($: EngineInterface) => (await $.env.get('USERPROFILE')) ?? (await $.env.get('HOME')) ?? ''
const stateDir = async ($: EngineInterface) =>
  (await $.env.get('NOVA_DEV_DIR')) ?? `${await home($)}/.config/nova-dev`

// Find the installed nova-dev folder: CLAUDE_PLUGIN_ROOT when the host sets it, otherwise the newest version
// folder in the plugin cache.
const versionKey = (v: string) => v.split('.').map(n => parseInt(n, 10) || 0)
const findPluginRoot = async ($: EngineInterface): Promise<string | null> => {
  const env = await $.env.get('CLAUDE_PLUGIN_ROOT')
  if (env) return env
  const base = `${await home($)}/.claude/plugins/cache/nova-dev/nova-dev`
  const versions = (await $.fs.list(base).catch(() => []))
    .filter(e => e.kind === 'dir')
    .map(e => e.name)
    .sort((a, b) => {
      const x = versionKey(a), y = versionKey(b)
      for (let i = 0; i < Math.max(x.length, y.length); i++) {
        const d = (x[i] ?? 0) - (y[i] ?? 0)
        if (d !== 0) return d
      }
      return 0
    })
  const newest = versions[versions.length - 1]
  return newest ? `${base}/${newest}` : null
}

// Run a nova-dev script with Python. The launcher and its flag are separate arguments.
const runPy = async ($: EngineInterface, script: string, args: string[]) => {
  const run = (cmd: string, pre: string[]) => $.process.run([cmd, ...pre, '-I', script, ...args]).catch(() => undefined)
  const out = (await run('py', ['-3'])) ?? (await run('python', []))
  return out && out.exitCode === 0 ? out.stdout.trim() : null
}

// Cached for CACHE_MS per session so a redraw does not start Python again.
const cachedBand = async ($: EngineInterface, cwd: string, sid: string): Promise<{ data: BandData | null; error: string | null }> => {
  const hit = (await $.store.get('band')) as { at: number; sid: string; data: BandData | null } | undefined
  if (hit && hit.sid === sid && Date.now() - hit.at < CACHE_MS && hit.data) return { data: hit.data, error: null }
  const root = await findPluginRoot($)
  if (!root) return { data: null, error: 'plugin folder not found' }
  const out = await runPy($, `${root}/hooks/statusline.py`, ['--band-json', cwd, sid])
  if (!out) return { data: null, error: 'could not run Python (is it installed?)' }
  try {
    const data = JSON.parse(out) as BandData
    await $.store.set('band', { at: Date.now(), sid, data })
    return { data, error: null }
  } catch {
    return { data: null, error: 'bad data from the status script' }
  }
}

const tokens = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(0)}k` : `${n}`)
const clock = (ms: number) => {
  const s = Math.floor(ms / 1000)
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60
  return h ? `${h}h ${String(m).padStart(2, '0')}m` : `${m}m ${String(sec).padStart(2, '0')}s`
}
const meter = (pct: number, width = 10) => {
  const filled = Math.max(0, Math.min(width, Math.round(pct / 100 * width)))
  return '█'.repeat(filled) + '░'.repeat(width - filled)
}
const levelColor = (level: string) =>
  ({ off: 'inactive', lite: 'suggestion', full: 'success', ultra: 'warning' } as Record<string, string>)[level] ?? 'inactive'
const pctColor = (pct: number) => (pct < 50 ? 'success' : pct < 75 ? 'warning' : 'error')

const setLevel = async ($: EngineInterface, level: string) => {
  await $.fs.write(`${await stateDir($)}/level`, level)
  await $.store.set('band', undefined)
  $.ui.toast(`nova-dev level: ${level}`)
}

// Build the session page with the report script, then open it with the system's default handler.
const openDetails = async ($: EngineInterface, cwd: string, sid: string, cost: number | undefined, d: BandData | null) => {
  const root = await findPluginRoot($)
  if (!root) return $.ui.toast('nova-dev: plugin folder not found')
  const args = [`${root}/scripts/report.py`, '--session', cwd, sid, cost === undefined ? '' : String(cost),
    String(d?.tests_counts?.passed ?? ''), String(d?.tests_counts?.failed ?? '')]
  const file = await runPy($, args[0] ?? '', args.slice(1))
  if (!file) return $.ui.toast('nova-dev: could not build the details page')
  const windows = (await $.env.get('OS')) === 'Windows_NT'
  if (windows) await $.process.run(['cmd', '/c', 'start', '', file])
  else await $.process.run([(await $.process.run(['uname'])).stdout.trim() === 'Darwin' ? 'open' : 'xdg-open', file])
}

export const register: Register = (on) => {
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const below = await next(e).catch(() => undefined)
    const { Box, Text, Button } = $.ui.resolve(e)
    const cwd = await $.session.cwd()
    const sid = await $.session.id().catch(() => '')
    const { data, error } = await cachedBand($, cwd, sid)
    // Session cost is the figure Claude Code reports, the same one ponytail's band shows.
    const usage = await $.session.usage().catch(() => undefined)
    const cost: number | undefined = typeof usage?.cost?.usd === 'number' ? usage.cost.usd : undefined

    const row1: any[] = []
    const row2: any[] = []
    if (error || !data) {
      row1.push(<Text key="err" bold color="error">{`● nova-dev: ${error ?? 'unavailable'}`}</Text>)
    } else {
      row1.push(<Text key="level" bold color={levelColor(data.level)}>{`● ${data.level.toUpperCase()}`}</Text>)
      row1.push(<Text key="project" dimColor>{data.project}</Text>)
      if (data.tests === 'pass') row1.push(<Text key="tests" color="success">{`✓ ${data.tests_counts?.passed ?? ''} passed`}</Text>)
      else if (data.tests === 'fail') row1.push(<Text key="tests" bold color="error">{`✗ ${data.tests_counts?.failed ?? ''} failing`}</Text>)
      if (cost !== undefined) row1.push(<Text key="cost">{`$${cost.toFixed(2)}`}</Text>)
      const s = data.session
      if (s) {
        row1.push(<Text key="time" color="suggestion">{`⏱ ${clock(s.agent_ms)}`}</Text>)
        row1.push(<Text key="tok" dimColor>{`↑ ${tokens(s.input + s.cache_read + s.cache_create)} in · ↓ ${tokens(s.output)} out`}</Text>)
        row2.push(<Text key="turns" dimColor>{`${s.turns} turns`}</Text>)
      }
      const sm = data.summary
      if (sm) {
        if (sm.context_pct !== null) {
          row2.push(<Text key="ctx" color={pctColor(sm.context_pct)}>{`ctx ${meter(sm.context_pct)} ${sm.context_pct.toFixed(0)}%`}</Text>)
        }
        if (sm.limit_pct !== null) {
          row2.push(<Text key="limit" color={pctColor(sm.limit_pct)}>{`limit ${meter(sm.limit_pct)} ${sm.limit_pct.toFixed(0)}%`}</Text>)
        }
        row2.push(<Text key="week" dimColor>{`7d ${tokens(sm.tokens7)} tok`}</Text>)
        if (sm.saved_reads > 0) {
          row2.push(<Text key="saved" color="success">{`↓ ${sm.saved_reads} repeats blocked`}</Text>)
        }
      }
    }

    const bar = (
      <Box flexDirection="column" gap={0}>
        <Box flexDirection="row" alignItems="center" gap={2}>
          {row1}
          <Box flexGrow={1} />
          {LEVELS.map(level => (
            <Button key={level} plain label={level} onPress={() => setLevel($, level)} />
          ))}
        </Box>
        <Box flexDirection="row" alignItems="center" gap={2}>
          {row2}
          <Box flexGrow={1} />
          <Button key="details" plain label="details ↗" onPress={() => openDetails($, cwd, sid, cost, data)} />
          <Button key="review" plain label="review ↗" onPress={() => $.command.run({ command: 'nova-dev:nova-dev-review', args: '' })} />
          <Button key="test" plain label="test ▶" onPress={() => $.command.run({ command: 'nova-dev:nova-dev-check', args: '' })} />
        </Box>
      </Box>
    )
    return below ? <Box flexDirection="column">{bar}{below}</Box> : bar
  })
}
