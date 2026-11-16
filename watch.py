"""Conservative prototype: notify on offer-view changes, never accept a shift."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.request
from urllib.parse import urlparse
from cryptography.fernet import Fernet

URL = 'https://portal.flaschenpost.de/#/shift-planning/shift-offers'
SELECTOR = 'app-shift-slot-offers-view .shift-slot-offers-content'
EMPTY = 'Leider haben wir aktuell keine freien Schichtangebote'
STATE = Path('.state/state.enc')


def classify(text):
    text = ' '.join(text.split())
    if text == EMPTY:
        return 'empty', None
    # Provisional until validated against an actual offer. Never treat loading as offers.
    if len(re.findall(r'\b(?:[01]?\d|2[0-3]):[0-5]\d\b', text)) >= 2:
        return 'offers', hashlib.sha256(text.encode()).hexdigest()
    return 'unknown', None


def notify(message):
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    if token or chat_id:
        if not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]+', token) or not re.fullmatch(r'[1-9][0-9]*', chat_id):
            raise ValueError('TELEGRAM_CONFIGURATION')
        payload = json.dumps({'chat_id': chat_id, 'text': f'Schichtalarm: {message}\n{URL}'}).encode()
        request = urllib.request.Request(
            f'https://api.telegram.org/bot{token}/sendMessage', data=payload,
            headers={'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            if json.load(response).get('ok') is not True:
                raise RuntimeError('PUSH_FAILED')
        return

    topic = os.environ['NTFY_TOPIC']
    if not re.fullmatch(r'shift-[a-f0-9]{32,64}', topic):
        raise ValueError('TOPIC_CONFIGURATION')
    payload = json.dumps({'topic': topic, 'title': 'Schichtalarm', 'message': message,
                          'click': URL, 'priority': 4}).encode()
    request = urllib.request.Request('https://ntfy.sh', data=payload,
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError('PUSH_FAILED')


def save(state, cipher):
    STATE.parent.mkdir(mode=0o700, exist_ok=True)
    temporary = STATE.with_suffix('.tmp')
    temporary.write_bytes(cipher.encrypt(json.dumps(state).encode()))
    temporary.replace(STATE)


def apply_observation(state, kind, signature, send):
    if kind == 'unknown':
        raise RuntimeError('VIEW_UNRECOGNIZED')
    if kind == 'empty':
        state['signature'] = None
    elif signature != state.get('signature'):
        send('Die Schichtangebotsanzeige hat sich geändert. Öffne das Portal und prüfe freie Schichten.')
        state['signature'] = signature  # Only advance after successful delivery.


def read_view(state, persist):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(storage_state=state.get('session'))
        page = context.new_page()
        page.set_default_timeout(20000)
        page.goto(URL, wait_until='domcontentloaded', timeout=45000)
        # Wait for either the offers view or the known login form.
        for _ in range(30):
            if page.locator(SELECTOR).is_visible() or page.locator('input[name="loginId"]').is_visible():
                break
            page.wait_for_timeout(1000)
        if page.locator('input[name="loginId"]').is_visible():
            if urlparse(page.url).hostname != 'fauth.flaschenpost.de':
                raise RuntimeError('LOGIN_ORIGIN')
            # Persist lock BEFORE submitting. Even a failed/aborted run must not retry blindly.
            state['blocked'] = True
            persist()
            page.locator('input[name="loginId"]').fill(os.environ['FLASCHENPOST_LOGIN'])
            page.locator('input[name="password"]').fill(os.environ['FLASCHENPOST_PASSWORD'])
            page.get_by_role('button', name=re.compile('Submit|Einloggen', re.I)).click()
            page.locator(SELECTOR).wait_for(state='visible', timeout=45000)
            state['blocked'] = False
        page.locator(SELECTOR).wait_for(state='visible')
        # Two stable observations reduce notifications caused by loading transitions.
        first = page.locator(SELECTOR).inner_text()
        page.wait_for_timeout(2000)
        second = page.locator(SELECTOR).inner_text()
        state['session'] = context.storage_state()
        browser.close()
        if classify(first) != classify(second):
            raise RuntimeError('VIEW_UNSTABLE')
        return classify(second)


def main(mode):
    if mode == 'notification-test':
        notify('Test erfolgreich: Hier erscheinen später Hinweise auf Schichtangebote.')
        print('PUSH_SENT')
        return
    cipher = Fernet(os.environ['STATE_KEY'].encode())
    if STATE.exists():
        state = json.loads(cipher.decrypt(STATE.read_bytes()))
    elif mode == 'retry-login':
        state = {}
    else:
        # Cache loss must not create repeated new login attempts.
        print('STATE_MISSING: Run retry-login manually once.')
        raise RuntimeError('STATE_MISSING')
    if mode == 'retry-login':
        state['blocked'] = False
        state.pop('error_at', None)
    persist = lambda: save(state, cipher)
    try:
        if state.get('blocked'):
            raise RuntimeError('LOGIN_PAUSED')
        kind, signature = read_view(state, persist)
        apply_observation(state, kind, signature, notify)
        state.pop('error_at', None)
        print('CHECK_OK_' + kind.upper())
    except Exception:
        if time.time() - state.get('error_at', 0) > 86400:
            notify('Schichtprüfung gestört oder Anmeldung pausiert. Bitte GitHub Actions prüfen. Keine zuverlässige Überwachung bis zur Behebung.')
            state['error_at'] = time.time()
        raise
    finally:
        persist()


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) == 2 else 'check'
    if mode not in {'check', 'retry-login', 'notification-test'}:
        sys.exit(2)
    try:
        main(mode)
    except Exception:
        # Never log exception details, page HTML, credentials, or cookies.
        print('CHECK_FAILED: configuration, login, page or delivery needs checking.')
        sys.exit(1)
