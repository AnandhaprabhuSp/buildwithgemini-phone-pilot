# My agent: PhonePilot (Pixel & Smartphone Advisor)
One-liner: A conversational shopping advisor that helps smartphone buyers compare devices (such as the Google Pixel 11 Pro), analyze point-by-point feature breakdowns, and calculate trade-in valuations and financing options across a catalog of modern smartphones.

Tool coverage:
- Memory: Remembers the user's current phone model, upgrade budget, preferred ecosystem, feature priorities (e.g., camera zoom, battery endurance, display refresh rate), and saved comparison shortlists across sessions.
- Tools: Smartphone spec retrieval (`get_phone_specs`), feature diff/comparison lookup (`compare_phones`), trade-in valuation estimator (`estimate_trade_in_value`), and monthly financing calculator (`calculate_financing`).
- Catalog/UI: A rich smartphone catalog rendering A2UI product cards with hero images, key feature bullet cards, and side-by-side spec/price comparison tables.
- Image gen: Generates crisp product visualization images (e.g., Pixel in custom color finishes like Obsidian, Porcelain, Hazel, or lifestyle shots).
- Sandbox: Code sandbox execution to compute multi-tier financing amortization, trade-in credit deductions, and sales tax adjustments.

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch (pick what fits): Code sandbox for loan/amortization computation, RAG Engine for grounding on official spec sheets and user review transcripts, Cloud Trace for observability.
