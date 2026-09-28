#!/usr/bin/env python3
"""Generated ROSMonitoring monitor: d3_native_guard.

This file is generated. Edit the YAML configuration and regenerate instead of
editing this monitor by hand.
"""

from __future__ import annotations

import argparse
try:
    import fcntl
except Exception:
    fcntl = None
import heapq
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import itertools
import json
import os
from pathlib import Path
import threading
import time
from typing import Any
from urllib.parse import urlparse

try:
    import websocket
except Exception:
    websocket = None

try:
    from std_msgs.msg import String
    from teleop_bridge_msgs.msg import ReceivedPoseStates
except Exception:
    String = object
    ReceivedPoseStates = object
try:
    from std_msgs.msg import String as ROSMonitoringVerdictString
except Exception:
    class ROSMonitoringVerdictString:
        def __init__(self):
            self.data = ""

ROS_VERSION = 'ros2'
MONITOR_ID = 'd3_native_guard'
LOG_PATH = '/results/monitor_native_events.jsonl'
STATUS_LOG_PATH = '/results/monitor_native_status.jsonl'
STATUS_ENABLED = True
SILENT = False
WARNING = 1
ORACLE = {'url': 'ws://127.0.0.1:18842', 'action': 'nothing', 'timeout': 0.05}
INTERFACES = [{'action': 'filter',
  'intercepting': True,
  'key': 'topic:/s4b/d1/native_input',
  'kind': 'topic',
  'legacy_name': '/s4b/d1/native_input',
  'max_delay_ms': 0,
  'name': '/s4b/d1/native_input',
  'ordered': False,
  'publishers': ['source'],
  'python_name': 's4b_d1_native_input',
  'remapped_name': '/s4b/d1/native_input_mon',
  'subscribers': [],
  'type': 'ReceivedPoseStates',
  'type_fqn': 'teleop_bridge_msgs.msg.ReceivedPoseStates'},
 {'action': 'filter',
  'intercepting': True,
  'key': 'topic:/s4b/d3/tick',
  'kind': 'topic',
  'legacy_name': '/s4b/d3/tick',
  'max_delay_ms': 0,
  'name': '/s4b/d3/tick',
  'ordered': False,
  'publishers': ['source'],
  'python_name': 's4b_d3_tick',
  'remapped_name': '/s4b/d3/tick_mon',
  'subscribers': [],
  'type': 'String',
  'type_fqn': 'std_msgs.msg.String'}]
