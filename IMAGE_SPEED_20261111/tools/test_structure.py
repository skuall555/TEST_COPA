"""Check preservation of model contracts, fallback safety, and single-topic scope."""
import hashlib
import subprocess
import unittest
from pathlib import Path
import yaml
from build import ROOT, REPO, BASE, NAME


def walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)


class Structure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = yaml.safe_load((ROOT / 'source' / NAME).read_text())
        cls.after = yaml.safe_load((ROOT / '4-9_貼り替え用.txt').read_text())
        cls.a = {n['id']: n for n in walk(cls.before) if 'id' in n and 'kind' in n}
        cls.b = {n['id']: n for n in walk(cls.after) if 'id' in n and 'kind' in n}

    def test_all_original_action_bodies_and_conditions_preserved(self):
        self.assertLessEqual(set(self.a), set(self.b))
        for ident, n in self.a.items():
            for key, value in n.items():
                if key not in ('actions', 'elseActions', 'conditions'):
                    self.assertEqual(value, self.b[ident][key], (ident, key))
            if 'conditions' in n:
                self.assertEqual([(c['id'], c['condition']) for c in n['conditions']], [(c['id'], c['condition']) for c in self.b[ident]['conditions']])

    def test_original_dependencies_and_ai_prompts_exactly_preserved(self):
        for ident in ('invokeAIBuilderModelAction_imageFacts', 'search_photoGuidelineRetrieve', 'answer_photoGuidelineJudge', 'setVariable_prompt1', 'setVariable_prompt2'):
            self.assertEqual(self.a[ident], self.b[ident], ident)

    def test_only_image_topic_is_patched(self):
        # Original files are untouched; all changes are isolated in this folder.
        tracked = subprocess.check_output(['git', '-C', str(REPO), 'diff', '--name-only', 'HEAD'], text=True).splitlines()
        self.assertTrue(all(p.startswith('IMAGE_SPEED_20261111/') for p in tracked), tracked)
        for name in (NAME, '1-マニュアル関連入口_optimized.yaml', '3-9-緊急保安業務エージェント_optimized.yaml', 'SUBARU_エージェント指示_optimized.txt'):
            current = REPO / 'SUBARU_optimized' / name
            original = subprocess.check_output(['git', '-C', str(REPO), 'show', BASE + ':SUBARU_optimized/' + name])
            self.assertEqual(hashlib.sha256(current.read_bytes()).hexdigest(), hashlib.sha256(original).hexdigest())

    def test_trigger_resume_fallback_and_history_preserved(self):
        for key in ('kind', 'condition', 'priority', 'type'):
            self.assertEqual(self.before['beginDialog'][key], self.after['beginDialog'][key])
        for ident in ('conditionGroup_photoGuideUnavailable', 'conditionGroup_sectionsMissing', 'setVariable_appendImageResultToGlobalHistory', 'sendActivity_analysisResult', 'endDialog_afterRestartEmergency'):
            self.assertEqual(self.a[ident], self.b[ident])
        self.assertFalse(any(n.get('kind') in ('BeginDialog', 'InvokeFlowAction') for n in walk(self.after)))

    def test_no_new_external_calls_unique_ids_and_valid_jumps(self):
        raw_ids = [n['id'] for n in walk(self.after) if 'id' in n]
        self.assertEqual(len(raw_ids), len(set(raw_ids)))
        for n in walk(self.after):
            if n.get('kind') == 'GotoAction':
                self.assertIn(n['actionId'], self.b)
        external = ('InvokeAIBuilderModelAction', 'SearchAndSummarizeContent', 'AnswerQuestionWithAI')
        self.assertEqual({k for k, n in self.a.items() if n.get('kind') in external}, {k for k, n in self.b.items() if n.get('kind') in external})

    def test_cache_stores_only_manual_text_never_image_or_decision(self):
        stores = [n for n in walk(self.after) if n.get('id', '').startswith('setVariable_imageSpeed_store')]
        self.assertEqual(len(stores), 6)
        self.assertEqual(stores[0]['value'], '=Topic.撮影要領本文')
        for n in stores:
            self.assertNotIn('画像事実', n['value'])
            self.assertNotIn('要領照合結果', n['value'])
        self.assertEqual(self.b['setVariable_imageSpeed_cacheSeconds']['value'], '=300')


if __name__ == '__main__':
    unittest.main()
