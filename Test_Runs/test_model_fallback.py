"""Google AI fallback model (GOOGLE_AI_FALLBACK_MODEL) — no real AI, no network.

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_model_fallback.py
A fake urlopen makes the primary model answer HTTP 503 / time out and the fallback model answer.
Checks every call type, that other errors don't use the fallback, the old behaviour without a
fallback, and end to end: task insights + farm report use the fallback's answer (not the
basic summary) and record which model answered.
"""
import io
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILED = []


def check(cond, label):
    print(f"  {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        FAILED.append(label)


PRIMARY, FALLBACK = "gemma-primary", "fallback-lite"
FAKE = {"primary": "503", "fallback": None, "fallback_text": "fallback answer", "calls": []}


class _Resp:
    def __init__(self, body: bytes, lines=None):
        self._body, self._lines = body, lines or []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._body

    def __iter__(self):
        return iter(self._lines)


def _answer(text):
    return json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}}]}).encode()


def fake_urlopen(req, timeout=None):
    url = req.full_url if hasattr(req, "full_url") else str(req)
    if url.split("?")[0].endswith("/models"):              # startup model list
        return _Resp(json.dumps({"models": [{"name": f"models/{PRIMARY}",
                                             "supportedGenerationMethods": ["generateContent"]}]}).encode())
    model = PRIMARY if f"/models/{PRIMARY}:" in url else FALLBACK
    FAKE["calls"].append(model)
    FAKE.setdefault("timeouts", []).append(timeout)
    mode = FAKE["primary"] if model == PRIMARY else FAKE["fallback"]
    if mode == "503":
        raise urllib.error.HTTPError(url, 503, "Service Unavailable", None,
                                     io.BytesIO(b'{"error": {"code": 503, "message": "high demand"}}'))
    if mode == "429":
        raise urllib.error.HTTPError(url, 429, "Too Many Requests", None,
                                     io.BytesIO(b'{"error": {"code": 429, "message": "quota"}}'))
    if mode == "400":
        raise urllib.error.HTTPError(url, 400, "Bad Request", None, io.BytesIO(b'{"error": {"code": 400}}'))
    if mode == "timeout":
        raise TimeoutError("The read operation timed out")
    text = FAKE["fallback_text"] if model == FALLBACK else "primary answer"
    if ":streamGenerateContent" in url:
        lines = [b"data: " + json.dumps({"candidates": [{"content": {"parts": [{"text": w + " "}]}}]}).encode()
                 for w in text.split()]
        return _Resp(b"", lines)
    return _Resp(_answer(text))


def reset(primary, fallback=None, text="fallback answer"):
    FAKE.update(primary=primary, fallback=fallback, fallback_text=text, calls=[], timeouts=[])