DASHBOARD_HTML = '<!doctype html>\n<html lang="en">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>ROSMonitoring Dashboard</title>\n  <style>\n    :root { color-scheme: light; --bg: #f4f6f8; --panel: #fff; --ink: #16202a; --muted: #647181; --line: #d9e0e7; --accent: #0b5cad; --bad: #b4232f; --ok: #146c43; }\n    * { box-sizing: border-box; }\n    body { font-family: system-ui, sans-serif; margin: 0; background: var(--bg); color: var(--ink); }\n    header { padding: 16px 24px; background: #101820; color: white; display: flex; align-items: center; justify-content: space-between; gap: 16px; }\n    header h1 { margin: 0; font-size: 20px; }\n    header .meta { color: #cbd5df; font-size: 13px; }\n    main { padding: 18px 24px 28px; }\n    .cards { display: grid; grid-template-columns: repeat(4, minmax(150px, 1fr)); gap: 12px; margin-bottom: 14px; }\n    .card, .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; }\n    .card { padding: 14px; }\n    .card .label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }\n    .card .value { font-size: 26px; font-weight: 700; margin-top: 4px; }\n    .tabs { display: flex; gap: 8px; margin: 12px 0; flex-wrap: wrap; }\n    button, input, select { font: inherit; }\n    button { border: 1px solid var(--line); background: white; border-radius: 6px; padding: 8px 10px; cursor: pointer; }\n    button.active { background: var(--accent); color: white; border-color: var(--accent); }\n    .toolbar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; }\n    input, select { border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px; background: white; }\n    .panel { overflow: hidden; }\n    .panel h2 { margin: 0; padding: 12px 14px; font-size: 15px; border-bottom: 1px solid var(--line); background: #f9fbfc; }\n    table { width: 100%; border-collapse: collapse; background: white; }\n    th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid #d8dde3; }\n    th { background: #eef1f5; font-weight: 650; }\n    td code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }\n    pre { margin: 0; white-space: pre-wrap; word-break: break-word; max-height: 520px; overflow: auto; padding: 12px; background: #0f1720; color: #d8e4ef; }\n    .split { display: grid; grid-template-columns: repeat(2, minmax(260px, 1fr)); gap: 12px; padding: 12px; }\n    .metric-grid { display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 10px; padding: 12px; }\n    .metric { border: 1px solid var(--line); border-radius: 8px; padding: 10px; background: #fbfcfd; }\n    .metric .label { color: var(--muted); font-size: 12px; }\n    .metric .value { font-size: 22px; font-weight: 750; margin-top: 3px; }\n    .plot { border: 1px solid var(--line); border-radius: 8px; overflow: hidden; background: white; min-height: 180px; }\n    .plot h3 { margin: 0; padding: 10px 12px; border-bottom: 1px solid var(--line); font-size: 13px; background: #f9fbfc; }\n    .bars { padding: 12px; display: grid; gap: 8px; }\n    .bar-row { display: grid; grid-template-columns: minmax(96px, 170px) 1fr 42px; align-items: center; gap: 8px; font-size: 13px; }\n    .bar-track { height: 12px; border-radius: 4px; background: #e8edf2; overflow: hidden; }\n    .bar-fill { height: 100%; background: var(--accent); }\n    .bar-fill.bad-fill { background: var(--bad); }\n    .plot svg, .sequence svg { width: 100%; display: block; }\n    .sequence { padding: 12px; overflow: auto; background: white; }\n    .sequence .empty, .plot .empty { color: var(--muted); padding: 12px; }\n    .legend { display: flex; gap: 12px; flex-wrap: wrap; padding: 0 12px 12px; color: var(--muted); font-size: 12px; }\n    .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 5px; background: var(--accent); }\n    .dot.bad-dot { background: var(--bad); }\n    .dot.ok-dot { background: var(--ok); }\n    .ok { color: var(--ok); font-weight: 650; }\n    .bad { color: var(--bad); font-weight: 650; }\n    .muted { color: var(--muted); }\n    .hidden { display: none; }\n    @media (max-width: 900px) { .cards, .metric-grid, .split { grid-template-columns: repeat(2, 1fr); } }\n    @media (max-width: 560px) { .cards, .metric-grid, .split { grid-template-columns: 1fr; } header { align-items: flex-start; flex-direction: column; } }\n  </style>\n</head>\n<body>\n  <header>\n    <h1>ROSMonitoring Dashboard</h1>\n    <div class="meta"><span id="updated">not loaded</span> · <label><input id="auto" type="checkbox" checked> auto-refresh</label></div>\n  </header>\n  <main>\n    <section class="cards">\n      <div class="card"><div class="label">Monitors</div><div class="value" id="monitorCount">0</div></div>\n      <div class="card"><div class="label">Events</div><div class="value" id="eventCount">0</div></div>\n      <div class="card"><div class="label">Violations</div><div class="value bad" id="violationCount">0</div></div>\n      <div class="card"><div class="label">Observed Payloads</div><div class="value" id="payloadCount">0</div></div>\n    </section>\n    <div class="tabs">\n      <button class="active" data-tab="overview">Overview</button>\n      <button data-tab="statistics">Statistics</button>\n      <button data-tab="sequence">Sequence</button>\n      <button data-tab="interfaces">Interfaces</button>\n      <button data-tab="events">Observed Events</button>\n      <button data-tab="status">Status Timeline</button>\n      <button data-tab="raw">Raw JSON</button>\n    </div>\n    <div class="toolbar">\n      <select id="monitorSelect"><option value="all">All monitors</option></select>\n      <input id="filter" placeholder="Filter text, interface, verdict">\n      <button id="refresh">Refresh</button>\n    </div>\n    <section id="overview" class="panel tab"><h2>Monitor Overview</h2><div id="overviewBody"></div></section>\n    <section id="statistics" class="panel tab hidden"><h2>Statistics</h2><div id="statisticsBody"></div></section>\n    <section id="sequence" class="panel tab hidden"><h2>Observed Sequence</h2><div id="sequenceBody"></div></section>\n    <section id="interfaces" class="panel tab hidden"><h2>Configured Interfaces</h2><div id="interfacesBody"></div></section>\n    <section id="events" class="panel tab hidden"><h2>Recent Observed Events</h2><div id="eventsBody"></div></section>\n    <section id="status" class="panel tab hidden"><h2>Status Timeline</h2><div id="statusBody"></div></section>\n    <section id="raw" class="panel tab hidden"><h2>Raw Dashboard Payload</h2><pre id="rawBody"></pre></section>\n  </main>\n  <script>\n    let latest = null;\n    let activeTab = \'overview\';\n    let selectedMonitor = \'all\';\n    const esc = (v) => String(v ?? \'\').replace(/[&<>"\']/g, c => ({\'&\':\'&amp;\',\'<\':\'&lt;\',\'>\':\'&gt;\',\'"\':\'&quot;\',"\'":\'&#39;\'}[c]));\n    const json = (v) => esc(JSON.stringify(v, null, 2));\n    function table(headers, rows) {\n      if (!rows.length) return \'<p class="muted" style="padding:12px">No data yet.</p>\';\n      return `<table><thead><tr>${headers.map(h => `<th>${esc(h)}</th>`).join(\'\')}</tr></thead><tbody>${rows.join(\'\')}</tbody></table>`;\n    }\n    function row(cells) { return `<tr>${cells.map(c => `<td>${c}</td>`).join(\'\')}</tr>`; }\n    function matchesFilter(item) {\n      const q = document.getElementById(\'filter\').value.trim().toLowerCase();\n      return !q || JSON.stringify(item).toLowerCase().includes(q);\n    }\n    function allMonitorIds(data) {\n      return Array.from(new Set([\n        ...Object.keys(data.status.monitors || {}),\n        ...Object.keys(data.monitor_configs || {}),\n        ...(data.recent_events || []).map(item => item._monitor).filter(Boolean),\n      ])).sort();\n    }\n    function monitorMatches(item) {\n      if (selectedMonitor === \'all\') return true;\n      return item.monitor === selectedMonitor || item._monitor === selectedMonitor;\n    }\n    function renderMonitorSelect(data) {\n      const select = document.getElementById(\'monitorSelect\');\n      const ids = allMonitorIds(data);\n      if (selectedMonitor !== \'all\' && !ids.includes(selectedMonitor)) {\n        selectedMonitor = \'all\';\n      }\n      select.innerHTML = [\n        \'<option value="all">All monitors</option>\',\n        ...ids.map(id => `<option value="${esc(id)}">${esc(id)}</option>`),\n      ].join(\'\');\n      select.value = selectedMonitor;\n    }\n    function monitorConfigs(data) {\n      const configs = {...(data.monitor_configs || {})};\n      if (data.monitor_config && data.monitor_config.id && !configs[data.monitor_config.id]) {\n        configs[data.monitor_config.id] = data.monitor_config;\n      }\n      return configs;\n    }\n    function eventDirection(item) {\n      if (Object.prototype.hasOwnProperty.call(item, \'request\')) return \'request\';\n      if (Object.prototype.hasOwnProperty.call(item, \'response\')) return \'response\';\n      return item.__direction || item.direction || \'message\';\n    }\n    function eventPayload(item) {\n      if (Object.prototype.hasOwnProperty.call(item, \'payload\')) return item.payload;\n      if (Object.prototype.hasOwnProperty.call(item, \'request\')) return item.request;\n      if (Object.prototype.hasOwnProperty.call(item, \'response\')) return item.response;\n      if (Object.prototype.hasOwnProperty.call(item, \'data\')) return item.data;\n      const copy = {...item};\n      [\'time\', \'topic\', \'service\', \'_monitor\', \'monitor\', \'status\', \'interface\', \'kind\',\n       \'verdict\', \'verdict_raw\', \'terminal\', \'will_stop\', \'ordered\', \'oracle_response\',\n       \'event\', \'direction\', \'session_id\', \'ros_version\', \'action\', \'blocked\',\n       \'communication_allowed\', \'decision\'].forEach(k => delete copy[k]);\n      return copy;\n    }\n    function verdictClass(value) {\n      const text = String(value ?? \'\').toLowerCase();\n      return text.includes(\'false\') || text === \'violation\' || text === \'violated\' ? \'bad\' : \'ok\';\n    }\n    function filteredStatusEvents(data) {\n      return (data.recent_status || [])\n        .filter(item => item.status === \'event\')\n        .filter(monitorMatches)\n        .filter(matchesFilter);\n    }\n    function filteredObservedEvents(data) {\n      return (data.recent_events || [])\n        .filter(monitorMatches)\n        .filter(matchesFilter);\n    }\n    function eventKey(item) {\n      return item.interface || item.topic || item.service || \'\';\n    }\n    function verdictLabel(item) {\n      if (item.verdict_raw !== undefined && item.verdict_raw !== null) return String(item.verdict_raw);\n      if (item.verdict === true) return \'allow\';\n      if (item.verdict === false) return \'block\';\n      return \'unknown\';\n    }\n    function decisionLabel(item) {\n      if (item.decision) return String(item.decision);\n      if (item.blocked === true) return \'blocked\';\n      if (item.communication_allowed === true && item.action === \'filter\') return \'forwarded\';\n      if (item.verdict === false) return \'negative verdict\';\n      if (item.verdict === true) return \'allow\';\n      return \'\';\n    }\n    function countBy(items, keyFn) {\n      const counts = new Map();\n      items.forEach(item => {\n        const key = keyFn(item) || \'unknown\';\n        counts.set(key, (counts.get(key) || 0) + 1);\n      });\n      return Array.from(counts.entries()).sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])));\n    }\n    function barPlot(title, rows, options = {}) {\n      const max = Math.max(1, ...rows.map(([, value]) => value));\n      const body = rows.length ? rows.map(([label, value]) => {\n        const width = Math.max(3, Math.round((value / max) * 100));\n        const fill = options.bad && options.bad(label, value) ? \'bar-fill bad-fill\' : \'bar-fill\';\n        return `<div class="bar-row"><code title="${esc(label)}">${esc(label)}</code><div class="bar-track"><div class="${fill}" style="width:${width}%"></div></div><strong>${esc(value)}</strong></div>`;\n      }).join(\'\') : \'<div class="empty">No data yet.</div>\';\n      return `<div class="plot"><h3>${esc(title)}</h3><div class="bars">${body}</div></div>`;\n    }\n    function timelinePlot(events) {\n      const timed = events\n        .map(item => ({...item, _t: Number(item.time)}))\n        .filter(item => Number.isFinite(item._t))\n        .sort((a, b) => a._t - b._t);\n      if (!timed.length) {\n        return \'<div class="plot"><h3>Event Timeline</h3><div class="empty">No timed events yet.</div></div>\';\n      }\n      const min = timed[0]._t;\n      const max = timed[timed.length - 1]._t;\n      const bins = 24;\n      const counts = Array.from({length: bins}, () => ({events: 0, violations: 0}));\n      timed.forEach(item => {\n        const index = max === min ? 0 : Math.min(bins - 1, Math.floor(((item._t - min) / (max - min)) * bins));\n        counts[index].events += 1;\n        if (item.verdict === false || String(item.verdict_raw || \'\').toLowerCase().includes(\'false\')) {\n          counts[index].violations += 1;\n        }\n      });\n      const width = 760;\n      const height = 180;\n      const pad = 24;\n      const innerW = width - pad * 2;\n      const innerH = height - pad * 2;\n      const maxCount = Math.max(1, ...counts.map(item => item.events));\n      const barW = innerW / bins;\n      const bars = counts.map((item, index) => {\n        const h = (item.events / maxCount) * innerH;\n        const badH = item.events ? (item.violations / maxCount) * innerH : 0;\n        const x = pad + index * barW + 2;\n        const y = height - pad - h;\n        const badY = height - pad - badH;\n        return `<rect x="${x}" y="${y}" width="${Math.max(2, barW - 4)}" height="${h}" rx="2" fill="#0b5cad"></rect>` +\n          `<rect x="${x}" y="${badY}" width="${Math.max(2, barW - 4)}" height="${badH}" rx="2" fill="#b4232f"></rect>`;\n      }).join(\'\');\n      return `<div class="plot"><h3>Event Timeline</h3><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="event timeline"><line x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}" stroke="#9aa6b2"></line>${bars}<text x="${pad}" y="16" font-size="11" fill="#647181">${esc(min.toFixed(3))}</text><text x="${width - pad}" y="16" text-anchor="end" font-size="11" fill="#647181">${esc(max.toFixed(3))}</text></svg><div class="legend"><span><i class="dot"></i>events</span><span><i class="dot bad-dot"></i>violations</span></div></div>`;\n    }\n    function renderStatistics(data) {\n      const statusEvents = filteredStatusEvents(data);\n      const observedEvents = filteredObservedEvents(data);\n      const times = statusEvents.map(item => Number(item.time)).filter(Number.isFinite);\n      const duration = times.length > 1 ? Math.max(...times) - Math.min(...times) : 0;\n      const violations = statusEvents.filter(item => item.verdict === false || String(item.verdict_raw || \'\').toLowerCase().includes(\'false\')).length;\n      const terminal = statusEvents.filter(item => item.terminal === true).length;\n      const interfaces = new Set(statusEvents.map(eventKey).filter(Boolean)).size;\n      const rate = duration > 0 ? (statusEvents.length / duration).toFixed(2) : \'0\';\n      const metrics = [\n        [\'Selected Events\', statusEvents.length],\n        [\'Payload Rows\', observedEvents.length],\n        [\'Violations\', violations],\n        [\'Terminal Verdicts\', terminal],\n        [\'Interfaces\', interfaces],\n        [\'Events / Second\', rate],\n        [\'Time Span\', duration ? `${duration.toFixed(2)}s` : \'0s\'],\n        [\'Selected Monitor\', selectedMonitor === \'all\' ? \'All\' : selectedMonitor],\n      ].map(([label, value]) => `<div class="metric"><div class="label">${esc(label)}</div><div class="value">${esc(value)}</div></div>`).join(\'\');\n      const monitorRows = countBy(statusEvents, item => item.monitor);\n      const interfaceRows = countBy(statusEvents, eventKey);\n      const verdictRows = countBy(statusEvents, verdictLabel);\n      document.getElementById(\'statisticsBody\').innerHTML =\n        `<div class="metric-grid">${metrics}</div>` +\n        `<div class="split">` +\n        barPlot(\'Events by Monitor\', monitorRows) +\n        barPlot(\'Events by Interface\', interfaceRows) +\n        barPlot(\'Verdicts\', verdictRows, {bad: label => String(label).toLowerCase().includes(\'false\') || String(label).toLowerCase() === \'block\'}) +\n        timelinePlot(statusEvents) +\n        `</div>`;\n    }\n    function interfaceConfigFor(data, item) {\n      const config = (monitorConfigs(data)[item.monitor] || {}).interfaces || [];\n      return config.find(interface => interface.name === item.interface || interface.legacy_name === item.interface) || {};\n    }\n    function observedEndpoint(data, item) {\n      const config = interfaceConfigFor(data, item);\n      const direction = item.direction || eventDirection(item);\n      if (config.kind === \'topic\' && config.intercepting) return config.remapped_name || item.interface || eventKey(item);\n      if (config.kind === \'service\' && direction === \'request\') return config.remapped_name || item.interface || eventKey(item);\n      if (config.kind === \'service\' && direction === \'response\') return config.name || item.interface || eventKey(item);\n      return item.interface || eventKey(item);\n    }\n    function forwardedEndpoint(data, item) {\n      const config = interfaceConfigFor(data, item);\n      const direction = item.direction || eventDirection(item);\n      const allowed = item.blocked === true ? false : item.verdict !== false;\n      if (config.kind === \'topic\' && config.intercepting && config.action === \'filter\' && allowed) {\n        return config.name || item.interface || eventKey(item);\n      }\n      if (config.kind === \'service\' && direction === \'request\' && allowed) {\n        return config.name || item.interface || eventKey(item);\n      }\n      if (config.kind === \'service\' && direction === \'response\') {\n        return config.remapped_name || item.interface || eventKey(item);\n      }\n      return \'\';\n    }\n    function sequenceParticipants(events, data) {\n      const lanes = [];\n      const add = value => {\n        const label = String(value || \'\').trim();\n        if (label && !lanes.includes(label)) lanes.push(label);\n      };\n      events.forEach(item => {\n        add(observedEndpoint(data, item));\n        add(item.monitor);\n        if (item.oracle_response !== null && item.oracle_response !== undefined) add(\'oracle\');\n        add(forwardedEndpoint(data, item));\n      });\n      return lanes;\n    }\n    function shortLabel(value, max = 52) {\n      const text = String(value ?? \'\');\n      return text.length > max ? text.slice(0, max - 3) + \'...\' : text;\n    }\n    function renderSequence(data) {\n      const events = filteredStatusEvents(data).slice(-80);\n      if (!events.length) {\n        document.getElementById(\'sequenceBody\').innerHTML = \'<div class="sequence"><div class="empty">No observed events yet.</div></div>\';\n        return;\n      }\n      const lanes = sequenceParticipants(events, data);\n      const laneGap = 190;\n      const left = 70;\n      const top = 54;\n      const rowGap = 70;\n      const width = Math.max(780, left * 2 + Math.max(1, lanes.length - 1) * laneGap);\n      const height = top + events.length * rowGap + 70;\n      const xFor = label => left + lanes.indexOf(label) * laneGap;\n      const laneLines = lanes.map(label => {\n        const x = xFor(label);\n        return `<line x1="${x}" y1="${top - 24}" x2="${x}" y2="${height - 24}" stroke="#d9e0e7" stroke-dasharray="4 5"></line><rect x="${x - 68}" y="10" width="136" height="28" rx="6" fill="#f9fbfc" stroke="#d9e0e7"></rect><text x="${x}" y="29" text-anchor="middle" font-size="12" fill="#16202a">${esc(shortLabel(label, 18))}</text>`;\n      }).join(\'\');\n      const arrows = events.map((item, index) => {\n        const y = top + index * rowGap;\n        const source = observedEndpoint(data, item);\n        const target = forwardedEndpoint(data, item);\n        const monitor = item.monitor;\n        const sourceX = xFor(source);\n        const monitorX = xFor(monitor);\n        const verdict = verdictLabel(item);\n        const bad = verdictClass(verdict) === \'bad\';\n        const payload = eventPayload(item);\n        const direction = item.direction || eventDirection(item);\n        const label = `observe ${direction} ${verdict}`;\n        let eventArrow = `<line x1="${sourceX}" y1="${y}" x2="${monitorX}" y2="${y}" stroke="${bad ? \'#b4232f\' : \'#0b5cad\'}" stroke-width="2" marker-end="url(#arrow)"></line><circle cx="${monitorX}" cy="${y}" r="4" fill="${bad ? \'#b4232f\' : \'#146c43\'}"></circle><text x="${(sourceX + monitorX) / 2}" y="${y - 8}" text-anchor="middle" font-size="11" fill="#16202a">${esc(shortLabel(label, 42))}</text><text x="${(sourceX + monitorX) / 2}" y="${y + 17}" text-anchor="middle" font-size="10" fill="#647181">${esc(shortLabel(JSON.stringify(payload), 58))}</text>`;\n        if (target) {\n          const targetX = xFor(target);\n          const fy = y + 44;\n          eventArrow += `<line x1="${monitorX}" y1="${fy}" x2="${targetX}" y2="${fy}" stroke="#146c43" stroke-width="2" marker-end="url(#arrowOk)"></line><text x="${(monitorX + targetX) / 2}" y="${fy - 7}" text-anchor="middle" font-size="10" fill="#146c43">forward ${esc(direction)}</text>`;\n        } else if (item.blocked === true) {\n          eventArrow += `<text x="${monitorX + 12}" y="${y + 5}" font-size="12" fill="#b4232f">blocked</text>`;\n        } else if (bad) {\n          eventArrow += `<text x="${monitorX + 12}" y="${y + 5}" font-size="12" fill="#b4232f">logged violation</text>`;\n        }\n        if (item.oracle_response === null || item.oracle_response === undefined || !lanes.includes(\'oracle\')) {\n          return eventArrow;\n        }\n        const oracleX = xFor(\'oracle\');\n        const oy = y + 26;\n        return eventArrow + `<line x1="${oracleX}" y1="${oy}" x2="${monitorX}" y2="${oy}" stroke="#647181" stroke-dasharray="4 4" marker-end="url(#arrowMuted)"></line><text x="${(monitorX + oracleX) / 2}" y="${oy - 7}" text-anchor="middle" font-size="10" fill="#647181">verdict ${esc(shortLabel(JSON.stringify(item.oracle_response), 36))}</text>`;\n      }).join(\'\');\n      document.getElementById(\'sequenceBody\').innerHTML =\n        `<div class="sequence"><svg viewBox="0 0 ${width} ${height}" style="min-width:${width}px" role="img" aria-label="observed monitor sequence"><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#0b5cad"></path></marker><marker id="arrowOk" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#146c43"></path></marker><marker id="arrowMuted" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#647181"></path></marker></defs>${laneLines}${arrows}</svg><div class="legend"><span><i class="dot"></i>observed by monitor</span><span><i class="dot ok-dot"></i>forwarded by filter/proxy</span><span><i class="dot bad-dot"></i>negative verdict or blocked event</span></div></div>`;\n    }\n    function renderOverview(data) {\n      const rows = Object.entries(data.status.monitors || {})\n      .filter(([id]) => selectedMonitor === \'all\' || id === selectedMonitor)\n      .map(([id, monitor]) => row([\n        `<code>${esc(id)}</code>`,\n        esc(monitor.status),\n        esc(monitor.events),\n        `<span class="${monitor.violations > 0 ? \'bad\' : \'ok\'}">${esc(monitor.violations)}</span>`,\n        esc(Object.keys(monitor.interfaces || {}).join(\', \')),\n        esc(monitor.last_seen || \'\')\n      ]));\n      document.getElementById(\'overviewBody\').innerHTML = table([\'Monitor\', \'Status\', \'Events\', \'Violations\', \'Interfaces\', \'Last Seen\'], rows);\n    }\n    function renderInterfaces(data) {\n      const rows = Object.entries(monitorConfigs(data))\n      .filter(([id]) => selectedMonitor === \'all\' || id === selectedMonitor)\n      .flatMap(([id, config]) => (config.interfaces || []).map(item => ({...item, _monitor: id})))\n      .filter(matchesFilter).map(item => row([\n        `<code>${esc(item._monitor)}</code>`,\n        `<code>${esc(item.name)}</code>`,\n        esc(item.kind),\n        esc(item.type_fqn || item.type),\n        esc(item.action),\n        esc(item.ordered),\n        `<code>${esc(item.remapped_name)}</code>`,\n        esc(item.intercepting)\n      ]));\n      document.getElementById(\'interfacesBody\').innerHTML = table([\'Monitor\', \'Name\', \'Kind\', \'Type\', \'Action\', \'Ordered\', \'Remapped\', \'Intercepting\'], rows);\n    }\n    function renderEvents(data) {\n      const rows = (data.recent_events || []).filter(monitorMatches).filter(matchesFilter).slice().reverse().map(item => row([\n        esc(item.time || \'\'),\n        `<code>${esc(item._monitor || \'\')}</code>`,\n        esc(item.topic || item.service || \'\'),\n        esc(eventDirection(item)),\n        `<pre>${json(eventPayload(item))}</pre>`,\n        `<pre>${json(item)}</pre>`\n      ]));\n      document.getElementById(\'eventsBody\').innerHTML = table([\'Time\', \'Monitor\', \'Topic/Service\', \'Direction\', \'Payload\', \'Raw Event\'], rows);\n    }\n    function renderStatus(data) {\n      const rows = (data.recent_status || []).filter(monitorMatches).filter(matchesFilter).slice().reverse().map(item => row([\n        esc(item.time || \'\'),\n        `<code>${esc(item.monitor || \'\')}</code>`,\n        esc(item.status || \'\'),\n        esc(item.interface || \'\'),\n        `<span class="${item.blocked === true ? \'bad\' : \'\'}">${esc(decisionLabel(item))}</span>`,\n        item.verdict_raw ? `<span class="${verdictClass(item.verdict_raw)}">${esc(item.verdict_raw)}</span>` : \'\',\n        esc(item.terminal ?? \'\'),\n        esc(item.will_stop ?? \'\'),\n        `<pre>${json(eventPayload(item))}</pre>`,\n        `<pre>${json(item)}</pre>`\n      ]));\n      document.getElementById(\'statusBody\').innerHTML = table([\'Time\', \'Monitor\', \'Status\', \'Interface\', \'Decision\', \'Oracle Verdict\', \'Terminal\', \'Will Stop\', \'Payload\', \'Raw\'], rows);\n    }\n    function render(data) {\n      latest = data;\n      renderMonitorSelect(data);\n      document.getElementById(\'monitorCount\').textContent = Object.keys(data.status.monitors || {}).length;\n      document.getElementById(\'eventCount\').textContent = data.status.events || 0;\n      document.getElementById(\'violationCount\').textContent = data.status.violations || 0;\n      document.getElementById(\'payloadCount\').textContent = (data.recent_events || []).length;\n      document.getElementById(\'updated\').textContent = new Date().toLocaleTimeString();\n      renderOverview(data);\n      renderStatistics(data);\n      renderSequence(data);\n      renderInterfaces(data);\n      renderEvents(data);\n      renderStatus(data);\n      document.getElementById(\'rawBody\').textContent = JSON.stringify(data, null, 2);\n    }\n    async function refresh() {\n      const response = await fetch(\'/api/dashboard\');\n      const data = await response.json();\n      render(data);\n    }\n    document.querySelectorAll(\'.tabs button\').forEach(btn => btn.addEventListener(\'click\', () => {\n      activeTab = btn.dataset.tab;\n      document.querySelectorAll(\'.tabs button\').forEach(b => b.classList.toggle(\'active\', b === btn));\n      document.querySelectorAll(\'.tab\').forEach(tab => tab.classList.toggle(\'hidden\', tab.id !== activeTab));\n    }));\n    document.getElementById(\'refresh\').addEventListener(\'click\', refresh);\n    document.getElementById(\'filter\').addEventListener(\'input\', () => latest && render(latest));\n    document.getElementById(\'monitorSelect\').addEventListener(\'change\', event => {\n      selectedMonitor = event.target.value;\n      if (latest) render(latest);\n    });\n    refresh();\n    setInterval(() => { if (document.getElementById(\'auto\').checked) refresh(); }, 1000);\n  </script>\n</body>\n</html>\n'


