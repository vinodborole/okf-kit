# okf-kit — launch playbook

Internal go-to-market notes + ready-to-paste launch copy. Not part of the
package or the website. If you'd rather keep this private, `git rm` it or add
`MARKETING.md` to `.gitignore`.

**The wedge (lead with this, not the platform):**
> Your coding agent has stale docs. okf-kit crawls any docs site into a local
> knowledge base your agent reads over MCP — or chat with it offline via
> Ollama. **No API key.**

The OKF-format / Google-interop story is the *credibility* layer — paragraph
two, never the headline.

---

## 0 · Pre-launch checklist (do before posting anything)

- [ ] 45–60s demo recorded (asciinema + short screen capture) — see §1
- [ ] README top-fold: GIF, one-line pitch, 3-command quickstart, badges
- [ ] Landing page live: https://vinodborole.github.io/okf-kit/ ✅
- [ ] OG share image wired ✅ (`docs/og.png`)
- [ ] Registry seeded (rust-book, backstage-book, fastapi, flask, httpx) ✅
- [ ] Listed in MCP directories + awesome-lists (§4) — do quietly first
- [ ] A friendly note to the OKF authors (§4) — highest-leverage credibility

---

## 1 · The 45–60s demo (the single most important asset)

**Story beats:** stale docs → one command → agent/offline answer → "no key."

### asciinema recipe (terminal cast)
```bash
# install once: pipx install asciinema   (or pip install asciinema)
asciinema rec okf-demo.cast -c "bash"     # records a fresh shell; type slowly

# --- inside the recording, run these with small pauses ---
pip install okf-kit
okf build https://fastapi.tiangolo.com/tutorial/ -o fastapi-book
#  ✓ 51 pages → fastapi-book  (CONFORMANT)   — point out: no API key, no browser
okf chat fastapi-book --provider ollama
#  you> how do I declare a query parameter with a default?
#  (answer streams, with a [tutorial/query-params.md] citation) — fully offline
# Ctrl-D to leave chat, Ctrl-D to end the recording

# turn it into a GIF for social (agg = asciinema's gif renderer):
#   cargo install --git https://github.com/asciinema/agg   (or: brew install agg)
agg --theme monokai --font-size 24 okf-demo.cast okf-demo.gif
```

### The MCP beat (screen capture, ~15s)
Open Claude Code / Cursor, run `okf serve-mcp fastapi-book`, then ask the agent
a FastAPI question and show it calling `search_bundle` / `read_concept`. The
punchline card at the end: **“No API key. Works offline. One command.”**

Keep the whole thing under a minute. Post the GIF inline everywhere; link the
full cast/video for those who want more.

---

## 2 · Show HN

**Title** (≤ 80 chars, no emoji, no hype):
```
Show HN: okf-kit – turn any website into offline, agent-readable docs (no LLM)
```

**Post body:**
```
I kept hitting the same wall: my coding agents (Claude Code, Cursor) have
stale training data for fast-moving libraries, and every "docs to AI" tool
wanted an API key, a vector DB, and a cloud account just to read a website.

okf-kit is a small Python library that crawls any docs site into a portable
"bundle" of plain markdown files — Google's Open Knowledge Format — that
agents, tools, and humans can all read. The whole build path (crawl,
structure, validate) runs with no LLM and no API key. It installs in seconds
(no headless browser).

  pip install okf-kit
  okf build https://your-docs.example.com -o my-book   # → folder of markdown
  okf chat my-book --provider ollama                   # ask it, fully offline
  okf serve-mcp my-book                                # give it to Claude Code/Cursor

A bundle is just a git-friendly folder, so you can diff it, zip it, and share
it. There's a small community registry (`okf get <name>`) with a few starter
bundles (Rust book, FastAPI, Flask, HTTPX, Backstage).

OKF is a Google-authored spec; okf-kit is an independent, unofficial
implementation of it — and they interoperate (okf-kit validates and renders
Google's own sample bundles). Where Google's reference agent targets BigQuery
metadata with an LLM, okf-kit targets any website deterministically with no
key, and adds incremental sync, offline chat, MCP, and the registry.

Apache-2.0. Repo: https://github.com/vinodborole/okf-kit
Site: https://vinodborole.github.io/okf-kit/

Honest about limits: JS-heavy sites need the optional `[js]` extra (a real
browser); extraction quality varies by site; it's early (v0.2). Feedback very
welcome — especially on crawl quality and what bundles you'd want.
```

**Your first top-comment** (post right after, adds the "why" without cluttering the OP):
```
A couple of design choices behind the "no LLM" part, since it's the thing
people ask about:

- The crawler is deterministic (httpx + trafilatura), not an LLM deciding what
  to fetch — so builds are reproducible and free. An LLM is optional and only
  used if you want `okf chat` with a hosted model or `--enrich`.
- Chat has a zero-key retrieval fallback, so `okf chat <bundle>` answers with
  citations even with no model configured; point it at Ollama for synthesized
  answers offline.
- Edges in the graph/explorer come from in-content links only (nav/sidebar
  stripped), which matters a lot on docs sites — a Backstage bundle went from
  ~7,000 nav edges to ~550 real references.

Happy to answer anything about the crawl, the format, or the MCP server.
```

