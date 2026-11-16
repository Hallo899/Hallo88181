import unittest
from unittest.mock import Mock
from cryptography.fernet import Fernet, InvalidToken
from watch import classify, apply_observation, EMPTY

class WatchTests(unittest.TestCase):
    def test_empty_and_loading(self):
        self.assertEqual(classify(EMPTY), ('empty', None))
        for text in ['', 'Lädt …', 'November 2026', 'Technischer Fehler']:
            self.assertEqual(classify(text), ('unknown', None))
    def test_provisional_offer_and_dedup(self):
        kind, signature = classify('Schicht 12:00 – 16:30')
        self.assertEqual(kind, 'offers')
        state, send = {}, Mock()
        apply_observation(state, kind, signature, send)
        apply_observation(state, kind, signature, send)
        self.assertEqual(send.call_count, 1)
        apply_observation(state, 'empty', None, send)
        apply_observation(state, kind, signature, send)
        self.assertEqual(send.call_count, 2)
    def test_failed_delivery_retries(self):
        state = {'signature': 'old'}
        with self.assertRaises(OSError):
            apply_observation(state, 'offers', 'new', Mock(side_effect=OSError()))
        self.assertEqual(state['signature'], 'old')
    def test_unknown_does_not_reset(self):
        state = {'signature': 'old'}
        with self.assertRaises(RuntimeError):
            apply_observation(state, 'unknown', None, Mock())
        self.assertEqual(state['signature'], 'old')
    def test_encryption_rejects_wrong_key(self):
        cipher = Fernet(Fernet.generate_key())
        token = cipher.encrypt(b'private-session')
        self.assertNotIn(b'private-session', token)
        self.assertEqual(cipher.decrypt(token), b'private-session')
        with self.assertRaises(InvalidToken):
            Fernet(Fernet.generate_key()).decrypt(token)
