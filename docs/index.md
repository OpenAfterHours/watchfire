---
template: home.html
title: watchfire — Static analysis for UK regulatory citations in Python
description: watchfire is a static-analysis tool for UK financial regulatory citations in Python code. Annotate functions with the rule they implement; verify against a versioned snapshot of CRR and the PRA Rulebook.
hide:
  - navigation
  - toc
  - footer
---

<div class="watchfire-landing" markdown="0">

<!-- ===== Top nav ===== -->
<header class="nav">
  <div class="nav-inner">
    <a class="nav-brand" href="#top">
      <img src="assets/openafterhours_icon_512.png" alt="">
      <span class="org">OpenAfterHours</span>
      <span class="slash">/</span>
      <span class="name">watchfire</span>
    </a>
    <span class="nav-version">v0.1.0</span>
    <nav class="nav-links">
      <a href="#why">Why</a>
      <a href="#how">How it works</a>
      <a href="#grammar">Citation grammar</a>
      <a href="#roadmap">Roadmap</a>
      <a href="https://github.com/OpenAfterHours/watchfire" class="nav-github">
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 .5C5.65.5.5 5.66.5 12.02c0 5.09 3.29 9.4 7.86 10.93.58.1.79-.25.79-.55v-2.02c-3.2.7-3.88-1.37-3.88-1.37-.52-1.34-1.28-1.69-1.28-1.69-1.04-.72.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.03 1.76 2.69 1.25 3.35.95.1-.74.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.46.11-3.04 0 0 .96-.31 3.15 1.18a10.93 10.93 0 0 1 5.74 0c2.19-1.49 3.15-1.18 3.15-1.18.62 1.58.23 2.75.11 3.04.74.81 1.18 1.84 1.18 3.1 0 4.43-2.7 5.4-5.26 5.68.41.36.78 1.06.78 2.13v3.16c0 .31.21.66.8.55A11.51 11.51 0 0 0 23.5 12.02C23.5 5.66 18.35.5 12 .5z"/></svg>
        GitHub
      </a>
    </nav>
  </div>
</header>

