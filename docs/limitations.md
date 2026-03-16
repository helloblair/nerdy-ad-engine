# Known Limitations — Nerdy Ad Engine

## Data & Research Limitations

- **~~No live Meta Ad Library scraping.~~** Resolved. A Playwright-based scraper (`competitor_scraper.py`) now collects active ads from 8 competitors via Meta Ad Library. Only active ads running 30+ days are fed into the generation pipeline. Remaining limitation: Meta's Ad Library DOM is unstable, so scraper selectors may need updating when Meta redesigns. The scraper runs on-demand (not scheduled), so competitor data goes stale between manual runs.
- **No real A/B testing.** There is no click-through rate, conversion data, or impression data from live campaigns. The evaluation is purely LLM-as-judge — the system has never verified whether a high-scoring ad actually performs well in the real ad auction. The human survey provides a proxy signal, but it's not the same as live campaign metrics.
- **No video generation.** The pipeline generates ad copy and static images (via Imagen 4) but no video creative. Real paid social increasingly favors short-form video (Reels/Stories). Video generation would require a different model pipeline.
- **Facebook and Instagram only.** No TikTok, YouTube, Google Ads, or other platform support. Ad copy conventions differ significantly across platforms (character limits, tone expectations, CTA formats), so extending this would require platform-specific writer prompts and evaluation criteria.

## Evaluation & Quality Limitations

- **Quality ratchet is conservative and AI-only.** The dynamic threshold (quality ratchet) uses the 25th percentile of approved scores with a gradual ramp (+0.5 per 10 ads, ceiling at 9.0). It requires 10+ approved ads to activate. The ratchet is stateless (recomputed from DB each run) and deterministic — it doesn't incorporate human ratings or conversion data, only AI evaluator scores. A production system should calibrate the ratchet against human agreement, not just AI scores. The ratchet floor is the evaluator's `THRESHOLD` (7.0) and it can only go up, never down.
- **Human confusion matrix: 43.3% precision.** When the AI evaluator approves an ad, humans only agree 43.3% of the time. The AI is too lenient. This is the system's most important known gap. The evaluator needs recalibration using the human ratings as ground truth, but that feedback loop is not yet automated.
- **~~Emotional resonance underweighted at 15%.~~** Resolved. Reweighted to 35% (text-only) / 25% (with image) based on survey data from 146 parents showing it's the #1 predictor of human approval. Now the highest-weighted dimension in both evaluation modes.
- **Evaluator confidence doesn't correlate well with accuracy.** The evaluator reports confidence scores per dimension, but high confidence (0.85+) doesn't reliably predict human agreement. Confidence calibration against the human ratings dataset hasn't been done yet.

## Infrastructure & Operations Limitations

- **Langfuse cost estimates are approximations.** Token counting uses `len(text) / 4` as a rough heuristic, not actual API-reported token counts. Real costs may vary 10-20% from estimates. Gemini and Claude don't return token counts in the same format, so unifying them would require per-model parsing.
- **Supabase timeout observed once during scale run.** During a 10-campaign batch run, one Supabase insert timed out. Retry logic (3 attempts with 1s delay) was added post-discovery in `pipeline.py`, but the root cause (connection pool exhaustion? Supabase free-tier limits?) was not fully diagnosed.
- **SQLite and Supabase schemas must be manually kept in sync.** The `db.py` abstraction layer handles reads and writes uniformly, but DDL changes (new columns, new tables) require manual updates to both `schema.sql` (SQLite) and the Supabase dashboard. There is a `migrations.py` but it's not a full migration framework — it's a manual script.
- **Single Fly.io region (dfw).** No geo-distributed deployment. All API requests route to Dallas regardless of user location. For a demo this is fine; for production, multi-region deployment or edge caching would be needed.
- **No authentication or rate limiting beyond ad caps.** The API has a global 500-ad cap and 10-ads-per-campaign cap, but no user authentication, API keys, or per-user rate limiting. Anyone with the URL can create campaigns.

## Pipeline Limitations

- **VT reference ads are static JSON, not a living dataset.** The ResearcherAgent extracts VT's own patterns from a fixed file (`reference_ads/varsity_tutors.json`). As Varsity Tutors' creative strategy evolves, these reference patterns become stale. Competitor data is now refreshable via `competitor_scraper.py`, but VT's own reference ads still require manual curation.
- **Fixer has dimension-specific strategies that are hand-written.** The `DIMENSION_STRATEGIES` dict in `fixer_agent.py` contains manually authored fix strategies for each dimension. These are effective but not learned from data — they're based on my analysis of the reference ads, not on what actually improved scores in past runs.
- **Max 3 iterations is a hard cap, not adaptive.** Some ads might converge faster (1 iteration), others might need 5. The 3-iteration cap is fixed. The pipeline doesn't adjust iteration budget based on how close the score is to threshold or how much improvement each iteration yields.
- **Writer retries on JSON parse failure, not on quality.** If the writer's output can't be parsed as JSON, it retries up to 3 times. But if the output is valid JSON that contains low-quality copy, there's no pre-evaluation quality gate — it goes straight to the evaluator.