def message_to_dict(message: Any) -> Any:
    if message is None or isinstance(message, (str, int, float, bool)):
        return message
    if isinstance(message, bytes):
        return message.decode("utf-8", errors="replace")
    if isinstance(message, (list, tuple)):
        return [message_to_dict(item) for item in message]
    if isinstance(message, dict):
        return {str(key): message_to_dict(value) for key, value in message.items()}
    slots = getattr(message, "__slots__", None)
    if slots:
        return {slot.lstrip("_"): message_to_dict(getattr(message, slot)) for slot in slots if hasattr(message, slot)}
    if hasattr(message, "__dict__"):
        return {str(key): message_to_dict(value) for key, value in vars(message).items() if not key.startswith("_")}
    return str(message)


def stamp_to_float(stamp: Any) -> float | None:
    if stamp is None:
        return None
    if isinstance(stamp, (int, float)):
        return float(stamp)
    sec = getattr(stamp, "sec", getattr(stamp, "secs", None))
    nanosec = getattr(stamp, "nanosec", getattr(stamp, "nsecs", None))
    if sec is not None:
        return float(sec) + (float(nanosec or 0) / 1000000000.0)
    if isinstance(stamp, dict):
        sec = stamp.get("sec", stamp.get("secs"))
        nanosec = stamp.get("nanosec", stamp.get("nsecs", 0))
        if sec is not None:
            return float(sec) + (float(nanosec or 0) / 1000000000.0)
    return None


