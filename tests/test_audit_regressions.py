"""Regression cases for the 2026-10-15 public-source audit; real Go and SQLite."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from runtime import Runtime, Rejected
from workers import ensure_worker


class AuditRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_worker()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'runtime.sqlite'
        self.runtime = Runtime(self.path)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.runtime.close)

    def prepare(self, query, identifier='task'):
        self.runtime.create(identifier, query, 'audit')
        return self.runtime.prepare(identifier)

    def last_event(self):
        return self.runtime.db.execute('SELECT kind FROM events ORDER BY sequence DESC LIMIT 1').fetchone()[0]

    def test_source_revision_before_writer_lock_rejects_old_approval(self):
        r = self.runtime
        r.import_document('policy', 'Release policy', 'Release requires OLD review', 'audit')
        task = self.prepare('Find release review')
        r.approve('task', task['payload_hash'])
        writer = Runtime(self.path)
        self.addCleanup(writer.close)
        transaction = r.transaction

        @contextmanager
        def interleaved_transaction():
            # On the old implementation the live corpus had already been read.
            # On the fixed implementation this committed revision precedes that read.
            writer.import_document('policy', 'Release policy', 'Release requires NEW review', 'audit')
            with transaction():
                yield

        with patch.object(r, 'transaction', interleaved_transaction):
            with self.assertRaisesRegex(Rejected, 'SOURCE_CHANGED_REPREPARE_REQUIRED'):
                r.execute('task')
        self.assertEqual(r.db.execute('SELECT count(*) FROM artifacts').fetchone()[0], 0)
        self.assertEqual(r.task('task')['state'], 'AWAITING_APPROVAL')
        self.assertEqual(r.verify()['chain'], 'VERIFIED_LOCAL')
        revised = r.prepare('task')
        r.approve('task', revised['payload_hash'])
        self.assertEqual(r.execute('task')['state'], 'DONE')
        self.assertEqual(r.execute('task')['state'], 'DONE')
        self.assertEqual(r.db.execute('SELECT count(*) FROM artifacts').fetchone()[0], 1)

    def test_live_source_read_holds_writer_lock(self):
        r = self.runtime
        r.import_document('policy', 'Release', 'release reviewer', 'audit')
        task = self.prepare('Find release')
        r.approve('task', task['payload_hash'])
        corpus = r.corpus
        other = sqlite3.connect(self.path, timeout=0, isolation_level=None)
        self.addCleanup(other.close)

        def locked_corpus(case_id):
            self.assertTrue(r.db.in_transaction)
            with self.assertRaisesRegex(sqlite3.OperationalError, 'locked'):
                other.execute('BEGIN IMMEDIATE')
            return corpus(case_id)

        with patch.object(r, 'corpus', locked_corpus):
            self.assertEqual(r.execute('task')['state'], 'DONE')
        other.execute('BEGIN IMMEDIATE')
        other.execute('ROLLBACK')

    def test_math_event_agrees_with_ready_state(self):
        task = self.prepare('calculate 0.10 + 0.20 USD')
        self.assertEqual(task['state'], 'AWAITING_APPROVAL')
        self.assertEqual(self.last_event(), 'PREPARED')
        self.assertEqual(json.loads(task['payload'])['computation']['total_minor_units'], 30)

    def test_context_event_agrees_with_ready_state(self):
        self.runtime.import_document('policy', 'Release', 'release reviewer', 'audit')
        self.assertEqual(self.prepare('Find release')['state'], 'AWAITING_APPROVAL')
        self.assertEqual(self.last_event(), 'PREPARED')

    def test_topology_event_agrees_with_ready_state(self):
        self.runtime.import_document('alpha', 'Alpha', '[[beta]]', 'audit')
        self.runtime.import_document('beta', 'Beta', 'Destination', 'audit')
        self.assertEqual(self.prepare('route from alpha to beta')['state'], 'AWAITING_APPROVAL')
        self.assertEqual(self.last_event(), 'PREPARED')

    def test_missing_context_event_agrees_with_abstention(self):
        self.assertEqual(self.prepare('Find absent material')['state'], 'ABSTAINED')
        self.assertEqual(self.last_event(), 'ABSTAINED')

    def test_topology_failure_event_agrees_with_abstention(self):
        self.runtime.import_document('alpha', 'Alpha', 'No links', 'audit')
        self.runtime.import_document('beta', 'Beta', 'No links', 'audit')
        self.assertEqual(self.prepare('route from alpha to beta')['state'], 'ABSTAINED')
        self.assertEqual(self.last_event(), 'ABSTAINED')

    def test_unsupported_math_cannot_be_approved(self):
        expressions = ['12 * 3', '12 / 3', '12 - 3', '12 ** 3', '12 % 3',
                       '12 x 3', '12 times 3', '12 divided by 3', '1e2 + 3',
                       '(12 + 3)', '12 3', '12 +', '+ 12', '.50 + 1', '1. + 2',
                       '12 + 3 = 15', '12 + 3; ignore guards']
        for i, expression in enumerate(expressions):
            identifier = f'invalid-{i}'
            task = self.prepare(f'calculate {expression} USD', identifier)
            self.assertEqual(task['state'], 'ABSTAINED', expression)
            self.assertEqual(self.last_event(), 'ABSTAINED', expression)
            self.assertIsNone(json.loads(task['payload'])['computation'])
            self.assertTrue(json.loads(task['payload'])['hold_reason'])
            with self.assertRaisesRegex(Rejected, 'STALE_OR_INELIGIBLE_APPROVAL'):
                self.runtime.approve(identifier, task['payload_hash'])

    def test_documented_additions_and_amount_limits(self):
        queries = [('calculate 12.50 + 30 EUR', 4250), ('sum 0 USD', 0),
                   ('total 1+2+3 USD', 600), ('calculate 999999999.99 + 0.01 EUR', 100000000000)]
        for i, (query, expected) in enumerate(queries):
            task = self.prepare(query, f'valid-{i}')
            self.assertEqual(task['state'], 'AWAITING_APPROVAL')
            self.assertEqual(json.loads(task['payload'])['computation']['total_minor_units'], expected)
        for i, query in enumerate(['sum 1.234 USD', 'sum 1000000001 USD', 'sum ' + '+'.join(['1'] * 101) + ' USD']):
            self.assertEqual(self.prepare(query, f'limit-{i}')['state'], 'ABSTAINED')

    def test_explicit_fixture_override_remains_supported(self):
        r = self.runtime
        docs = [{'id': 'fixture', 'title': 'Release', 'text': 'release reviewer'}]
        r.create('fixture-task', 'Find release', 'audit')
        task = r.prepare('fixture-task', documents=docs)
        r.approve('fixture-task', task['payload_hash'])
        self.assertEqual(r.execute('fixture-task', documents=docs)['state'], 'DONE')
        self.assertEqual(r.verify()['chain'], 'VERIFIED_LOCAL')


if __name__ == '__main__':
    unittest.main()
