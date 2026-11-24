// nova-dev band: a bar above the prompt showing the level and the last test result,
// with buttons for the levels, review, and the test runner. Same host API as ponytail's band.
import type { EngineInterface, Register } from 'claude-code'

const LEVELS = ['off', 'lite', 'full', 'ultra'] as const
// The script ships inside the plugin, so resolve it from the plugin folder, not the project folder.
const SCRIPT = (pluginRoot: string) => `${pluginRoot}/hooks/statusline.py`

const home = async ($: EngineInterface) => (await $.env.get('USERPROFILE')) ?? (await $.env.get('HOME')) ?? ''
const stateDir = async ($: EngineInterface) =>
  (await $.env.get('NOVA_DEV_DIR')) ?? `${await home($)}/.config/nova-dev`

// Same file the hooks read: setting a level here is the same as typing "nova dev <level>".
const setLevel = async ($: EngineInterface, level: string) => {
  await $.fs.write(`${await stateDir($)}/level`, level)
  $.ui.toast(`nova-dev level: ${level}`)
}

// The band text comes from the same script the status line uses, so both always agree.
const bandText = async ($: EngineInterface, cwd: string, pluginRoot: string) => {
  const run = (cmd: string) => $.process.run([cmd, '-I', SCRIPT(pluginRoot), '--band', cwd]).catch(() => undefined)
  const out = (await run('py -3')) ?? (await run('python'))
  return out?.exitCode === 0 ? out.stdout.trim() : 'nova-dev: not available (is Python installed?)'
}

export const register: Register = (on) => {
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const below = await next(e).catch(() => undefined)
    const { Box, Text, Button } = $.ui.resolve(e)
    const cwd = await $.session.cwd()
    const pluginRoot = (await $.env.get('CLAUDE_PLUGIN_ROOT')) ?? (await $.session.repo().catch(() => null))?.root ?? cwd
    const line = await bandText($, cwd, pluginRoot)
    const failing = line.includes('FAIL')

    const bar = (
      <Box flexDirection="row" alignItems="center" gap={2}>
        <Text bold color={failing ? 'error' : 'suggestion'}>{line}</Text>
        <Box flexGrow={1} />
        {LEVELS.map(level => (
          <Button key={level} plain label={level} onPress={() => setLevel($, level)} />
        ))}
        <Button key="review" plain label="Review" onPress={() => $.command.run({ command: 'nova-dev:nova-dev-review', args: '' })} />
        <Button key="test" plain label="Test" onPress={() => $.command.run({ command: 'nova-dev:nova-dev-check', args: '' })} />
      </Box>
    )
    return below ? <Box flexDirection="column">{bar}{below}</Box> : bar
  })
}