def source_time(payload: Any, fallback: float | None = None) -> float:
    fallback = time.time() if fallback is None else fallback
    header = getattr(payload, "header", None)
    if header is not None:
        value = stamp_to_float(getattr(header, "stamp", None))
        if value is not None:
            return value
    direct = stamp_to_float(getattr(payload, "stamp", None))
    if direct is not None:
        return direct
    if isinstance(payload, dict):
        header = payload.get("header")
        if isinstance(header, dict):
            value = stamp_to_float(header.get("stamp"))
            if value is not None:
                return value
        value = stamp_to_float(payload.get("stamp"))
        if value is not None:
            return value
    return fallback


class OrderedDecision:
    def __init__(self, requires_decision: bool):
        self.requires_decision = requires_decision
        self.condition = threading.Condition()
        self.done = False
        self.allowed = True

    def set_result(self, allowed: bool):
        with self.condition:
            self.allowed = allowed
            self.done = True
            self.condition.notify_all()

    def wait(self, timeout: float | None = None) -> bool:
        with self.condition:
            if not self.done:
                self.condition.wait(timeout=timeout)
            return self.done


class OrderedEventBuffer:
    def __init__(self, max_delay_ms: int = 0):
        self.max_delay = max(0, max_delay_ms) / 1000.0
        self.sequence = itertools.count()
        self.heap = []
        self.watermark = None

    def push(self, event: dict[str, Any], payload: Any, decision: OrderedDecision) -> OrderedDecision:
        event_time = float(event["__source_time"])
        if self.watermark is None or event_time > self.watermark:
            self.watermark = event_time
        heapq.heappush(self.heap, (event_time, next(self.sequence), event, payload, decision))
        return decision

    def flush_ready(self) -> list[tuple[dict[str, Any], Any, OrderedDecision]]:
        if self.max_delay == 0:
            return self.flush_all()
        if self.watermark is None:
            return []
        threshold = self.watermark - self.max_delay
        return self._pop_while(lambda event_time, event, decision: event_time <= threshold)

    def flush_expired(self) -> list[tuple[dict[str, Any], Any, OrderedDecision]]:
        if self.max_delay == 0:
            return self.flush_all()
        now = time.monotonic()
        return self._pop_while(
            lambda event_time, event, decision: now - float(event.get("__buffered_at", now)) >= self.max_delay
        )

    def flush_through(self, decision: OrderedDecision) -> list[tuple[dict[str, Any], Any, OrderedDecision]]:
        target_time = None
        for event_time, _, _, _, item_decision in self.heap:
            if item_decision is decision:
                target_time = event_time
                break
        if target_time is None:
            return []
        return self._pop_while(lambda event_time, event, item_decision: event_time <= target_time)

    def flush_all(self) -> list[tuple[dict[str, Any], Any, OrderedDecision]]:
        return self._pop_while(lambda event_time, event, decision: True)

    def _pop_while(self, predicate):
        ready = []
        while self.heap and predicate(self.heap[0][0], self.heap[0][2], self.heap[0][4]):
            _, _, event, payload, decision = heapq.heappop(self.heap)
            ready.append((event, payload, decision))
        return ready


