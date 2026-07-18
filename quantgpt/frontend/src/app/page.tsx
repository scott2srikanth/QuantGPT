"use client";

import { useState } from "react";

type NavItem = { label: string; icon: string; badge?: string };

const navigation: NavItem[] = [
  { label: "Overview", icon: "⌂" },
  { label: "Signals", icon: "◈", badge: "12" },
  { label: "Portfolio", icon: "▣" },
  { label: "Watchlist", icon: "☆" },
  { label: "Risk", icon: "◉" },
  { label: "Strategy Performance", icon: "⌁" },
  { label: "Agent Status", icon: "✦" },
  { label: "Trade Journal", icon: "▤" },
  { label: "Reports", icon: "▱" },
  { label: "News", icon: "≡", badge: "8" },
  { label: "AI Reasoning", icon: "✧" },
];

const stats = [
  ["Portfolio value", "$248,420.82", "+$4,286.12", "up"],
  ["Today’s P&L", "+$2,184.60", "+0.89%", "up"],
  ["Buying power", "$72,185.24", "29.1% available", "neutral"],
  ["Portfolio heat", "4.2%", "Within 6.0% limit", "up"],
];

const watchlist = [
  ["NVDA", "NVIDIA Corp.", "$942.89", "+2.14%", "up"],
  ["MSFT", "Microsoft Corp.", "$418.56", "+0.76%", "up"],
  ["AAPL", "Apple Inc.", "$183.45", "−0.41%", "down"],
  ["TSLA", "Tesla Inc.", "$171.25", "+3.28%", "up"],
];

const positions = [
  ["NVDA", "Long · 120 shares", "$113,146", "+$3,744", "+3.42%", "up"],
  ["MSFT", "Long · 80 shares", "$33,485", "+$812", "+2.49%", "up"],
  ["AAPL", "Long · 60 shares", "$11,007", "−$104", "−0.93%", "down"],
  ["TLT", "Long · 200 shares", "$18,762", "+$318", "+1.72%", "up"],
];

function EquityChart() {
  return (
    <svg viewBox="0 0 720 225" className="chart-svg" role="img" aria-label="Equity curve">
      <defs>
        <linearGradient id="equityFill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#63e6be" stopOpacity=".32" />
          <stop offset="100%" stopColor="#63e6be" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[36, 82, 128, 174].map((y) => <line key={y} x1="0" x2="720" y1={y} y2={y} className="chart-grid" />)}
      <path d="M0 183 L34 176 L67 179 L101 158 L135 168 L169 138 L203 150 L237 142 L270 110 L304 118 L338 93 L372 104 L406 81 L440 94 L474 65 L508 76 L542 50 L576 62 L610 38 L644 45 L680 19 L720 28 L720 225 L0 225 Z" fill="url(#equityFill)" />
      <path d="M0 183 L34 176 L67 179 L101 158 L135 168 L169 138 L203 150 L237 142 L270 110 L304 118 L338 93 L372 104 L406 81 L440 94 L474 65 L508 76 L542 50 L576 62 L610 38 L644 45 L680 19 L720 28" className="equity-line" />
      <circle cx="680" cy="19" r="5" className="chart-dot" />
      <text x="0" y="218">MAY</text><text x="165" y="218">JUN</text><text x="340" y="218">JUL</text><text x="515" y="218">AUG</text><text x="680" y="218">SEP</text>
    </svg>
  );
}

function Bars() {
  const values = [38, 65, 45, 88, 55, 78, 42, 96, 60, 74, 50, 83];
  return <div className="bars">{values.map((value, i) => <div key={i} className={i === 7 ? "bar accent" : "bar"} style={{ height: `${value}%` }} />)}</div>;
}

function HeatMap() {
  const cells = ["#193d38", "#155348", "#225f50", "#7b342f", "#15463f", "#28725b", "#1c443d", "#632e2c", "#1e5145", "#319170", "#234d45", "#1c3837"];
  return <div className="heatmap">{cells.map((color, index) => <span key={index} style={{ background: color }} />)}</div>;
}