<!-- ===== Hero ===== -->
<section class="hero" id="top">
  <div class="cite-bg" aria-hidden="true">
    <span style="top:8%;left:2%;font-size:12px;transform:rotate(-2deg)" class="lit">CRR Art. 153(1)(a)</span>
    <span style="top:46%;left:60%;font-size:16px;transform:rotate(1deg)">PRA Rulebook, Credit Risk, 3.2</span>
    <span style="top:78%;left:4%;font-size:11px;transform:rotate(-1deg)" class="lit">PS9/24</span>
    <span style="top:24%;left:44%;font-size:12px;transform:rotate(2deg)">SS1/23, paragraph 2.5</span>
    <span style="top:4%;left:68%;font-size:12px;transform:rotate(-3deg)" class="lit">CRR Art. 92</span>
    <span style="top:86%;left:38%;font-size:13px;transform:rotate(1.5deg)">Delegated Regulation 2018/171 Art. 3</span>
    <span style="top:38%;left:8%;font-size:14px;transform:rotate(-0.5deg)">CRR Article 4(1)(75)</span>
    <span style="top:2%;left:34%;font-size:10px;transform:rotate(2.5deg)" class="dim">CRR Art. 113</span>
    <span style="top:62%;left:78%;font-size:11px;transform:rotate(-1.5deg)">PRA Rulebook, Internal Capital Adequacy, 2.1</span>
    <span style="top:18%;left:84%;font-size:11px;transform:rotate(0.5deg)">CRR Art. 166</span>
    <span style="top:82%;left:70%;font-size:16px;transform:rotate(-2.5deg)" class="lit">CRR Art. 143</span>
    <span style="top:36%;left:54%;font-size:10px;transform:rotate(1deg)" class="dim">SS3/18</span>
    <span style="top:56%;left:12%;font-size:11px;transform:rotate(-2deg)">CRR Art. 142</span>
    <span style="top:12%;left:52%;font-size:10px;transform:rotate(2deg)" class="dim">CRR Art. 111</span>
    <span style="top:68%;left:32%;font-size:12px;transform:rotate(-1deg)" class="lit">PS5/23</span>
    <span style="top:92%;left:14%;font-size:11px;transform:rotate(1.5deg)">CRR Art. 154</span>
  </div>

  <div class="hero-inner">
    <div>
      <div class="hero-eyebrow">
        <span class="dot"></span>
        v0.1.0 <span class="sep">·</span> Static analysis <span class="sep">·</span> Python 3.11+
      </div>
      <h1>watchfire<span class="glyph">_</span></h1>
      <p class="hero-lead">Static analysis for UK financial regulatory citations in Python code.</p>
      <p class="hero-sub">Annotate functions with the rule they implement. <code>watchfire check</code> verifies each citation against a bundled, versioned snapshot of CRR and the PRA Rulebook — and breaks the build when the trail drifts.</p>
      <div class="hero-actions">
        <div class="install-pill">
          <span class="prompt">$&nbsp;</span>
          <span class="cmd">uv add watchfire</span>
          <button class="copy-btn">COPY</button>
        </div>
        <a class="btn btn-ghost" href="https://github.com/OpenAfterHours/watchfire">
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 .5C5.65.5.5 5.66.5 12.02c0 5.09 3.29 9.4 7.86 10.93.58.1.79-.25.79-.55v-2.02c-3.2.7-3.88-1.37-3.88-1.37-.52-1.34-1.28-1.69-1.28-1.69-1.04-.72.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.03 1.76 2.69 1.25 3.35.95.1-.74.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.46.11-3.04 0 0 .96-.31 3.15 1.18a10.93 10.93 0 0 1 5.74 0c2.19-1.49 3.15-1.18 3.15-1.18.62 1.58.23 2.75.11 3.04.74.81 1.18 1.84 1.18 3.1 0 4.43-2.7 5.4-5.26 5.68.41.36.78 1.06.78 2.13v3.16c0 .31.21.66.8.55A11.51 11.51 0 0 0 23.5 12.02C23.5 5.66 18.35.5 12 .5z"/></svg>
          View on GitHub
        </a>
      </div>
    </div>

    <div class="hero-window">
      <div class="win-head">
        <div class="win-dots"><span></span><span></span><span></span></div>
        <span class="win-title">src/myproj/irb.py</span>
        <span class="win-tag">@cites</span>
      </div>
      <div class="win-body">
        <span class="ln"><span class="kw">from</span> watchfire <span class="kw">import</span> cites</span>
        <span class="ln">&nbsp;</span>
        <span class="ln">&nbsp;</span>
        <span class="ln"><span class="dec">cites</span><span class="pun">(</span><span class="str">"CRR Art. 153(1)(a)"</span><span class="pun">)</span></span>
        <span class="ln"><span class="kw">def</span> <span class="name">corporate_rw</span><span class="pun">(</span>pd<span class="pun">:</span> <span class="kw">float</span><span class="pun">,</span> lgd<span class="pun">:</span> <span class="kw">float</span><span class="pun">,</span> m<span class="pun">:</span> <span class="kw">float</span><span class="pun">)</span> <span class="pun">-&gt;</span> <span class="kw">float</span><span class="pun">:</span></span>
        <span class="ln">&nbsp;&nbsp;&nbsp;&nbsp;<span class="com">"""Risk-weight under the IRB approach for corporates."""</span></span>
        <span class="ln">&nbsp;&nbsp;&nbsp;&nbsp;R <span class="pun">=</span> <span class="num">0.12</span> <span class="pun">*</span> <span class="pun">(</span><span class="num">1</span> <span class="pun">-</span> exp<span class="pun">(</span><span class="pun">-</span><span class="num">50</span> <span class="pun">*</span> pd<span class="pun">))</span> <span class="pun">/</span> <span class="pun">(</span><span class="num">1</span> <span class="pun">-</span> exp<span class="pun">(</span><span class="pun">-</span><span class="num">50</span><span class="pun">))</span></span>
        <span class="ln">&nbsp;&nbsp;&nbsp;&nbsp;<span class="kw">return</span> lgd <span class="pun">*</span> phi<span class="pun">(</span>...<span class="pun">)</span></span>
      </div>
      <div class="win-pin">
        <div class="pin-head">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2v6M8 8h8l-1 4-2 1v7l-1 1-1-1v-7l-2-1-1-4z"/></svg>
          Resolved
        </div>
        <div class="pin-body"><strong>CRR Art. 153</strong> — IRB risk weights</div>
        <div class="pin-meta">rulebook 2024-07-09 · checked in CI</div>
      </div>
    </div>
  </div>
</section>