def read_status_log(log_path: str) -> dict[str, Any]:
    path = Path(log_path)
    monitors: dict[str, dict[str, Any]] = {}
    events = 0
    violations = 0
    if not path.exists():
        return {"monitors": monitors, "events": events, "violations": violations}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            monitor_id = item.get("monitor", "unknown")
            monitor = monitors.setdefault(
                monitor_id,
                {"status": "unknown", "last_seen": None, "events": 0, "violations": 0, "interfaces": {}},
            )
            monitor["status"] = item.get("status", monitor["status"])
            monitor["last_seen"] = item.get("time", monitor["last_seen"])
            if item.get("status") == "event":
                events += 1
                monitor["events"] += 1
                interface = item.get("interface", "unknown")
                monitor["interfaces"][interface] = monitor["interfaces"].get(interface, 0) + 1
                if item.get("verdict") is False:
                    violations += 1
                    monitor["violations"] += 1
    return {"monitors": monitors, "events": events, "violations": violations}


def read_jsonl_tail(log_path: str, limit: int = 200) -> list[dict[str, Any]]:
    path = Path(log_path)
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-limit:]


def monitor_event_log_paths(status_rows: list[dict[str, Any]]) -> dict[str, str]:
    paths = {}
    for item in status_rows:
        monitor = item.get("monitor")
        log_path = item.get("log_path")
        if monitor and log_path:
            paths[str(monitor)] = str(log_path)
    return paths