function PageHeading({ active }: { active: string }) {
  const descriptions: Record<string, string> = {
    Signals: "Ranked, explainable market opportunities from the research system.",
    Portfolio: "Capital allocation, exposure and live position performance.",
    Watchlist: "Symbols under active monitoring by your agents.",
    Risk: "Guardrails evaluated before any order reaches OpenAlgo.",
    "Strategy Performance": "Strategy attribution, reliability and recent execution quality.",
    "Agent Status": "Monitor the research and trading agents in real time.",
    "Trade Journal": "Every decision, execution and post-trade learning record.",
    Reports: "Exportable views of performance, exposure and risk.",
    News: "Market-moving context attached to active symbols.",
    "AI Reasoning": "Inspectable evidence behind each probabilistic forecast.",
  };
  return <section className="section-heading"><div><p className="eyebrow">WORKSPACE / {active.toUpperCase()}</p><h1>{active}</h1><p>{descriptions[active]}</p></div><button className="primary-button">+ New research</button></section>;
}

function DetailsPage({ active }: { active: string }) {
  if (active === "AI Reasoning") return <ReasoningPage />;
  const isRisk = active === "Risk";
  return <><PageHeading active={active} /><div className="content-grid"><section className="card full-height"><div className="card-head"><div><h2>{isRisk ? "Risk control centre" : `${active} feed`}</h2><p>{isRisk ? "All limits are live and enforced prior to order routing." : "Live workspace data will appear here as agents and integrations stream updates."}</p></div><span className="status-live"><i /> LIVE</span></div><div className="empty-state"><span>{isRisk ? "◉" : "✦"}</span><h3>{isRisk ? "Risk engine active" : `Your ${active.toLowerCase()} workspace is ready`}</h3><p>{isRisk ? "Orders are checked for exposure, loss limits, drawdown, correlation and portfolio heat before being sent to OpenAlgo." : "Select a research run or connect market data to begin populating this view."}</p></div></section><aside className="card"><h2>Quick metrics</h2><div className="mini-metrics"><div><span>Active signals</span><b>12</b></div><div><span>Approval rate</span><b>94.8%</b></div><div><span>Risk state</span><b className="positive">Normal</b></div></div></aside></div></>;
}

function ReasoningPage() {
  const [selected, setSelected] = useState("NVDA");
  const trade = selected === "NVDA" ? { symbol: "NVDA", side: "LONG", confidence: "82%", price: "$938.12", target: "$982.00", stop: "$911.50" } : { symbol: "MSFT", side: "LONG", confidence: "71%", price: "$417.80", target: "$435.00", stop: "$406.20" };
  return <><PageHeading active="AI Reasoning" /><section className="reasoning-layout"><aside className="card decision-list"><div className="card-head"><div><p className="eyebrow">PROPOSED TRADES</p><h2>Decision queue</h2></div><span className="status-live"><i /> LIVE</span></div>{[["NVDA", "Long", "82%", "High"], ["MSFT", "Long", "71%", "Medium"], ["AAPL", "No trade", "44%", "Low"]].map(([symbol, side, confidence, risk]) => <button onClick={() => setSelected(symbol === "MSFT" ? "MSFT" : "NVDA")} className={`decision-row ${selected === symbol ? "decision-selected" : ""}`} key={symbol}><span className="ticker-icon">{symbol[0]}</span><span><b>{symbol}</b><small>{side} · {confidence} confidence</small></span><em className={risk === "High" ? "risk-high" : ""}>{risk} risk</em></button>)}</aside><section className="decision-dossier"><article className="card dossier-hero"><div className="dossier-title"><div><p className="eyebrow">TRADE THESIS / PROBABILISTIC FORECAST</p><h2>{trade.symbol} <span>{trade.side}</span></h2><p>No certainty claimed. This is a research forecast with an estimated probability, not investment advice.</p></div><div className="confidence-ring"><b>{trade.confidence}</b><span>confidence</span></div></div><div className="trade-levels"><span><small>ENTRY ZONE</small><b>{trade.price}</b></span><span><small>EXPECTED RETURN</small><b className="positive">+4.68%</b></span><span><small>INVALIDATION</small><b>{trade.stop}</b></span><span><small>RISK / REWARD</small><b>2.7 : 1</b></span></div></article><div className="dossier-grid"><article className="card explanation-card"><p className="eyebrow">WHY THIS TRADE</p><h2>Supporting indicators</h2><ul className="evidence-list"><li><i className="check">✓</i><span><b>Trend confirmation</b><small>Price reclaimed the 20-day average; medium-term trend remains positive.</small></span></li><li><i className="check">✓</i><span><b>Volume expansion</b><small>Relative volume is 1.8× its 20-session average on the breakout.</small></span></li><li><i className="check">✓</i><span><b>Options positioning</b><small>Call skew and dealer gamma support upside momentum into earnings.</small></span></li></ul></article><article className="card explanation-card caution-card"><p className="eyebrow">WHY NOT / WHAT COULD CHANGE</p><h2>Risks to the thesis</h2><ul className="evidence-list"><li><i className="caution">!</i><span><b>Event volatility</b><small>Semiconductor earnings and Fed commentary can widen the expected range.</small></span></li><li><i className="caution">!</i><span><b>Concentration</b><small>Technology exposure would rise to 42.6%, near the portfolio sector limit.</small></span></li><li><i className="caution">!</i><span><b>Failed breakout</b><small>A close below $911.50 invalidates the setup and triggers reassessment.</small></span></li></ul></article></div><div className="dossier-grid"><article className="card sources-card"><div className="card-head"><div><p className="eyebrow">SUPPORTING NEWS</p><h2>Market context</h2></div><span className="source-count">3 sources</span></div><div className="source"><span>REUTERS</span><p>AI server demand continues to support data-centre spending forecasts.</p><small>Today · 42 min ago</small></div><div className="source"><span>MARKET DATA</span><p>Semiconductor index is leading the S&P 500 on breadth and volume.</p><small>Today · 1 hr ago</small></div></article><article className="card sources-card"><div className="card-head"><div><p className="eyebrow">SUPPORTING FUNDAMENTALS</p><h2>Business quality</h2></div><span className="source-count positive">Positive</span></div><div className="fundamentals"><span><small>REVENUE EST. REVISIONS</small><b className="positive">+6.2%</b></span><span><small>FORWARD P/E</small><b>36.8×</b></span><span><small>FREE CASH FLOW MARGIN</small><b>42.1%</b></span><span><small>EARNINGS DATE</small><b>May 22</b></span></div></article></div><article className="card approval-bar"><div><span className="approval-icon">✓</span><p><b>Risk Engine: eligible for approval</b><small>Position size is capped at 36 shares. Daily loss, heat, sector exposure and correlation checks currently pass.</small></p><button className="outline-button">Review risk checks</button><button className="primary-button">Approve trade</button></div></article></section></section></>;
}

