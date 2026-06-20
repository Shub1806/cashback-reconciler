# cashback-reconciler

A trust-first cashback reconciliation layer (US market). It answers the question
no other tool does: **did the cashback you were promised actually post?**

This is the MVP scaffold. The deterministic core — merchant matching, the
reconciliation matcher, and the reliability index — is fully implemented and
tested. The two integration points (email extraction, Plaid) are scaffolded with
the real prompts/mappings and just need API keys.

See **[SPEC.md](SPEC.md)** for the full design, rationale, and build order.

## Run it now (no keys)

```bash
python3 demo.py            # full loop on offline mock data
python3 -m pytest -q       # 16 passing tests
```

Expected demo output: Blue Bottle's $10 credit is reconciled as POSTED,
Sweetgreen is flagged MISSING ("you appear to be owed $7.00"), Nike stays pending
under its min spend, and an issuer reliability score is computed.

## What's done vs. what needs you

| Component | File | Status |
|---|---|---|
| Data models | `src/models.py` | done |
| Merchant normalization + match | `src/merchant.py` | done, tested |
| Reconciliation matcher | `src/matcher.py` | done, tested |
| Reliability index (Wilson) | `src/reliability.py` | done, tested |
| Offline demo | `demo.py` | runnable |
| Email → Offer extraction | `src/extract.py` | scaffold + prompt; needs `LLM_*` env vars |
| Plaid received stream | `src/plaid_client.py` | stub + sample loader; needs Plaid keys |

## Next steps (in order)

1. Run `extract.py` against your own Amex/Chase offer emails; refine the prompt.
2. Wire Plaid `/transactions/sync`; **verify how statement credits appear** in
   the feed for your test cards (descriptor + sign) — the matcher depends on it.
3. Replace `load_sample_transactions()` with the live feed and run `reconcile`
   over your real offers.
4. Build the alert + claim helper on top of MISSING results.
5. Record it catching a real missing credit — that's the thing to show.

## Design stance

No merchant commissions — subscription only. The differentiator is that the
tool works for the user, not the merchant. Keep it that way.