<!-- ===== Dev strip ===== -->
<div class="devstrip">
  <div class="devstrip-inner">
    <span class="tag">Pre-release</span>
    <span class="body">This package is still in development and is not production ready. <em>v0.1 ships the grammar, decorator, and check.</em></span>
  </div>
</div>

<!-- ===== Why this exists ===== -->
<section class="section" id="why">
  <div class="section-inner">
    <div class="section-head">
      <div class="section-eyebrow">Why this exists</div>
      <h2>Today the audit trail is a <span class="accent">Word document</span> that drifts the moment anyone changes the code.</h2>
      <p class="section-sub">Regulatory engineering teams in UK banks need an auditable trail from every formula in their RWA / capital code back to a specific article of the CRR or rule in the PRA Rulebook. watchfire moves that mapping into the codebase, where it can be checked.</p>
    </div>

    <div class="why-grid">
      <div class="why-card before">
        <div class="why-tag">— Before</div>
        <h3>Compliance lives in a spreadsheet</h3>
        <p>A reviewer cross-references function names against a regulatory mapping document maintained by hand. The mapping is correct on Monday and stale by Friday.</p>
        <div class="why-trail">
          <div class="line"><span class="doc">capital_mapping_v17.xlsx</span></div>
          <div class="line"><span class="ref">CRR Art. 153</span> <span class="arrow">→</span> <span class="doc">corporate_rw()</span> <span class="x">✕ renamed</span></div>
          <div class="line"><span class="ref">CRR Art. 113</span> <span class="arrow">→</span> <span class="doc">sa_rw()</span> <span class="x">✕ moved</span></div>
          <div class="line"><span class="ref">SS1/23 §2.5</span> <span class="arrow">→</span> <span class="doc">validate()</span> <span class="x">✕ deleted</span></div>
        </div>
      </div>

      <div class="why-card after">
        <div class="why-tag">+ With watchfire</div>
        <h3>The mapping is the code</h3>
        <p>Citations live next to the implementation, get parsed into structured data, and are verified against a pinned snapshot of the rulebook on every commit. Drift becomes a failing CI check, not a Q3 audit finding.</p>
        <div class="why-trail">
          <div class="line"><span class="doc">@cites("CRR Art. 153(1)(a)")</span></div>
          <div class="line"><span class="ref">CRR Art. 153</span> <span class="arrow">→</span> <span class="doc">corporate_rw()</span> <span class="check">✓ resolved</span></div>
          <div class="line"><span class="ref">CRR Art. 113</span> <span class="arrow">→</span> <span class="doc">sa_rw()</span> <span class="check">✓ resolved</span></div>
          <div class="line"><span class="ref">SS1/23 §2.5</span> <span class="arrow">→</span> <span class="doc">validate()</span> <span class="check">✓ resolved</span></div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ===== How it works ===== -->
<section class="section subtle" id="how">
  <div class="section-inner">
    <div class="section-head">
      <div class="section-eyebrow">How it works</div>
      <h2>Three steps. No runtime wrapping.</h2>
      <p class="section-sub">The <code>@cites</code> decorator attaches the parsed citations to the function as a <code>tuple[Citation, ...]</code> on <code>__watchfire__</code> (stack decorators when a rule lives in more than one instrument) and returns the function unchanged. The AST walker reads your source without importing it.</p>
    </div>

    <div class="steps">
      <div class="step">
        <div class="step-head"><span class="step-num"></span><h3>Decorate</h3></div>
        <p>Tag every regulated function with the article it implements. Sub-paragraphs and points are first-class.</p>
        <pre><span class="kw">from</span> watchfire <span class="kw">import</span> cites

<span class="dec">cites</span><span class="pun">(</span><span class="str">"CRR Art. 153(1)(a)"</span><span class="pun">)</span>
<span class="kw">def</span> <span class="name">corporate_rw</span><span class="pun">(</span>...<span class="pun">):</span>
    <span class="com">"""IRB risk-weight for corporates."""</span></pre>
      </div>

      <div class="step">
        <div class="step-head"><span class="step-num"></span><h3>Configure</h3></div>
        <p>Pin a rulebook snapshot and declare which instruments your project is allowed to cite.</p>
        <pre><span class="com"># pyproject.toml</span>