export default function HomePage() {
  const [active, setActive] = useState("Overview");
  const [period, setPeriod] = useState("1M");
  if (active !== "Overview") return <main className="terminal"><Sidebar active={active} setActive={setActive} /><div className="workspace"><Topbar /><DetailsPage active={active} /></div></main>;
  return (
    <main className="terminal">
      <Sidebar active={active} setActive={setActive} />
      <div className="workspace">
        <Topbar />
        <section className="hero"><div><p className="eyebrow">GOOD MORNING, SRIKANTH</p><h1>Market intelligence,<br /><em>with conviction.</em></h1><p className="hero-copy">Your AI research desk is monitoring 842 signals across markets. Here’s what needs your attention.</p></div><div className="market-state"><span className="pulse" /><div><small>MARKET STATUS</small><b>US Market Open</b><p>Closes in 05:42:18</p></div></div></section>
        <section className="stat-grid">{stats.map(([label, value, change, state]) => <article className="stat-card" key={label}><span>{label}</span><strong>{value}</strong><small className={state}>{change}</small><div className="stat-spark"><i /><i /><i /><i /><i /><i /><i /></div></article>)}</section>
        <section className="dashboard-grid">
          <article className="card equity-card"><div className="card-head"><div><p className="eyebrow">PORTFOLIO PERFORMANCE</p><h2>Equity curve</h2></div><div className="period-switch">{["1W", "1M", "3M", "YTD"].map(item => <button className={period === item ? "selected" : ""} onClick={() => setPeriod(item)} key={item}>{item}</button>)}</div></div><div className="chart-number"><b>$248,420</b><span className="positive">+18.42% <small>all time</small></span></div><EquityChart /></article>
          <article className="card insight-card"><div className="card-head"><div><p className="eyebrow">AI PRIORITY SIGNAL</p><h2>NVDA · Long</h2></div><span className="confidence">82% confidence</span></div><p className="signal-copy">Momentum remains constructive as price reclaims the 20-day moving average on expanding volume.</p><div className="signal-metrics"><span><small>ENTRY</small><b>$938.12</b></span><span><small>TARGET</small><b>$982.00</b></span><span><small>RISK</small><b className="warning">Medium</b></span></div><button className="outline-button" onClick={() => setActive("AI Reasoning")}>Review AI reasoning <span>→</span></button></article>
          <article className="card pnl-card"><div className="card-head"><div><p className="eyebrow">DAILY P&L</p><h2>Execution rhythm</h2></div><b className="positive">+$2,184</b></div><Bars /><div className="axis-labels"><span>09:30</span><span>12:00</span><span>16:00</span></div></article>
          <article className="card allocation-card"><div className="card-head"><div><p className="eyebrow">SECTOR EXPOSURE</p><h2>Allocation</h2></div><button className="link-button" onClick={() => setActive("Portfolio")}>Details</button></div><div className="donut-wrap"><div className="donut"><b>64%</b><span>Equities</span></div><div className="legend"><span><i className="teal" />Technology <b>38.2%</b></span><span><i className="blue" />Fixed income <b>18.7%</b></span><span><i className="purple" />Healthcare <b>7.1%</b></span><span><i className="gray" />Cash <b>29.1%</b></span></div></div></article>
        </section>
        <section className="lower-grid"><article className="card table-card"><div className="card-head"><div><p className="eyebrow">ACTIVE POSITIONS</p><h2>Portfolio</h2></div><button className="link-button" onClick={() => setActive("Portfolio")}>View all positions</button></div><div className="position-table"><div className="table-head"><span>SYMBOL</span><span>MARKET VALUE</span><span>UNREALIZED P&L</span></div>{positions.map(row => <div className="position-row" key={row[0]}><div><b>{row[0]}</b><small>{row[1]}</small></div><span>{row[2]}</span><div className={row[5]}><b>{row[3]}</b><small>{row[4]}</small></div></div>)}</div></article><article className="card heat-card"><div className="card-head"><div><p className="eyebrow">STRATEGY PULSE</p><h2>Signal heatmap</h2></div><span className="status-live"><i /> LIVE</span></div><HeatMap /><div className="heat-legend"><span>Weak</span><i /><i /><i /><i /><span>Strong</span></div><div className="win-rate"><span>Win rate <b>68.4%</b></span><div><i /></div><small>+4.2% vs last 30d</small></div></article></section>
        <section className="bottom-grid"><article className="card watch-card"><div className="card-head"><div><p className="eyebrow">WATCHLIST</p><h2>High-conviction names</h2></div><button className="link-button" onClick={() => setActive("Watchlist")}>Open watchlist</button></div><div className="watch-list">{watchlist.map(row => <div key={row[0]}><span className="ticker-icon">{row[0][0]}</span><p><b>{row[0]}</b><small>{row[1]}</small></p><p><b>{row[2]}</b><small className={row[4]}>{row[3]}</small></p></div>)}</div></article><article className="card reasoning-card"><div className="reasoning-mark">✧</div><p className="eyebrow">DECISION INTELLIGENCE</p><h2>Every trade has a reason.</h2><p>Inspect why a position was proposed, why alternatives were rejected, the confidence range, risks, indicators, news and fundamentals before approving it.</p><button className="primary-button" onClick={() => setActive("AI Reasoning")}>Open AI reasoning <span>→</span></button></article></section>
      </div>
    </main>
  );
}

function Sidebar({ active, setActive }: { active: string; setActive: (page: string) => void }) {
  return <aside className="sidebar"><div className="brand"><span className="brand-mark">Q</span><span>QUANT<span>GPT</span></span></div><div className="account"><div className="avatar">SR</div><div><b>Srikanth Reddy</b><small>Research Terminal</small></div><button>⌄</button></div><nav>{navigation.map(item => <button key={item.label} onClick={() => setActive(item.label)} className={active === item.label ? "nav-active" : ""}><span className="nav-icon">{item.icon}</span>{item.label}{item.badge && <em>{item.badge}</em>}</button>)}</nav><div className="sidebar-foot"><div><i className="pulse" /><span>Systems operational</span></div><button>◐ <span>Settings</span></button></div></aside>;
}

function Topbar() {
  return <header className="topbar"><label className="search"><span>⌕</span><input aria-label="Search markets" placeholder="Search markets, signals, trades..." /><kbd>⌘ K</kbd></label><div className="top-actions"><button className="icon-button">◌<i /></button><button className="icon-button">?</button><span className="divider" /><button className="new-trade">+ New trade</button></div></header>;
}