_orig_urlopen = urllib.request.urlopen
urllib.request.urlopen = fake_urlopen
try:
    from app.services.ai_model_service.Gemma.google_ai_provider import GoogleAIProvider

    print("\n-- provider: every call type")
    p = GoogleAIProvider(api_key="test-key", model=PRIMARY, fallback_model=FALLBACK)
    check(p.fallback_model == FALLBACK, "fallback model read")

    reset("503")
    check(p.complete_direct("hi", timeout=5) == "fallback answer" and FAKE["calls"] == [PRIMARY, FALLBACK]
          and p.answered_model() == FALLBACK, f"direct: 503 → fallback answers, no same-model retry ({FAKE['calls']})")
    reset("timeout")
    check(p.complete_direct("hi", timeout=5) == "fallback answer" and p.answered_model() == FALLBACK,
          "direct: timeout → fallback answers")
    reset(None)
    check(p.complete_direct("hi", timeout=5) == "primary answer" and p.answered_model() == PRIMARY
          and FAKE["calls"] == [PRIMARY], "direct: primary fine → primary answers, fallback not called")
    reset("400")
    try:
        p.complete_direct("hi", timeout=5)
        check(False, "direct: HTTP 400 → raises, no fallback")
    except urllib.error.HTTPError:
        check(FAKE["calls"] == [PRIMARY], "direct: HTTP 400 → raises, no fallback")
    reset("503", fallback="503")
    try:
        p.complete_direct("hi", timeout=5)
        check(False, "direct: both 503 → raises")
    except urllib.error.HTTPError:
        check(FAKE["calls"] == [PRIMARY, FALLBACK] and p.answered_model() is None,
              "direct: both unavailable → raises after one fallback try")

    reset("503")
    out = p.complete("hi")
    check(out.startswith("fallback answer") and p.answered_model() == FALLBACK, f"complete (chat): 503 → fallback ({out!r})")
    reset("timeout")
    check(p.complete_json("hi") == "fallback answer" and p.answered_model() == FALLBACK, "complete_json: timeout → fallback")
    reset("503", text="streamed from fallback")
    streamed = "".join(p.stream_complete("hi")).strip()
    check(streamed == "streamed from fallback" and p.answered_model() == FALLBACK and FAKE["calls"] == [PRIMARY, FALLBACK],
          f"stream: 503 on connect → streamed by the fallback ({streamed!r})")

    print("\n-- chat fast path: one primary attempt, then straight to the fallback, no retries")
    for mode in ("503", "429", "timeout", "400"):
        reset(mode, text="chat from fallback")
        out = "".join(p.stream_complete_chat("hi")).strip()
        att = p.chat_attempts()
        check(out == "chat from fallback" and FAKE["calls"] == [PRIMARY, FALLBACK] and p.answered_model() == FALLBACK
              and [a["model"] for a in att] == [PRIMARY, FALLBACK] and att[1]["outcome"] == "ok",
              f"chat: {mode} on the primary → fallback at once ({[(a['model'], a['outcome']) for a in att]})")
    reset(None)
    check("".join(p.stream_complete_chat("hi")).strip() == "primary answer" and FAKE["calls"] == [PRIMARY]
          and p.answered_model() == PRIMARY, "chat: primary fine → primary answers, fallback not called")
    reset("503", fallback="503")
    out = "".join(p.stream_complete_chat("hi"))
    check(out.startswith("The AI advisor is not available") and FAKE["calls"] == [PRIMARY, FALLBACK],
          "chat: both unavailable → 'not available' after 2 calls (→ rule-based answer), no retries")
    p.CHAT_PRIMARY_S = -1.0                      # deadline already passed before the first answer token
    reset(None, text="chat from fallback")
    out = "".join(p.stream_complete_chat("hi")).strip()
    check(out == "chat from fallback" and p.chat_attempts()[0]["outcome"] == "timeout",
          f"chat: no answer token before the primary's deadline → fallback ({p.chat_attempts()})")
    del p.CHAT_PRIMARY_S
    reset("503", text="chat from fallback")
    "".join(p.stream_complete_chat("hi"))
    check(FAKE["timeouts"][0] == 8.0 and 14.0 <= FAKE["timeouts"][1] <= 15.0,
          f"chat: primary fails fast → the fallback gets the rest of the 15 s budget ({FAKE['timeouts']})")
    reset("503", fallback="timeout")
    out = "".join(p.stream_complete_chat("hi"))
    retry = p.complete_chat("hi", timeout=5)
    check(out.startswith("The AI advisor is not available") and retry.startswith("The AI advisor is not available")
          and FAKE["calls"] == [PRIMARY, FALLBACK],
          f"chat: fallback timeout → no retry, rule-based answer ({FAKE['calls']})")
    reset(None)
    "".join(p.stream_complete_chat("hi"))        # a normal chat call (resets the no-retry flag)
    reset("503", text="retry answer")
    check(p.complete_chat("hi", timeout=4) == "retry answer" and FAKE["calls"] == [FALLBACK],
          "chat retry (unusable answer): one non-streaming call on the fallback model")

    print("\n-- provider without a fallback (old behaviour)")
    p0 = GoogleAIProvider(api_key="test-key", model=PRIMARY, fallback_model="")
    reset("503")
    try:
        p0.complete_direct("hi", timeout=5)
        check(False, "no fallback: 503 → retries the same model once, then raises")
    except urllib.error.HTTPError:
        check(FAKE["calls"] == [PRIMARY, PRIMARY], "no fallback: 503 → retries the same model once, then raises")
    p_same = GoogleAIProvider(api_key="test-key", model=PRIMARY, fallback_model=PRIMARY)
    check(p_same.fallback_model is None, "fallback = primary model → treated as no fallback")

    print("\n-- end to end (task insights, farm report)")
    from run import app  # bootstrap(): fresh reseed of this test's database
    with app.app_context():
        from app.agents.coordinator_agent import CoordinatorAgent
        from app.services.ai_model_service import ai_model_service
        from app.services import task_insights_service as ti, farm_report_service as fr
        from app.services import insight_signals_service as sig
        from app.utils import clock

        from app.services import demo_scenario_service
        demo_scenario_service.apply(1, "typical")   # scenario 1: 7–8 May western disturbance
        CoordinatorAgent().daily_update(user_id=1, as_of_date=clock.today())
        snap = sig.collect(1, clock.today())
        signals, cands = sig.build_from(snap), ti.candidates(snap)
        season, changes = fr.season_lines(snap), ["This is the first farm report."]

        before = ai_model_service._fast_provider
        ai_model_service.register_fast_provider(p)
        try:
            reset("503", text=ti._placeholder_answer(signals, cands))
            r = ti.generate(1)
            check(not r["is_fallback"] and r["data"]["insights"] and r["model"] == f"Google AI/{FALLBACK} (fallback)",
                  f"task insights: primary 503 → fallback's answer used, not the basic summary (model {r['model']!r})")
            reset("503", fallback="503")
            r = ti.generate(1)
            check(r["is_fallback"] and "503" in (r["data"]["error"] or ""), "task insights: both 503 → basic summary")
            reset("timeout", text=fr._placeholder_answer(signals, season, changes))
            r = fr.generate(1)
            check(not r["is_fallback"] and r["data"]["headline"] and r["model"].endswith("(fallback)"),
                  f"farm report: primary timeout → fallback's answer used (model {r['model']!r})")
            reset(None, text="")
            FAKE["calls"] = []
            r = ti.generate(1)
            check(r["model"] == f"Google AI/{PRIMARY}" and FAKE["calls"] == [PRIMARY],
                  "primary fine → primary's answer, model recorded without '(fallback)'")
        finally:
            ai_model_service._fast_provider = before
finally:
    urllib.request.urlopen = _orig_urlopen

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
