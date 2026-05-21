# Scoreboard Correlation Debugging

Use backend commands to debug a missing public scoreboard button on an RCON
historical match. Normal frontend payloads and pages should stay free of
correlation diagnostics.

## Sequence

1. Refresh trusted public scoreboard candidates for the relevant server:

   ```powershell
   docker compose exec backend python -m app.scoreboard_candidate_backfill --server comunidad-hispana-02 --from 2026-05-20T00:00:00Z --to 2026-05-21T23:59:59Z --max-pages 5 --page-size 100
   ```

2. Scan existing materialized RCON matches against those candidates:

   ```powershell
   docker compose exec backend python -m app.rcon_scoreboard_relink --server comunidad-hispana-02
   ```

3. Inspect one match correlation:

   ```powershell
   docker compose exec backend python -m app.scoreboard_correlation_diagnostics --server comunidad-hispana-02 --match comunidad-hispana-02:1779310451:1779315851:foywarfare
   ```

4. Verify the detail endpoint used by the match page:

   ```powershell
   Invoke-WebRequest 'http://localhost:8000/api/historical/matches/detail?server=comunidad-hispana-02&match=comunidad-hispana-02%3A1779310451%3A1779315851%3Afoywarfare' | Select-Object -ExpandProperty Content
   ```

## Reading Output

The diagnostic JSON includes the RCON match window, score, candidate search
window, safe top candidate summaries, the selected candidate when one is strong
enough, and `final_reason`.

- `linked` means the detail read model can expose the trusted `match_url`.
- `no-safe-candidate` means candidate persistence or map/window matching needs
  inspection.
- `low-confidence` means candidates exist but evidence is insufficient.
- `ambiguous-candidate` means two candidates tie and no public URL is selected.
- `unsafe-url` in a candidate summary means the raw candidate URL is not emitted
  or selected.
