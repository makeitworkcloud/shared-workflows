import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.load(
    (ROOT / '.github/workflows/_opencode-review.yml').read_text(), Loader=yaml.BaseLoader
)
STEPS = {step.get('id', step['name']): step for step in WORKFLOW['jobs']['review']['steps']}
HEAD, BASE = 'a' * 40, 'b' * 40
CHILDREN = [
    'adversarial-code-reviewer', 'infra-security-reviewer', 'devops-engineer',
    'qa-engineer', 'release-engineer',
]
SKILLS = [
    'opentofu-root-change', 'shared-workflow-change-impact', 'sops-ksops-safe-editing',
    'opencode-chart-release-and-gitops-rollout', 'cloudflare-dns-and-tunnel-ownership',
]
HARNESS = r'''
const fs = require('fs');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const output = {outputs: {}, git: [], api: []};
const github = {rest: {
  repos: {
    get: async args => {output.api.push({method: 'repository', args}); return {data: {default_branch: 'main'}};},
    getCollaboratorPermissionLevel: async args => {output.api.push({method: 'permission', args}); return {data: {permission: input.permission || 'read'}};},
  },
  pulls: {get: async args => {output.api.push({method: 'pull', args}); return {data: input.pr};}},
}};
const core = {setOutput: (key, value) => {output.outputs[key] = value;}};
const mockRequire = name => name === 'child_process' ? {
  execFileSync: (command, args) => {
    output.git.push({command, args});
    if (input.gitError) throw Error('mock collection failure');
    if (args.includes('--name-only')) return input.names || 'src/app.js\0';
    if (args.includes('--numstat')) return input.numstat || '1\t1\tsrc/app.js';
    if (args.includes('--raw')) return input.raw || '';
    if (args.includes('diff')) return input.diff || 'diff --git a/src/app.js b/src/app.js\n+safe';
    return '';
  },
} : require(name);
new Function('require', 'github', 'context', 'core',
  'return (async () => {' + input.script + '\n})()'
)(mockRequire, github, input.context, core).then(
  () => process.stdout.write(JSON.stringify(output)),
  error => process.stdout.write(JSON.stringify({...output, error: error.message})),
);
'''


class ReviewWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / 'review'
        self.work.mkdir()
        self.source = self.root / 'workspace/source'
        self.source.mkdir(parents=True)
        policy = self.root / 'workspace/policy/opencode-server/files'
        (policy / 'agents').mkdir(parents=True)
        for name in CHILDREN:
            (policy / 'agents' / f'{name}.md').write_text(
                '---\npermission: legacy\nmodel: wrong/provider\n---\nTrusted reviewer body.\n'
            )
        for name in SKILLS:
            folder = policy / 'skills' / name
            folder.mkdir(parents=True)
            (folder / 'SKILL.md').write_text('Trusted skill.\n')
        self.pr = {
            'number': 7, 'state': 'open', 'title': 'Untrusted title', 'body': 'Untrusted body',
            'head': {'sha': HEAD, 'repo': {'full_name': 'example/repo'}},
            'base': {'sha': BASE, 'repo': {'full_name': 'example/repo'}},
        }

    def run_step(self, step, *, event='pull_request_target', permission='read', **overrides):
        context = {
            'repo': {'owner': 'example', 'repo': 'repo'}, 'eventName': event,
            'ref': 'refs/heads/main', 'actor': 'maintainer', 'serverUrl': 'https://github.com',
            'runId': 42, 'payload': {'action': 'synchronize', 'pull_request': {'number': 7}},
        }
        context.update(overrides.pop('context', {}))
        env = {
            'PATH': os.environ['PATH'], 'REVIEW_DIR': str(self.work),
            'GITHUB_WORKSPACE': str(self.root / 'workspace'), 'REVIEW_MODEL': 'openai/test-model',
            'HEAD': HEAD, 'BASE': BASE, 'NUMBER': '7', 'PR_NUMBER': '7',
            'DISPATCH_ACTOR': 'maintainer', 'APPROVED_HEAD': HEAD,
        }
        env.update(overrides.pop('env', {}))
        result = subprocess.run(
            ['node', '-e', HARNESS], input=json.dumps({
                'script': STEPS[step]['with']['script'], 'context': context,
                'pr': self.pr, 'permission': permission, **overrides,
            }), text=True, capture_output=True, env=env, check=True, timeout=10,
        )
        return json.loads(result.stdout)

    def stream(self, text='No findings.\nREVIEW_COMPLETE', *, exitcode='0', records=None):
        def event(kind, message='final', **part):
            return {'type': kind, 'sessionID': 'ses_test', 'part': {'messageID': message, **part}}
        values = records if records is not None else [
            event('step_start'), event('text', text=text), event('step_finish'),
        ]
        (self.work / 'exitcode').write_text(exitcode)
        (self.work / 'stdout.ndjson').write_text('\n'.join(json.dumps(item) for item in values))
        return event

    def comment(self):
        return (self.work / 'comment.md').read_text()

    def test_native_v2_config_and_explicit_agent_permissions(self):
        result = self.run_step('prepare')
        self.assertEqual(result['outputs']['ready'], 'true')
        config = json.loads((self.work / 'opencode.json').read_text())
        self.assertIn('agents', config)
        self.assertNotIn('agent', config)
        self.assertNotIn('permission', config)
        deny = {'action': '*', 'resource': '*', 'effect': 'deny'}
        self.assertEqual(config['permissions'], [deny])
        for name, agent in config['agents'].items():
            self.assertEqual(agent['model'], 'openai/test-model')
            self.assertEqual(agent['permissions'][0], deny)
            self.assertNotIn('permission', agent)
            self.assertNotIn('prompt', agent)
            self.assertNotIn('legacy', agent['system'])
            grants = [r for r in agent['permissions'] if r['effect'] == 'allow']
            self.assertFalse(any(r['action'] in ['shell', 'edit', 'execute', 'webfetch', 'websearch'] for r in grants))
            delegates = [r['resource'] for r in grants if r['action'] == 'subagent']
            self.assertEqual(delegates, CHILDREN if name == 'pipeline-reviewer' else [])
            if name == 'devops-engineer':
                self.assertEqual(agent['permissions'], [deny])
        primary = config['agents']['pipeline-reviewer']['permissions']
        source_grant = next(i for i, r in enumerate(primary) if r == {
            'action': 'read', 'resource': str(self.source) + '/*', 'effect': 'allow',
        })
        for pattern in ['*/.git/*', '*.env*', '*.tfstate*', '*credential*', '*secret*']:
            index = next(i for i, r in enumerate(primary) if r['resource'] == pattern)
            self.assertGreater(index, source_grant)

    def test_same_repository_bots_are_not_filtered(self):
        result = self.run_step('snapshot', context={'actor': 'dependabot[bot]'})
        self.assertEqual(result['outputs']['authorized'], 'true')

    def test_fork_automatic_run_never_authorizes_inference(self):
        self.pr['head']['repo']['full_name'] = 'fork/repo'
        self.assertEqual(self.run_step('snapshot')['outputs']['authorized'], 'false')

    def test_dispatch_requires_effective_permission_exact_head_and_default_ref(self):
        self.pr['head']['repo']['full_name'] = 'fork/repo'
        for permission in ['read', 'triage']:
            self.assertIn('error', self.run_step('snapshot', event='workflow_dispatch', permission=permission))
        for permission in ['write', 'maintain', 'admin']:
            self.assertEqual(self.run_step('snapshot', event='workflow_dispatch', permission=permission)['outputs']['authorized'], 'true')
        for kwargs in [
            {'env': {'APPROVED_HEAD': 'c' * 40}},
            {'context': {'ref': 'refs/heads/untrusted'}},
        ]:
            self.assertIn('error', self.run_step('snapshot', event='workflow_dispatch', permission='write', **kwargs))

    def test_closed_or_unsupported_event_cannot_review(self):
        self.pr['state'] = 'closed'
        self.assertNotIn('authorized', self.run_step('snapshot')['outputs'])
        self.assertIn('error', self.run_step('snapshot', event='push'))

    def test_authorization_queries_the_event_or_dispatch_pr_and_effective_actor(self):
        automatic = self.run_step('snapshot', env={'PR_NUMBER': '999'})
        self.assertEqual([call['args'] for call in automatic['api'] if call['method'] == 'pull'], [
            {'owner': 'example', 'repo': 'repo', 'pull_number': 7},
        ])
        self.pr['number'] = 37
        manual = self.run_step('snapshot', event='workflow_dispatch', permission='write', env={
            'PR_NUMBER': '37', 'DISPATCH_ACTOR': 'effective-maintainer',
        })
        self.assertEqual([call['args'] for call in manual['api'] if call['method'] == 'pull'], [
            {'owner': 'example', 'repo': 'repo', 'pull_number': 37},
        ])
        self.assertEqual([call['args'] for call in manual['api'] if call['method'] == 'permission'], [
            {'owner': 'example', 'repo': 'repo', 'username': 'effective-maintainer'},
        ])

    def test_one_exact_git_route_with_safe_diff_options(self):
        result = self.run_step('prepare')
        calls = result['git']
        self.assertTrue(all(call['command'] == 'git' for call in calls))
        self.assertEqual([call['args'][3:] for call in calls[:3]], [
            ['cat-file', '-e', f'{BASE}^{{commit}}'],
            ['cat-file', '-e', f'{HEAD}^{{commit}}'],
            ['merge-base', BASE, HEAD],
        ])
        diffs = [call['args'][3:] for call in calls[3:]]
        options = ['diff', '--no-ext-diff', '--no-textconv', '--no-renames']
        self.assertEqual(diffs, [
            options + ['--name-only', '-z', f'{BASE}...{HEAD}'],
            options + ['--numstat', f'{BASE}...{HEAD}'],
            options + ['--raw', f'{BASE}...{HEAD}'],
            options + [f'{BASE}...{HEAD}'],
        ])

    def test_invalid_model_and_snapshot_are_rejected(self):
        self.assertIn('error', self.run_step('snapshot', env={'REVIEW_MODEL': 'other/model'}))
        self.pr['head']['sha'] = 'not-a-sha'
        self.assertIn('error', self.run_step('snapshot'))

    def test_missing_trusted_prompt_or_skill_fails_closed(self):
        policy = self.root / 'workspace/policy/opencode-server/files'
        prompt = policy / 'agents' / f'{CHILDREN[0]}.md'
        original = prompt.read_text()
        prompt.unlink()
        self.assertNotIn('ready', self.run_step('prepare')['outputs'])
        prompt.write_text(original)
        (policy / 'skills' / SKILLS[0] / 'SKILL.md').unlink()
        self.assertNotIn('ready', self.run_step('prepare')['outputs'])

    def test_collection_fails_closed_before_sensitive_content_or_on_limit(self):
        cases = [
            {'names': '.env\0'}, {'names': 'cluster-secret.yaml\0'},
            {'numstat': '-\t-\timage.png'}, {'raw': ':160000 160000 abc def M\tmodule'},
            {'diff': 'x' * 100001}, {'diff': '+version https://git-lfs.github.com/spec/v1'},
            {'gitError': True},
        ]
        for case in cases:
            with self.subTest(case=list(case)):
                result = self.run_step('prepare', **case)
                self.assertNotIn('ready', result['outputs'])
                self.assertFalse(json.loads((self.work / 'result.json').read_text())['complete'])
                (self.work / 'result.json').unlink()
                if 'names' in case:
                    self.assertFalse(any(call['args'][-1] == f'{BASE}...{HEAD}' and not any(
                        option in call['args'] for option in ['--name-only', '--numstat', '--raw']
                    ) for call in result['git'] if 'diff' in call['args']))

    def test_stale_head_or_base_suppresses_inference_and_publication(self):
        for side in ['head', 'base']:
            original = self.pr[side]['sha']
            self.pr[side]['sha'] = 'c' * 40
            self.assertEqual(self.run_step('fresh')['outputs']['current'], 'false')
            self.assertNotIn('publish', self.run_step('result')['outputs'])
            self.pr[side]['sha'] = original

    def test_only_final_message_and_post_finish_suffix_are_published_as_inert_text(self):
        event = self.stream()
        self.stream(records=[
            event('step_start', 'earlier'), event('text', 'earlier', text='OLD REVIEW_COMPLETE'),
            event('step_finish', 'earlier'), event('step_start'),
            event('text', text='![untrusted](https://invalid.example/image)\nREVIEW_'),
            event('step_finish'), event('text', text='COMPLETE'),
        ])
        self.assertEqual(self.run_step('result')['outputs']['publish'], 'true')
        body = self.comment()
        self.assertNotIn('OLD', body)
        self.assertIn('    ![untrusted]', body)
        self.assertIn('    REVIEW_COMPLETE', body)
        self.assertIn(HEAD, body)

    def test_invalid_and_failed_output_is_incomplete_without_raw_errors(self):
        event = self.stream()
        cases = [
            {'exitcode': '1'}, {'text': 'No completion marker'},
            {'records': [{'type': 'error', 'error': {'message': 'PRIVATE_ERROR'}}]},
            {'records': [event('step_start'), event('tool_use', state={'status': 'error'})]},
            {'records': [event('step_start'), event('text', text='REVIEW_COMPLETE')]},
            {'text': 'x' * 48001 + '\nREVIEW_COMPLETE'},
        ]
        for case in cases:
            with self.subTest(case=list(case)):
                self.stream(**case)
                self.run_step('result')
                self.assertIn('REVIEW_INCOMPLETE', self.comment())
                self.assertNotIn('PRIVATE_ERROR', self.comment())
        (self.work / 'stdout.ndjson').write_text('not json')
        self.run_step('result')
        self.assertIn('REVIEW_INCOMPLETE', self.comment())

    def test_honest_incomplete_findings_are_retained(self):
        self.stream('Known finding; missing context.\nREVIEW_INCOMPLETE')
        self.run_step('result')
        self.assertIn('Known finding', self.comment())
        self.assertIn('REVIEW_INCOMPLETE', self.comment())

    def test_cr_and_crlf_cannot_escape_inert_output(self):
        for ending in ['\r', '\r\n', '\n']:
            with self.subTest(ending=repr(ending)):
                self.stream(f'Untrusted output{ending}![image](https://invalid.example/image){ending}@mention\nREVIEW_COMPLETE')
                self.run_step('result')
                body = (self.work / 'comment.md').read_bytes().decode()
                self.assertNotIn('\r', body)
                self.assertIn('\n    ![image]', body)
                self.assertIn('\n    @mention', body)

    def test_rendering_expansion_and_unicode_cannot_exceed_comment_bound(self):
        for payload in ['x\n' * 10000, '\U0001f600' * 15000]:
            with self.subTest(kind='newlines' if payload.startswith('x') else 'unicode'):
                self.stream(payload + '\nREVIEW_COMPLETE')
                self.run_step('result')
                body = (self.work / 'comment.md').read_bytes()
                self.assertLess(len(body), 60000)
                self.assertIn(b'REVIEW_INCOMPLETE', body)
                self.assertIn(b'comment bound', body)

    def test_workflow_contract_is_disabled_pinned_and_bounded(self):
        inputs = WORKFLOW['on']['workflow_call']['inputs']
        self.assertEqual(inputs['enabled']['default'], 'false')
        self.assertEqual(list(WORKFLOW['on']), ['workflow_call'])
        job = WORKFLOW['jobs']['review']
        self.assertEqual(job['runs-on'], 'ubuntu-24.04')
        self.assertIn("vars.OPENCODE_REVIEW_ENABLED == 'true'", job['if'])
        self.assertEqual(job['timeout-minutes'], '20')
        self.assertEqual(STEPS['cli']['timeout-minutes'], '15')
        self.assertEqual(WORKFLOW['concurrency']['cancel-in-progress'], 'true')
        self.assertEqual(WORKFLOW['permissions'], {'contents': 'read', 'pull-requests': 'write'})
        for step in job['steps']:
            if 'uses' in step:
                self.assertRegex(step['uses'], r'@[0-9a-f]{40}$')
            if 'run' in step:
                self.assertNotIn('${{', step['run'])
            if 'OPENAI_API_KEY' in step.get('env', {}):
                self.assertEqual(step['id'], 'cli')
        self.assertFalse(any('GITHUB_TOKEN' in step.get('env', {}) or 'GH_TOKEN' in step.get('env', {}) for step in job['steps']))
        comments = [step for step in job['steps'] if step.get('uses', '').startswith('marocchino/')]
        self.assertEqual(len(comments), 2)
        self.assertTrue(all('number_force' in step['with'] and 'recreate' not in step['with'] for step in comments))
        for name in ['Checkout source', 'Checkout trusted reviewer definitions', 'Set up Node', 'Install official V2 CLI', 'prepare']:
            self.assertEqual(STEPS[name]['if'], "steps.snapshot.outputs.authorized == 'true'")
        self.assertEqual(STEPS['fresh']['if'], "steps.prepare.outputs.ready == 'true'")
        self.assertEqual(STEPS['cli']['if'], "steps.fresh.outputs.current == 'true'")
        self.assertEqual(STEPS['result']['if'], "always() && steps.snapshot.outputs.authorized == 'true'")
        source = STEPS['Checkout source']['with']
        for key in ['persist-credentials', 'submodules', 'lfs']:
            self.assertEqual(source[key], 'false')
        self.assertEqual(source['fetch-depth'], '0')
        checks = yaml.load((ROOT / '.github/workflows/_opencode-review-tests.yml').read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(checks['on'], {'pull_request': {'branches': ['main']}, 'push': {'branches': ['main']}})
        self.assertEqual(checks['permissions'], {'contents': 'read'})
        self.assertNotIn('secrets', json.dumps(checks))


if __name__ == '__main__':
    unittest.main()