<span class="head">[tool.watchfire]</span>
<span class="key">rulebook_version</span> <span class="pun">=</span> <span class="str">"2024-07-09"</span>
<span class="key">instruments</span> <span class="pun">=</span> <span class="pun">[</span><span class="str">"CRR"</span>, <span class="str">"PRA_RULEBOOK"</span>,
               <span class="str">"PS"</span>, <span class="str">"SS"</span><span class="pun">]</span>
<span class="key">source_paths</span> <span class="pun">=</span> <span class="pun">[</span><span class="str">"src"</span><span class="pun">]</span></pre>
      </div>

      <div class="step">
        <div class="step-head"><span class="step-num"></span><h3>Check</h3></div>
        <p>Run in CI. Unknown articles, unparseable citations, and missing instruments break the build.</p>
        <pre><span class="prompt">$</span> uv run watchfire check
<span class="ok">watchfire</span>: checked <span class="ok">47</span> citation(s);
          no issues found.

<span class="prompt">$</span> echo <span class="str">$?</span>
<span class="ok">0</span></pre>
      </div>
    </div>
  </div>
</section>

<!-- ===== Commands ===== -->
<section class="section" id="commands">
  <div class="section-inner">
    <div class="section-head">
      <div class="section-eyebrow">CLI surface</div>
      <h2>One command gates the build. <span class="accent">One produces the audit deliverable.</span></h2>
    </div>

    <div class="cmds">
      <div class="cmd-card gate">
        <div class="cmd-head">
          <div class="cmd-cmd">$ watchfire check</div>
          <h3>The CI gate</h3>
          <p class="cmd-sub">Reports unparsable citations and references that point at instruments or articles missing from the index. Non-zero exit on any failing finding.</p>
          <span class="cmd-flag">● Exits non-zero on drift</span>
        </div>
        <div class="cmd-out">
          <div><span class="prompt">$</span> uv run watchfire check</div>
          <div><span class="file">src/myproj/sa.py:31</span>: <span class="dim">sovereign_rw</span>:</div>
          <div>&nbsp;&nbsp;<span class="fail">unknown_article</span>: citation</div>
          <div>&nbsp;&nbsp;<span class="ref">'CRR Art. 999'</span> points to CRR</div>
          <div>&nbsp;&nbsp;Article 999, which is not in the</div>
          <div>&nbsp;&nbsp;bundled rulebook index</div>
          <div class="dim">&nbsp;</div>
          <div><span class="head">watchfire</span>: <span class="fail">1 failing finding(s)</span>,</div>
          <div>&nbsp;&nbsp;0 unresolved, out of 12 resolved.</div>
          <div class="dim">&nbsp;</div>
          <div><span class="prompt">$</span> echo $?</div>
          <div><span class="fail">1</span></div>
        </div>
      </div>

      <div class="cmd-card audit">
        <div class="cmd-head">
          <div class="cmd-cmd">$ watchfire matrix</div>
          <h3>The traceability matrix</h3>
          <p class="cmd-sub">Reverse lookup: for every cited article, the functions that cite it. Suitable as a PR comment, an audit artifact, or a downstream JSON feed.</p>
          <span class="cmd-flag">○ Always exits 0 — informational</span>
        </div>
        <div class="cmd-out">
          <div><span class="prompt">$</span> uv run watchfire matrix</div>
          <div><span class="ref">CRR Art. 4(1)(75)</span> <span class="dim">Definitions: corporate</span></div>
          <div>&nbsp;&nbsp;<span class="file">irb.py:21</span> <span class="underline">is_corporate</span></div>
          <div class="dim">&nbsp;</div>
          <div><span class="ref">CRR Art. 113</span> <span class="dim">SA risk weights</span></div>
          <div>&nbsp;&nbsp;<span class="file">sa.py:6</span> <span class="underline">calculate_sa_rwa</span></div>
          <div class="dim">&nbsp;</div>
          <div><span class="ref">CRR Art. 153</span> <span class="dim">IRB risk weights</span></div>
          <div>&nbsp;&nbsp;<span class="file">irb.py:7</span> <span class="underline">corporate_rw</span></div>
          <div class="dim">&nbsp;</div>
          <div><span class="head">watchfire matrix</span>: 4 entries,</div>
          <div>&nbsp;&nbsp;4 sites across 4 functions.</div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ===== Grammar ===== -->
