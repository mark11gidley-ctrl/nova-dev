// nova-dev band: a row of status chips above the prompt (level, tests, cost, context, tokens, savings)
// and quick buttons. Same host API as ponytail's band. The numbers come from statusline.py --band-json.
import type { EngineInterface, Register } from 'claude-code'

const LEVELS = ['off', 'lite', 'full', 'ultra'] as const
const CACHE_MS = 10_000 // the bar redraws often; the numbers change slowly, so reuse them briefly

type Summary = {
  tokens7: number
  limit_pct: number | null
  context_pct: number | null
  saved_reads: number
  saved_tokens: number
} | null
type BandData = { level: string; tests: 'pass' | 'fail' | null; summary: Summary }

// Find the installed nova-dev folder. Prefer CLAUDE_PLUGIN_ROOT when the host sets it; otherwise pick the
// newest version folder in the plugin cache, because the bar cannot rely on the host setting the variable.
const home = async ($: EngineInterface) => (await $.env.get('USERPROFILE')) ?? (await $.env.get('HOME')) ?? ''
const stateDir = async ($: EngineInterface) =>
  (await $.env.get('NOVA_DEV_DIR')) ?? `${await home($)}/.config/nova-dev`

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

// Ask the script for the bar's data as JSON. The launcher and its flag are separate arguments.
const fetchBand = async ($: EngineInterface, cwd: string, pluginRoot: string): Promise<BandData | null> => {
  const script = `${pluginRoot}/hooks/statusline.py`
  const run = (cmd: string, pre: string[]) =>
    $.process.run([cmd, ...pre, '-I', script, '--band-json', cwd]).catch(() => undefined)
  const out = (await run('py', ['-3'])) ?? (await run('python', []))
  if (!out || out.exitCode !== 0) return null
  try {
    return JSON.parse(out.stdout.trim()) as BandData
  } catch {
    return null
  }
}

// Cached for CACHE_MS so a redraw does not start Python again.
const cachedBand = async ($: EngineInterface, cwd: string): Promise<{ data: BandData | null; error: string | null }> => {
  const hit = (await $.store.get('band')) as { at: number; data: BandData | null } | undefined
  if (hit && Date.now() - hit.at < CACHE_MS && hit.data) return { data: hit.data, error: null }
  const root = await findPluginRoot($)
  if (!root) return { data: null, error: 'plugin folder not found' }
  const data = await fetchBand($, cwd, root)
  if (!data) return { data: null, error: 'could not run Python (is it installed?)' }
  await $.store.set('band', { at: Date.now(), data })
  return { data, error: null }
}

const tokens = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(0)}k` : `${n}`)
const levelColor = (level: string) =>
  ({ off: 'inactive', lite: 'suggestion', full: 'success', ultra: 'warning' } as Record<string, string>)[level] ?? 'inactive'
const contextColor = (pct: number) => (pct < 50 ? 'success' : pct < 75 ? 'warning' : 'error')

export const register: Register = (on) => {
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const below = await next(e).catch(() => undefined)
    const { Box, Text, Button } = $.ui.resolve(e)
    const cwd = await $.session.cwd()
    const { data, error } = await cachedBand($, cwd)
    // Session cost is the figure Claude Code reports, the same one ponytail's band shows.
    const usage = await $.session.usage().catch(() => undefined)
    const cost = usage?.cost?.usd

    const chips: any[] = []
    if (error || !data) {
      chips.push(<Text key="err" bold color="error">{`● nova-dev: ${error ?? 'unavailable'}`}</Text>)
    } else {
      chips.push(<Text key="level" bold color={levelColor(data.level)}>{`● ${data.level}`}</Text>)
      if (data.tests === 'pass') chips.push(<Text key="tests" color="success">✓ tests</Text>)
      else if (data.tests === 'fail') chips.push(<Text key="tests" bold color="error">✗ tests failing</Text>)
      else chips.push(<Text key="tests" dimColor>tests –</Text>)
      if (typeof cost === 'number') chips.push(<Text key="cost">{`$${cost.toFixed(2)} session`}</Text>)
      const s = data.summary
      if (s) {
        chips.push(<Text key="tok" dimColor>{`${tokens(s.tokens7)} tok · 7d`}</Text>)
        if (s.context_pct !== null) {
          chips.push(<Text key="ctx" color={contextColor(s.context_pct)}>{`ctx ${s.context_pct.toFixed(0)}%`}</Text>)
        }
        if (s.limit_pct !== null) {
          chips.push(<Text key="limit" color={s.limit_pct < 80 ? 'success' : 'error'}>{`limit ${s.limit_pct.toFixed(0)}%`}</Text>)
        }
        if (s.saved_reads > 0) {
          chips.push(<Text key="saved" color="success">{`↓ ${s.saved_reads} repeats · ~${tokens(s.saved_tokens)} saved`}</Text>)
        }
      }
    }

    const bar = (
      <Box flexDirection="column" gap={0}>
        <Box flexDirection="row" alignItems="center" gap={2}>
          {chips}
          <Box flexGrow={1} />
          {LEVELS.map(level => (
            <Button key={level} plain label={level} onPress={() => setLevel($, level)} />
          ))}
          <Button key="review" plain label="review ↗" onPress={() => $.command.run({ command: 'nova-dev:nova-dev-review', args: '' })} />
          <Button key="test" plain label="test ▶" onPress={() => $.command.run({ command: 'nova-dev:nova-dev-check', args: '' })} />
        </Box>
      </Box>
    )
    return below ? <Box flexDirection="column">{bar}{below}</Box> : bar
  })
}

// Same file the hooks read: setting a level here is the same as typing "nova dev <level>".
const setLevel = async ($: EngineInterface, level: string) => {
  await $.fs.write(`${await stateDir($)}/level`, level)
  await $.store.set('band', undefined)
  $.ui.toast(`nova-dev level: ${level}`)
}
