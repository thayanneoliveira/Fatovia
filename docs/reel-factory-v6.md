# V6 factory: release and caption contract

The factory selects a pending official document only if the existing independent documentary audit and live source check pass. It builds a 12-shot visual plan, unique episode seed, script, and a caption with two topic-specific questions, a respectful comment prompt, verified source link, editorial ID, and at most five topic/brand hashtags. No claim of hashtag-driven reach; measure comments/reach, shares/reach, retention when available. No unrelated tags, political persuasion or generic viral bait.

The schedule runs independently of publisher/radar state locks. Without an explicitly configured free-tier attestation it creates text/plan only; no TTS request. A generated MP4 is a review draft, never automatically approved by technical checks. Visual art is procedural and requires assessment for novelty and narrative quality.

Release sequence (trusted reviewer, existing guarded publisher):
1. Download the draft artifact. Review exact MP4 and caption independently for factual, audio, visual, technical and closing requirements. Write a review JSON with reviewer, scope=independent_final_media, checked_at (ISO offset), six review fields editorial_review/audio_review/visual_review/source_review/technical_review/closing_review=approved, and video_sha256/script_sha256/caption_sha256/logo_sha256 bound to report and actual bytes. No self-approval based on a successful render.
2. Run python -m fatovia.reel_release --bundle PATH --review REVIEW.json --stage host on a clean latest main checkout. Commit only the staged MP4 in docs/media/reels. Existing Pages deployment serves it. Do not add to queue yet.
3. On fresh main after Pages deployment, run the same command with --stage queue. It rechecks live source, documentary review, exact HTTP 200 MP4 bytes and approval. Commit only policy and state together, with concurrency/optimistic push; never overwrite an active transaction. Existing scheduled publisher checks quotas, account, hash, review, hosting, duplicate controls and reconciles. Do not trigger real Meta in CI. If blocked, other formats proceed.

Limitations: generic layouts are not guaranteed to reach owner-approved artistic quality; live full A/V render and actual hosting/publisher path still require verification. The branch CI is offline; no paid services or automatic approval. No minimum publication count.