<section class="section subtle" id="grammar">
  <div class="section-inner">
    <div class="section-head">
      <div class="section-eyebrow">Citation grammar</div>
      <h2>Canonical UK regulatory citation strings, parsed into <span class="accent">structured data</span>.</h2>
      <p class="section-sub">The keyword for an article accepts <code>Art</code>, <code>Art.</code>, <code>Article</code>, or <code>article</code> in any case. Whitespace is normalised. Anything that doesn't parse raises <code>CitationParseError</code> with the offending input.</p>
    </div>

    <div class="grammar-wrap">
      <table class="grammar">
        <thead><tr><th>Input</th><th>Meaning</th></tr></thead>
        <tbody>
          <tr><td class="cite">CRR Art. 153</td><td class="mean">Whole article</td></tr>
          <tr><td class="cite">CRR Article 153<span class="alt"> &nbsp;— alternate spelling</span></td><td class="mean faint">(see row above)</td></tr>
          <tr><td class="cite">CRR Art. 153(1)</td><td class="mean">Paragraph</td></tr>
          <tr><td class="cite">CRR Art. 153(1)(a)</td><td class="mean">Point</td></tr>
          <tr><td class="cite">CRR Art. 153(1)(a)(ii)</td><td class="mean">Sub-point</td></tr>
          <tr><td class="cite">CRR Art. 4(1)(75)</td><td class="mean">Numeric point (definitions)</td></tr>
          <tr><td class="cite">PRA Rulebook, Credit Risk, 3.2</td><td class="mean">Rulebook section</td></tr>
          <tr><td class="cite">PS9/24</td><td class="mean">Policy Statement, whole document</td></tr>
          <tr><td class="cite">SS1/23, paragraph 2.5</td><td class="mean">Supervisory Statement with paragraph</td></tr>
          <tr><td class="cite">Delegated Regulation 2018/171 Art. 3</td><td class="mean">UK on-shored EU Delegated Regulation</td></tr>
        </tbody>
      </table>
      <div class="grammar-foot">
        <span>Instruments: <strong>CRR</strong> · <strong>PRA_RULEBOOK</strong> · <strong>PS</strong> · <strong>SS</strong> · <strong>DELEGATED_REG</strong></span>
        <span>Output: <strong>Citation</strong> (frozen dataclass)</span>
      </div>
    </div>
  </div>
</section>

<!-- ===== Roadmap ===== -->
<section class="section" id="roadmap">
  <div class="section-inner">
    <div class="section-head">
      <div class="section-eyebrow">Roadmap</div>
      <h2>A narrow vertical slice, then expand.</h2>
      <p class="section-sub">v0.1 is the foundation: get the citation grammar right against real usage in <code>rwa_calculator</code>, ship the decorator and CLI, then build out. If you have feedback on the grammar, open an issue — getting it wrong now is much cheaper to fix than getting it wrong later.</p>
    </div>

    <div class="roadmap">
      <div class="milestone active">
        <div class="ms-ver">v0.1 <span class="ms-status">Shipped</span></div>
        <h3>Grammar &amp; check</h3>
        <ul>
          <li>Citation grammar + <code>parse_citation</code></li>
          <li><code>@cites</code> decorator — runtime no-op</li>
          <li><code>watchfire check</code> CLI</li>
          <li>Bundled CRR index (Arts. 4, 92, 107, 111, 113, 114, 142, 143, 153, 154, 166)</li>
        </ul>
      </div>
      <div class="milestone next">
        <div class="ms-ver">v0.2 <span class="ms-status">Next</span></div>
        <h3>Audit deliverables</h3>
        <ul>
          <li><code>watchfire matrix</code> — traceability output</li>
          <li><code>watchfire stale</code> — rulebook diff vs index</li>
          <li><code>--format markdown / json</code> for PRs &amp; tooling</li>
        </ul>
      </div>
      <div class="milestone">
        <div class="ms-ver">v0.3+ <span class="ms-status">Planned</span></div>
        <h3>Live rulebook</h3>
        <ul>
          <li>Automated scrape of legislation.gov.uk</li>
          <li>Automated scrape of the PRA Rulebook</li>
          <li>Test-to-citation mapping</li>
        </ul>
      </div>
    </div>
  </div>
</section>