def read_monitor_events(status_rows: list[dict[str, Any]], default_monitor: str, default_log_path: str) -> dict[str, list[dict[str, Any]]]:
    paths = monitor_event_log_paths(status_rows)
    paths.setdefault(default_monitor, default_log_path)
    events = {}
    for monitor, path in sorted(paths.items()):
        rows = []
        for event in read_jsonl_tail(path):
            annotated = dict(event)
            annotated["_monitor"] = monitor
            rows.append(annotated)
        events[monitor] = rows
    return events


def monitor_configs_from_status_rows(status_rows: list[dict[str, Any]], current_config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    configs = {str(current_config["id"]): dict(current_config)}
    for item in status_rows:
        monitor = item.get("monitor")
        if not monitor:
            continue
        config = configs.setdefault(str(monitor), {"id": str(monitor)})
        if item.get("ros_version"):
            config["ros_version"] = item["ros_version"]
        if item.get("log_path"):
            config["log_path"] = item["log_path"]
        if item.get("interfaces"):
            config["interfaces"] = item["interfaces"]
    return configs


def dashboard_payload() -> dict[str, Any]:
    recent_status = read_jsonl_tail(STATUS_LOG_PATH)
    events_by_monitor = read_monitor_events(recent_status, MONITOR_ID, LOG_PATH)
    recent_events = []
    for rows in events_by_monitor.values():
        recent_events.extend(rows)
    recent_events.sort(key=lambda item: item.get("time", 0))
    current_config = {
        "id": MONITOR_ID,
        "ros_version": ROS_VERSION,
        "status_enabled": STATUS_ENABLED,
        "oracle": ORACLE,
        "interfaces": INTERFACES,
        "log_path": LOG_PATH,
        "status_log_path": STATUS_LOG_PATH,
    }
    return {
        "status": read_status_log(STATUS_LOG_PATH),
        "status_log": STATUS_LOG_PATH,
        "event_log": LOG_PATH,
        "event_logs": monitor_event_log_paths(recent_status),
        "recent_status": recent_status,
        "recent_events": recent_events[-200:],
        "recent_events_by_monitor": events_by_monitor,
        "monitor_config": current_config,
        "monitor_configs": monitor_configs_from_status_rows(recent_status, current_config),
    }


def parse_monitor_args(args=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--dashboard",
        action="store_true",
        default=os.environ.get("ROSMONITORING_DASHBOARD", "").lower() in {"1", "true", "yes", "on"},
    )
    parser.add_argument("--dashboard-host", default=os.environ.get("ROSMONITORING_DASHBOARD_HOST", "127.0.0.1"))
    parser.add_argument(
        "--dashboard-port",
        type=int,
        default=int(os.environ.get("ROSMONITORING_DASHBOARD_PORT", "8765")),
    )
    parser.add_argument(
        "--fresh-session",
        action="store_true",
        default=os.environ.get("ROSMONITORING_FRESH_SESSION", "").lower() in {"1", "true", "yes", "on"},
    )
    parser.add_argument("--session-id", default=os.environ.get("ROSMONITORING_SESSION_ID", str(os.getppid())))
    return parser.parse_known_args(args)


try:
    import rclpy
    from rclpy.node import Node
    from rclpy.callback_groups import ReentrantCallbackGroup
    from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
    from rclpy.qos import DurabilityPolicy, QoSProfile
except Exception:
    rclpy = None
    Node = object
    ReentrantCallbackGroup = None
    ExternalShutdownException = KeyboardInterrupt
    MultiThreadedExecutor = None
    DurabilityPolicy = None
    QoSProfile = None


class ROSMonitor_d3_native_guard(Node):
    def __init__(
        self,
        dashboard: bool = False,
        dashboard_host: str = "127.0.0.1",
        dashboard_port: int = 8765,
        fresh_session: bool = False,
        session_id: str = "",
    ):
        super().__init__(MONITOR_ID)
        self.lock = threading.RLock()
        self.order_lock = threading.RLock()
        self.oracle = self._connect_oracle()
        ordered_delays = [item["max_delay_ms"] for item in INTERFACES if item["ordered"]]
        self.ordered_buffer = OrderedEventBuffer(max(ordered_delays) if ordered_delays else 0)
        self.interfaces_by_key = {item["key"]: item for item in INTERFACES}
        self.publishers_by_interface = {}
        self.service_clients_by_interface = {}
        self._stop_requested = False
        self.session_id = str(session_id or os.getppid())
        self._open_files(fresh_session)
        self._create_ros_interfaces()
        self._publish_status("started", {"interfaces": INTERFACES, "log_path": LOG_PATH})
        if dashboard:
            self._start_dashboard(dashboard_host, dashboard_port)

    def _clear_shared_log_once(self, log_path: str, session_id: str):
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        marker = Path(str(path) + ".session")
        lock = Path(str(path) + ".lock")
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("a", encoding="utf-8") as handle:
            if fcntl is not None:
                fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                previous = marker.read_text(encoding="utf-8") if marker.exists() else None
                if previous != session_id:
                    path.write_text("", encoding="utf-8")
                    marker.write_text(session_id, encoding="utf-8")
            finally:
                if fcntl is not None:
                    fcntl.flock(handle, fcntl.LOCK_UN)

    def _open_files(self, fresh_session: bool = False):
        Path(LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(STATUS_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
        if fresh_session:
            Path(LOG_PATH).write_text("", encoding="utf-8")
            if STATUS_ENABLED:
                self._clear_shared_log_once(STATUS_LOG_PATH, self.session_id)
        self.log_file = open(LOG_PATH, "a", encoding="utf-8")
        self.status_file = open(STATUS_LOG_PATH, "a", encoding="utf-8") if STATUS_ENABLED else None

    def _log_info(self, message: str):
        if not SILENT:
            self.get_logger().info(message)

    def _log_warning(self, message: str):
        if WARNING:
            self.get_logger().warning(message)

    def _shutdown_runtime(self):
        if rclpy is not None and rclpy.ok():
            rclpy.shutdown()

    def _connect_oracle(self):
        if ORACLE is None:
            return None
        if websocket is None:
            self._log_warning("websocket-client is not installed; monitor will run in log-only mode")
            return None
        try:
            return websocket.create_connection(ORACLE["url"], timeout=ORACLE["timeout"])
        except Exception as exc:
            self._log_warning("could not connect to oracle: " + str(exc))
            return None

    def _event(self, interface: dict[str, Any], payload: Any, direction: str = "message") -> dict[str, Any]:
        observed = time.time()
        payload_dict = message_to_dict(payload)
        event_time = source_time(payload, observed)
        event = {
            "__monitor": MONITOR_ID,
            "__kind": interface["kind"],
            "__interface": interface["name"],
            "__interface_key": interface["key"],
            "__direction": direction,
            "__action": interface["action"],
            "__ordered": interface["ordered"],
            "__observed_time": observed,
            "__source_time": event_time,
        }
        if interface["kind"] == "topic":
            if isinstance(payload_dict, dict):
                event.update(payload_dict)
            else:
                event["data"] = payload_dict
            event["topic"] = interface["legacy_name"]
            event["time"] = event_time
            return event

        event["service"] = interface["legacy_name"]
        event["time"] = event_time
        event[direction] = payload_dict
        if isinstance(payload_dict, dict) and "stamp" in payload_dict:
            event["stamp"] = payload_dict["stamp"]
        return event

    def _wire_event(self, event: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in event.items() if not key.startswith("__")}

    def _event_payload_for_status(self, wire_event: dict[str, Any]) -> Any:
        if "request" in wire_event:
            return wire_event["request"]
        if "response" in wire_event:
            return wire_event["response"]
        if "data" in wire_event:
            return wire_event["data"]
        return {
            key: value
            for key, value in wire_event.items()
            if key not in {"time", "topic", "service"}
        }

    def _write_jsonl(self, file_handle, event: dict[str, Any]):
        file_handle.write(json.dumps(event, sort_keys=True) + "\n")
        file_handle.flush()

    def _publish_status(self, status: str, extra: dict[str, Any] | None = None):
        if not self.status_file:
            return
        event = {
            "monitor": MONITOR_ID,
            "status": status,
            "time": time.time(),
            "ros_version": ROS_VERSION,
            "session_id": getattr(self, "session_id", str(os.getppid())),
        }
        if extra:
            event.update(extra)
        self._write_jsonl(self.status_file, event)

    def _start_dashboard(self, host: str, port: int):
        if not STATUS_ENABLED:
            self._log_warning("status dashboard requested, but status logging is disabled")
            return

        class Handler(BaseHTTPRequestHandler):
            def do_GET(handler_self):
                path = urlparse(handler_self.path).path
                if path == "/api/status":
                    body = json.dumps(read_status_log(STATUS_LOG_PATH)).encode("utf-8")
                    handler_self.send_response(200)
                    handler_self.send_header("Content-Type", "application/json")
                    handler_self.send_header("Content-Length", str(len(body)))
                    handler_self.end_headers()
                    handler_self.wfile.write(body)
                    return
                if path == "/api/dashboard":
                    body = json.dumps(dashboard_payload()).encode("utf-8")
                    handler_self.send_response(200)
                    handler_self.send_header("Content-Type", "application/json")
                    handler_self.send_header("Content-Length", str(len(body)))
                    handler_self.end_headers()
                    handler_self.wfile.write(body)
                    return
                body = DASHBOARD_HTML.encode("utf-8")
                handler_self.send_response(200)
                handler_self.send_header("Content-Type", "text/html; charset=utf-8")
                handler_self.send_header("Content-Length", str(len(body)))
                handler_self.end_headers()
                handler_self.wfile.write(body)

            def log_message(handler_self, format, *args):
                return

        try:
            server = ThreadingHTTPServer((host, port), Handler)
        except OSError as exc:
            self._log_warning("could not start status dashboard: " + str(exc))
            self._publish_status("dashboard_error", {"error": str(exc), "host": host, "port": port})
            return
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self._dashboard_server = server
        self._publish_status("dashboard_started", {"host": host, "port": port})
        self._log_info("ROSMonitoring status dashboard: http://" + host + ":" + str(port))

    def _normalize_verdict(self, verdict: Any) -> str:
        if isinstance(verdict, bool):
            return "true" if verdict else "false"
        return str(verdict).lower()

    def _publish_verdict(self, verdict: Any):
        publisher = getattr(self, "verdict_publisher", None)
        if publisher is None:
            return
        message = ROSMonitoringVerdictString()
        message.data = self._normalize_verdict(verdict)
        publisher.publish(message)

    def _is_negative_verdict(self, verdict: Any) -> bool:
        return self._normalize_verdict(verdict) in {"false", "currently_false", "violation", "violated"}

    def _is_terminal_verdict(self, verdict: Any) -> bool:
        return self._normalize_verdict(verdict) in {"true", "false"}

    def _can_stop_after_terminal_verdict(self) -> bool:
        return not any(interface["intercepting"] for interface in INTERFACES)

    def _should_report_violation(self, verdict: Any) -> bool:
        if WARNING <= 0:
            return False
        normalized = self._normalize_verdict(verdict)
        if normalized in {"false", "violation", "violated"}:
            return True
        return normalized == "currently_false" and WARNING == 1

    def _request_stop_after_terminal_verdict(self, verdict: Any):
        if not self._is_terminal_verdict(verdict) or getattr(self, "_stop_requested", False):
            return
        if not self._can_stop_after_terminal_verdict():
            return
        self._stop_requested = True
        self._log_info("terminal oracle verdict " + self._normalize_verdict(verdict) + "; stopping passive monitor")
        self._shutdown_runtime()

    def _oracle_verdict(self, event: dict[str, Any]) -> tuple[bool, Any, Any]:
        if self.oracle is None:
            return True, "unknown", None
        try:
            self.oracle.send(json.dumps(self._wire_event(event)))
            response = self.oracle.recv()
        except Exception as exc:
            self._publish_status("oracle_error", {"error": str(exc)})
            return True, "unknown", None
        try:
            decoded = json.loads(response)
        except Exception:
            decoded = response
        if isinstance(decoded, dict):
            verdict = decoded.get("verdict", decoded.get("ok", True))
            return not self._is_negative_verdict(verdict), verdict, decoded
        return not self._is_negative_verdict(decoded), decoded, decoded

    def _handle_event(self, interface: dict[str, Any], event: dict[str, Any], payload: Any) -> bool:
        with self.lock:
            wire_event = self._wire_event(event)
            self._write_jsonl(self.log_file, wire_event)
            verdict, oracle_verdict, oracle_response = self._oracle_verdict(event)
            direction = event.get("__direction", "message")
            blocked = (
                interface["action"] == "filter"
                and not verdict
                and (interface["kind"] == "topic" or direction == "request")
            )
            communication_allowed = not blocked
            if blocked:
                decision = "blocked"
            elif interface["action"] == "filter" and (interface["kind"] == "topic" or direction == "request"):
                decision = "forwarded"
            elif interface["kind"] == "service" and direction == "response":
                decision = "response_logged"
            else:
                decision = "logged"
            self._publish_status(
                "event",
                {
                    "interface": interface["name"],
                    "kind": interface["kind"],
                    "action": interface["action"],
                    "direction": direction,
                    "event": wire_event,
                    "payload": self._event_payload_for_status(wire_event),
                    "verdict": verdict,
                    "verdict_raw": oracle_verdict,
                    "blocked": blocked,
                    "communication_allowed": communication_allowed,
                    "decision": decision,
                    "terminal": self._is_terminal_verdict(oracle_verdict),
                    "will_stop": self._is_terminal_verdict(oracle_verdict) and self._can_stop_after_terminal_verdict(),
                    "ordered": interface["ordered"],
                    "oracle_response": oracle_response,
                },
            )
            self._publish_verdict(oracle_verdict)
            if self._should_report_violation(oracle_verdict):
                self._log_warning("property violation on " + interface["name"])
            self._request_stop_after_terminal_verdict(oracle_verdict)
            return communication_allowed

    def _requires_inline_decision(self, interface: dict[str, Any], direction: str) -> bool:
        return interface["action"] == "filter" and (
            interface["kind"] == "topic" or direction == "request"
        )

    def _process_ordered_ready(self, ready: list[tuple[dict[str, Any], Any, OrderedDecision]]):
        for ready_event, ready_payload, decision in ready:
            interface = self.interfaces_by_key[ready_event["__interface_key"]]
            allowed = self._handle_event(interface, ready_event, ready_payload)
            decision.set_result(allowed)

    def _drain_ordered_ready(self):
        with self.order_lock:
            ready = self.ordered_buffer.flush_ready()
        self._process_ordered_ready(ready)

    def _drain_ordered_expired(self):
        with self.order_lock:
            ready = self.ordered_buffer.flush_expired()
        self._process_ordered_ready(ready)

    def _flush_ordered_through(self, decision: OrderedDecision):
        with self.order_lock:
            ready = self.ordered_buffer.flush_through(decision)
        self._process_ordered_ready(ready)

    def _wait_for_ordered_decision(self, decision: OrderedDecision) -> bool:
        deadline = time.monotonic() + self.ordered_buffer.max_delay
        while not decision.done:
            self._drain_ordered_ready()
            if decision.done:
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._drain_ordered_expired()
                if not decision.done:
                    self._flush_ordered_through(decision)
                break
            decision.wait(min(remaining, 0.05))
        return decision.allowed

    def _handle_or_buffer(self, interface: dict[str, Any], payload: Any, direction: str = "message") -> bool:
        event = self._event(interface, payload, direction)
        if not interface["ordered"]:
            return self._handle_event(interface, event, payload)
        event["__buffered_at"] = time.monotonic()
        decision = OrderedDecision(self._requires_inline_decision(interface, direction))
        with self.order_lock:
            self.ordered_buffer.push(event, payload, decision)
            ready = self.ordered_buffer.flush_ready()
        self._process_ordered_ready(ready)
        if decision.requires_decision:
            return self._wait_for_ordered_decision(decision)
        return True

    def close(self):
        with self.order_lock:
            ready = self.ordered_buffer.flush_all()
        self._process_ordered_ready(ready)
        self._publish_status("stopped")
        dashboard_server = getattr(self, "_dashboard_server", None)
        if dashboard_server is not None:
            dashboard_server.shutdown()
            dashboard_server.server_close()
        self.log_file.close()
        if self.status_file:
            self.status_file.close()


    def _create_ros_interfaces(self):
        self.callback_group = ReentrantCallbackGroup()
        verdict_qos = QoSProfile(depth=1000, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.verdict_publisher = self.create_publisher(
            ROSMonitoringVerdictString,
            MONITOR_ID + "/monitor_verdict",
            verdict_qos,
            callback_group=self.callback_group,
        )
        for interface in INTERFACES:
            msg_type = globals()[interface["type"]]
            if interface["kind"] == "topic":
                subscribe_name = interface["remapped_name"] if interface["intercepting"] else interface["name"]
                self.create_subscription(
                    msg_type,
                    subscribe_name,
                    self._topic_callback(interface),
                    1000,
                    callback_group=self.callback_group,
                )
                if interface["intercepting"]:
                    publish_name = interface["name"] if interface["publishers"] else interface["remapped_name"]
                    self.publishers_by_interface[interface["name"]] = self.create_publisher(msg_type, publish_name, 1000)
            else:
                self.create_service(
                    msg_type,
                    interface["remapped_name"],
                    self._service_callback(interface),
                    callback_group=self.callback_group,
                )
                self.service_clients_by_interface[interface["name"]] = self.create_client(
                    msg_type,
                    interface["name"],
                    callback_group=self.callback_group,
                )

    def _topic_callback(self, interface):
        def callback(message):
            allowed = self._handle_or_buffer(interface, message)
            publisher = self.publishers_by_interface.get(interface["name"])
            if allowed and publisher is not None:
                publisher.publish(message)
        return callback

    def _service_callback(self, interface):
        def callback(request, response):
            allowed = self._handle_or_buffer(interface, request, "request")
            if not allowed:
                return response
            client = self.service_clients_by_interface[interface["name"]]
            if not client.wait_for_service(timeout_sec=10.0):
                self._publish_status("service_unavailable", {"interface": interface["name"]})
                return response
            future = client.call_async(request)
            done = threading.Event()
            future.add_done_callback(lambda _: done.set())
            if not done.wait(timeout=10.0):
                self._publish_status("service_timeout", {"interface": interface["name"]})
                return response
            result = future.result()
            self._handle_or_buffer(interface, result, "response")
            return result
        return callback


def main(args=None):
    if rclpy is None:
        raise RuntimeError("ROS2 rclpy is not available")
    monitor_args, ros_args = parse_monitor_args(args)
    rclpy.init(args=ros_args)
    monitor = ROSMonitor_d3_native_guard(
        dashboard=monitor_args.dashboard,
        dashboard_host=monitor_args.dashboard_host,
        dashboard_port=monitor_args.dashboard_port,
        fresh_session=monitor_args.fresh_session,
        session_id=monitor_args.session_id,
    )
    executor = MultiThreadedExecutor()
    executor.add_node(monitor)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        executor.shutdown()
        monitor.close()
        monitor.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()