**Timing:** Tue–Thu, ~8–10am US Eastern. Then stay in the thread all day.

---

## 3 · Reddit + social

### r/LocalLLaMA (your best-fit audience — post here first)
**Title:** `Give your local model any website's docs, fully offline — no API key (okf-kit)`
```
I built a small tool to solve a personal annoyance: getting up-to-date library
docs into a local LLM without a cloud account.

`okf build <url>` crawls a docs site into a folder of plain markdown (Google's
Open Knowledge Format). No API key, no headless browser, installs in seconds.
Then `okf chat <bundle> --provider ollama` lets you ask questions fully
offline, with citations — or `okf serve-mcp` exposes it to Claude Code/Cursor.

Bundles are just git-friendly folders you can share; there's a tiny registry
(`okf get fastapi-book`, `rust-book`, `flask-book`, …).

Apache-2.0, pip install okf-kit. Repo + demo in comments. Would love feedback
on crawl quality and which docs you'd want as ready-made bundles.
```
(Drop the GitHub link + GIF as the first comment, not in the post — some subs
auto-filter link posts.)

### X / Twitter thread
```
1/ Your coding agent's docs are stale. And every "docs → AI" tool wants an API
key + a vector DB + a cloud account.

okf-kit turns any website into a folder of markdown your agent can read.
No LLM. No browser. pip install, one command. 🧵

2/ okf build https://fastapi.tiangolo.com/tutorial/ -o fastapi-book
→ 51 pages of clean markdown, validated, in seconds.
The crawler is deterministic — no model deciding what to fetch, so it's free
and reproducible.

3/ Then use it however you like:
• okf chat fastapi-book --provider ollama   (offline, with citations)
• okf serve-mcp fastapi-book                (Claude Code / Cursor over MCP)
• okf visualize fastapi-book                (a readable explorer)

4/ A bundle is just a git folder of markdown + YAML. Diff it, zip it, share it.
There's a community registry too: `okf get rust-book`. Add yours and it shows
up automatically.

5/ It implements Google's Open Knowledge Format spec — and interoperates:
okf-kit validates & renders Google's own sample bundles. Same format, but
any website, no cloud, no key.

6/ Apache-2.0. Try it:
pip install okf-kit
https://vinodborole.github.io/okf-kit/
Feedback welcome 🙏  [attach the demo GIF]
```

### LinkedIn (data / enterprise-knowledge angle)
```
Most "knowledge for AI" tooling assumes a model API, a vector database, and a
cloud account. I wanted the opposite: take a URL, get a portable, versionable
knowledge asset — no LLM required.

okf-kit crawls any website into an Open Knowledge Format bundle: plain markdown
+ YAML, organized as a hierarchy, readable by humans and agents alike. It
installs in seconds, runs deterministically (no per-build model cost), and the
output is just a git folder you can review, diff, and share.

OKF is a Google-authored, vendor-neutral spec (from the Knowledge Catalog /
Dataplex world); okf-kit is an independent, lightweight implementation that
also does incremental sync, offline chat, an MCP server for coding agents, and
a community registry — and it's interoperable with Google's reference bundles.

Open source (Apache-2.0): https://vinodborole.github.io/okf-kit/
```

---

## 4 · Quiet credibility seeding (evergreen, before the "launch")

- **MCP directories:** mcp.so, glama.ai, PulseMCP, Smithery; PRs to
  `punkpeye/awesome-mcp-servers` and `modelcontextprotocol/servers`.
- **awesome-lists:** `vinta/awesome-python`, `awesome-mcp-servers`,
  `awesome-rag`, `e2b-dev/awesome-ai-agents`, `awesome-selfhosted`.
- **OKF authors (highest leverage):** open a friendly Discussion/issue on
  `GoogleCloudPlatform/knowledge-catalog` — "community implementation of OKF;
  it validates & renders your sample bundles" — and offer okf-kit as a link.
  An acknowledgement from the spec authors is worth more than any influencer.
- **Product Hunt:** optional; a spike + a backlink. Only after the above.

---

## 5 · Influencers — value-first, never cold asks

- Target **micro-creators (5–50k)** in MCP / Claude Code / Ollama / Python.
  They engage and convert far better than big names.
- **Give before you ask:** build a bundle of *their* project's or favorite
  tool's docs and send it as a gift ("made a local doc-chat for <X>").
- Be genuinely present in their replies for a while before any ask.
- Make the demo so clean they can screen-record it in 30 seconds.

---

## 6 · Cadence & metrics

- **Sequence, don't blast:** r/LocalLLaMA → blog post → Show HN → other subs →
  socials, spread over ~2 weeks. Be present in every thread.
- **Track:** GitHub stars (signal), PyPI downloads (real usage), registry PRs
  (community health), referral sources.
- **Realistic:** a good LocalLLaMA + HN run ≈ a few hundred stars + first
  outside contributors. This compounds over months; consistency beats one
  viral day.
- **"10 community bundles"** is itself a launch moment — engineer toward it.

---

## Don'ts
- No astroturfing, sockpuppets, or upvote-begging — communities detect it and
  it's reputational suicide.
- Don't copy-paste identical text everywhere; tailor each channel.
- Don't oversell. "No key, offline, one command" sells itself.
- Always be clear OKF is Google's spec and okf-kit is independent/unofficial.