<!-- ===== CTA strip ===== -->
<section class="cta-strip">
  <div class="cite-bg" aria-hidden="true">
    <span style="top:8%;left:2%;font-size:12px;transform:rotate(-2deg)" class="lit">CRR Art. 153(1)(a)</span>
    <span style="top:46%;left:60%;font-size:16px;transform:rotate(1deg)">PRA Rulebook, Credit Risk, 3.2</span>
    <span style="top:78%;left:4%;font-size:11px;transform:rotate(-1deg)" class="lit">PS9/24</span>
    <span style="top:24%;left:44%;font-size:12px;transform:rotate(2deg)">SS1/23, paragraph 2.5</span>
    <span style="top:4%;left:68%;font-size:12px;transform:rotate(-3deg)" class="lit">CRR Art. 92</span>
  </div>
  <div class="cta-inner">
    <div>
      <h2>Put the audit trail next to the code.</h2>
      <p class="cta-sub">watchfire is Apache 2.0 and Python 3.11+. The first real user is <code>OpenAfterHours/rwa_calculator</code>. If you're building something similar, open an issue with the citations you'd like the parser to accept — that's the most useful feedback we can get right now.</p>
    </div>
    <div class="cta-actions">
      <div class="install-pill"><span class="prompt">$&nbsp;</span><span class="cmd">uv add watchfire</span><button class="copy-btn">COPY</button></div>
      <div class="install-pill"><span class="prompt">$&nbsp;</span><span class="cmd">pip install watchfire</span><button class="copy-btn">COPY</button></div>
      <a class="btn btn-primary" href="https://github.com/OpenAfterHours/watchfire">
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 .5C5.65.5.5 5.66.5 12.02c0 5.09 3.29 9.4 7.86 10.93.58.1.79-.25.79-.55v-2.02c-3.2.7-3.88-1.37-3.88-1.37-.52-1.34-1.28-1.69-1.28-1.69-1.04-.72.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.03 1.76 2.69 1.25 3.35.95.1-.74.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.46.11-3.04 0 0 .96-.31 3.15 1.18a10.93 10.93 0 0 1 5.74 0c2.19-1.49 3.15-1.18 3.15-1.18.62 1.58.23 2.75.11 3.04.74.81 1.18 1.84 1.18 3.1 0 4.43-2.7 5.4-5.26 5.68.41.36.78 1.06.78 2.13v3.16c0 .31.21.66.8.55A11.51 11.51 0 0 0 23.5 12.02C23.5 5.66 18.35.5 12 .5z"/></svg>
        Open the Repository
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
      </a>
    </div>
  </div>
</section>

<!-- ===== Footer ===== -->
<footer class="footer">
  <div class="footer-inner">
    <div class="foot-brand">
      <div class="lock">
        <img src="assets/openafterhours_icon_512.png" alt="">
        <strong>watchfire</strong>
      </div>
      <p>Open source regulatory tools for the financial industry. Built after hours, with care.</p>
      <span class="lic">Apache-2.0 · © OpenAfterHours</span>
    </div>
    <div class="foot-col">
      <h4>Project</h4>
      <ul>
        <li><a href="https://github.com/OpenAfterHours/watchfire">Repository<span class="ext">↗</span></a></li>
        <li><a href="https://github.com/OpenAfterHours/watchfire/issues">Issues<span class="ext">↗</span></a></li>
        <li><a href="https://github.com/OpenAfterHours/watchfire/blob/master/CHANGELOG.md">Changelog<span class="ext">↗</span></a></li>
        <li><a href="https://github.com/OpenAfterHours/watchfire/blob/master/LICENSE">Licence<span class="ext">↗</span></a></li>
      </ul>
    </div>
    <div class="foot-col">
      <h4>Docs</h4>
      <ul>
        <li><a href="#how">Quickstart</a></li>
        <li><a href="#grammar">Citation grammar</a></li>
        <li><a href="#commands">CLI reference</a></li>
        <li><a href="#roadmap">Roadmap</a></li>
      </ul>
    </div>
    <div class="foot-col">
      <h4>OpenAfterHours</h4>
      <ul>
        <li><a href="https://github.com/OpenAfterHours/rwa_calculator">rwa_calculator<span class="ext">↗</span></a></li>
        <li><a href="https://github.com/OpenAfterHours">Org on GitHub<span class="ext">↗</span></a></li>
      </ul>
    </div>
  </div>
  <div class="foot-bot">
    <span><span class="prompt">$</span>_ built after hours.</span>
    <span>watchfire@0.1.0 · rulebook 2024-07-09</span>
  </div>
</footer>

</div>
