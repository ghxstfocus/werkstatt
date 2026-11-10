// OP-306b: Workspace-Overview-Shell; project cards consume /api/overview.
(function () {
  "use strict";
  var generation = 0;
  var SVG = "http://www.w3.org/2000/svg";

  function el(id) { return document.getElementById(id); }
  function node(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function fmt(n) { return Number(n || 0).toLocaleString("de-DE"); }
  function rel(value) {
    if (!value) return "Noch kein Run";
    var ms = Date.parse(value);
    if (!Number.isFinite(ms)) return "Zeit unbekannt";
    var sec = Math.max(0, Math.floor((Date.now() - ms) / 1000));
    if (sec < 60) return "gerade eben";
    if (sec < 3600) return Math.floor(sec / 60) + " Min. zuvor";
    if (sec < 86400) return Math.floor(sec / 3600) + " Std. zuvor";
    return Math.floor(sec / 86400) + " Tage zuvor";
  }
  function openProject(name) {
    if (window.WerkstattTabs && window.WerkstattTabs.oeffne_projekt) {
      window.WerkstattTabs.oeffne_projekt(name);
    }
  }
  function sparkline(values) {
    var svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", "0 0 120 30");
    svg.setAttribute("preserveAspectRatio", "none");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Loop-Runs pro Tag in den letzten 30 Tagen");
    svg.classList.add("overview-project-sparkline");
    var nums = Array.isArray(values) ? values.map(Number) : [];
    if (!nums.length) nums = [0, 0];
    var max = Math.max.apply(null, nums.concat([1]));
    var points = nums.map(function (v, i) {
      var x = nums.length < 2 ? 60 : i * 120 / (nums.length - 1);
      var y = 28 - Math.max(0, v) * 24 / max;
      return x.toFixed(1) + "," + y.toFixed(1);
    }).join(" ");
    var line = document.createElementNS(SVG, "polyline");
    line.setAttribute("points", points);
    svg.appendChild(line);
    return svg;
  }
  function renderDonut(data) {
    var target = el("overview-outcomes");
    if (!target) return;
    target.replaceChildren();
    var n = data && data.ergebnisse_30d || {};
    var success = Number(n.erfolg || 0);
    var failed = Number(n.fehlgeschlagen || 0);
    var aborted = Number(n.abgebrochen || 0);
    var total = Number(n.gesamt || success + failed + aborted);
    if (!total) {
      target.appendChild(node("p", "overview-no-data", "Noch keine Run-Daten in den letzten 30 Tagen."));
      return;
    }
    var svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", "0 0 100 100");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Erfolgsquote: " + Math.round(success * 100 / total) + " Prozent");
    svg.classList.add("overview-donut");
    var circumference = 2 * Math.PI * 40;
    var values = [
      {value: success, cls: "overview-donut-success"},
      {value: failed, cls: "overview-donut-failed"},
      {value: aborted, cls: "overview-donut-aborted"}
    ];
    var offset = 0;
    values.forEach(function (part) {
      if (!part.value) return;
      var circle = document.createElementNS(SVG, "circle");
      circle.setAttribute("cx", "50");
      circle.setAttribute("cy", "50");
      circle.setAttribute("r", "40");
      circle.setAttribute("fill", "none");
      circle.setAttribute("stroke-width", "11");
      circle.setAttribute("stroke-dasharray", (part.value * circumference / total) + " " + circumference);
      circle.setAttribute("stroke-dashoffset", String(-offset));
      circle.setAttribute("transform", "rotate(-90 50 50)");
      circle.classList.add(part.cls);
      svg.appendChild(circle);
      offset += part.value * circumference / total;
    });
    var value = document.createElementNS(SVG, "text");
    value.setAttribute("x", "50");
    value.setAttribute("y", "48");
    value.classList.add("overview-donut-value");
    value.textContent = Math.round(success * 100 / total) + "%";
    svg.appendChild(value);
    var caption = document.createElementNS(SVG, "text");
    caption.setAttribute("x", "50");
    caption.setAttribute("y", "59");
    caption.classList.add("overview-donut-caption");
    caption.textContent = "ERFOLG";
    svg.appendChild(caption);
    target.appendChild(svg);
    var legend = node("div", "overview-legend");
    [
      ["Erfolgreich", success, "var(--sem-ok)"],
      ["Fehlgeschlagen", failed, "var(--sem-error)"],
      ["Abgebrochen", aborted, "var(--sem-warn)"]
    ].forEach(function (entry) {
      var row = node("div", "overview-legend-row");
      var dot = node("span", "overview-legend-dot");
      dot.style.background = entry[2];
      row.appendChild(dot);
      row.appendChild(node("span", "", entry[0] + " · " + fmt(entry[1])));
      legend.appendChild(row);
    });
    target.appendChild(legend);
  }
  function renderBars(projects) {
    var root = el("overview-project-bars");
    if (!root) return;
    root.replaceChildren();
    projects.forEach(function (p) {
      var r = p.ergebnisse_30d || {};
      var success = Number(r.erfolg || 0);
      var failed = Number(r.fehlgeschlagen || 0);
      var aborted = Number(r.abgebrochen || 0);
      var total = Number(r.gesamt || success + failed + aborted);
      if (!total) return;
      var row = node("div", "overview-project-bar-row");
      row.appendChild(node("span", "overview-project-bar-name", p.name));
      var bar = node("div", "overview-project-bar");
      [["success", success], ["failed", failed], ["aborted", aborted]].forEach(function (x) {
        var segment = node("span", x[0]);
        segment.style.width = (x[1] * 100 / total) + "%";
        bar.appendChild(segment);
      });
      row.appendChild(bar);
      row.appendChild(node("span", "overview-project-bar-count", fmt(success) + "/" + fmt(total)));
      root.appendChild(row);
    });
  }
  function renderTop(projects, names) {
    var root = el("overview-top-projects");
    if (!root) return;
    root.replaceChildren();
    var ranking = (names || []).map(function (name) {
      return projects.find(function (p) { return p.name === name; });
    }).filter(Boolean).slice(0, 3);
    if (!ranking.length) {
      root.appendChild(node("p", "overview-no-data", "Diese Woche gibt es noch keine Loop-Aktivität."));
      return;
    }
    ranking.forEach(function (p, i) {
      var btn = node("button", "overview-top-project");
      btn.type = "button";
      btn.appendChild(node("span", "overview-top-rank", String(i + 1).padStart(2, "0")));
      btn.appendChild(node("span", "overview-top-name", p.name));
      btn.appendChild(node("span", "overview-top-count", fmt(p.runs_7d_total) + " Runs"));
      btn.addEventListener("click", function () { openProject(p.name); });
      root.appendChild(btn);
    });
  }
  function renderProjects(projects) {
    var root = el("overview-projects");
    if (!root) return;
    root.replaceChildren();
    if (!projects.length) {
      var empty = node("div", "overview-empty");
      empty.appendChild(node("p", "", "Noch keine Werkstatt-Projekte gefunden."));
      var create = node("button", "overview-refresh", "+ Erstes Projekt anlegen");
      create.type = "button";
      create.addEventListener("click", function () { var b = el("tab-neu"); if (b) b.click(); });
      empty.appendChild(create);
      root.appendChild(empty);
      return;
    }
    projects.forEach(function (p) {
      var card = node("button", "overview-project-card");
      card.type = "button";
      card.setAttribute("aria-label", p.name + " öffnen");
      card.addEventListener("click", function () { openProject(p.name); });
      var title = node("span", "overview-project-title");
      var dot = node("span", "overview-status-dot");
      var state = p.loop_status || "idle";
      dot.dataset.state = state;
      dot.setAttribute("aria-hidden", "true");
      title.appendChild(dot);
      title.appendChild(node("strong", "", p.name));
      title.appendChild(node("span", "overview-project-state", ({running:"Läuft",done:"Fertig",failed:"Fehler",idle:"Idle"})[state] || "Idle"));
      card.appendChild(title);
      card.appendChild(sparkline(p.runs_30d));
      var kpis = node("div", "overview-project-kpis");
      kpis.appendChild(node("span", "", fmt(p.runs_30d_total) + " Runs"));
      kpis.appendChild(node("span", "", Math.round(Number(p.erfolgsquote_30d || 0) * 100) + "% Erfolg"));
      kpis.appendChild(node("span", "", fmt(p.ops_offen) + " offene OPs"));
      card.appendChild(kpis);
      var results = p.ergebnisse_30d || {};
      var resultTotal = Number(results.gesamt || 0);
      if (resultTotal) {
        var bar = node("span", "overview-project-success");
        [["success",results.erfolg],["failed",results.fehlgeschlagen],["aborted",results.abgebrochen]].forEach(function (part) {
          var seg = node("span", part[0]);
          seg.style.width = (Number(part[1] || 0) * 100 / resultTotal) + "%";
          bar.appendChild(seg);
        });
        card.appendChild(bar);
      }
      card.appendChild(node("span", "overview-project-last", "Letzter Run · " + rel(p.letzter_run && p.letzter_run.ts)));
      root.appendChild(card);
    });
  }
  function lade() {
    var id = ++generation;
    var projects = el("overview-projects");
    if (projects && !projects.children.length) projects.appendChild(node("p","overview-no-data","Übersicht wird geladen …"));
    fetch("/api/overview", {credentials:"same-origin", cache:"no-store"})
      .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(function (data) {
        if (id !== generation) return;
        var items = Array.isArray(data.projekte) ? data.projekte : [];
        renderTop(items, data.top_3);
        renderDonut(data);
        renderBars(items);
        renderProjects(items);
        var updated = el("overview-updated");
        if (updated) updated.textContent = data.generated_at ? "Aktualisiert " + rel(data.generated_at) : "";
      })
      .catch(function () {
        if (id !== generation) return;
        var root = el("overview-projects");
        if (root) { root.replaceChildren(); root.appendChild(node("p","overview-empty","Projektübersicht konnte nicht geladen werden. Bitte erneut versuchen.")); }
      });
  }
  document.addEventListener("DOMContentLoaded", function () {
    var refresh = el("overview-refresh");
    if (refresh) refresh.addEventListener("click", lade);
    var create = el("overview-new-project");
    if (create) create.addEventListener("click", function () { var b = el("tab-neu"); if (b) b.click(); });
  });
  window.WerkstattOverview = { lade: lade };
})();
