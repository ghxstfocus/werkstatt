// Detail-Drawer (OP-298). Zeigt Plan/Evidence/Handoffs/Plan-Diff.
(function () {
  "use strict";
  var aktuellesProjekt = "werkstatt";

  function _el(id) { return document.getElementById(id); }
  function _clear(box) { if (box) box.innerHTML = ""; }

  function _api(pfad) {
    return fetch("/api/projects/" + encodeURIComponent(aktuellesProjekt) + pfad,
                 {credentials: "same-origin"})
      .then(function (r) { return r.ok ? r.json() : {}; })
      .catch(function () { return {}; });
  }

  function _setTab(name) {
    var d = _el("detail-drawer");
    if (!d) return;
    d.querySelectorAll(".dd-tab").forEach(function (b) {
      b.classList.toggle("aktiv", b.dataset.tab === name);
    });
    var body = _el("dd-body");
    if (!body) return;
    _clear(body);
    if (name === "plan") _renderPlan(body);
    else if (name === "evidence") _renderEvidence(body);
    else if (name === "handoffs") _renderHandoffs(body);
    else if (name === "diff") _renderPlanDiff(body);
  }

  function _renderPlan(body) {
    _api("/gate/context").then(function (ctx) {
      if (!ctx || !ctx.plan || !ctx.plan.text) {
        body.textContent = "(kein Plan im aktuellen Run)";
        return;
      }
      var info = document.createElement("div");
      info.style.cssText = "color:var(--text-dim);font-size:10px;margin-bottom:8px;";
      info.textContent = "Quelle: " + (ctx.plan.kind || "?") + " · " + (ctx.plan.text.length) + " Zeichen";
      body.appendChild(info);
      var pre = document.createElement("pre");
      pre.className = "dd-plan";
      pre.textContent = ctx.plan.text;
      body.appendChild(pre);
    });
  }

  function _renderEvidence(body) {
    _api("/evidence").then(function (d) {
      var links = d.links || [];
      if (links.length === 0) {
        body.textContent = "(keine Evidence-Links)";
        return;
      }
      var list = document.createElement("div");
      list.className = "dd-evidence-list";
      links.forEach(function (l) {
        var row = document.createElement("div");
        row.className = "dd-evidence" + (l.im_plan_erwaehnt ? " im-plan" : "");
        var badge = document.createElement("span");
        badge.className = "dd-evidence-badge";
        badge.textContent = l.quelle || "?";
        var txt = document.createElement("span");
        txt.textContent = l.text || "";
        row.appendChild(badge);
        row.appendChild(txt);
        list.appendChild(row);
      });
      body.appendChild(list);
    });
  }

  function _renderHandoffs(body) {
    _api("/handoffs").then(function (d) {
      var ho = d.handoffs || [];
      if (ho.length === 0) {
        body.textContent = "(keine Handoffs)";
        return;
      }
      var flow = document.createElement("div");
      flow.className = "dd-handoff-flow";
      ho.forEach(function (h, i) {
        var node = document.createElement("div");
        node.className = "dd-handoff";
        var rolle = document.createElement("div");
        rolle.className = "dd-handoff-rolle";
        rolle.textContent = h.rolle;
        node.appendChild(rolle);
        var meta = document.createElement("div");
        meta.className = "dd-handoff-meta";
        meta.textContent = h.anzahl + " Events";
        node.appendChild(meta);
        if (h.beispiele && h.beispiele.length) {
          var ul = document.createElement("ul");
          h.beispiele.forEach(function (b) {
            var li = document.createElement("li");
            li.textContent = b;
            ul.appendChild(li);
          });
          node.appendChild(ul);
        }
        flow.appendChild(node);
        if (i < ho.length - 1) {
          var pfeil = document.createElement("div");
          pfeil.className = "dd-handoff-pfeil";
          pfeil.textContent = "\u2193";
          flow.appendChild(pfeil);
        }
      });
      body.appendChild(flow);
    });
  }

  function _renderPlanDiff(body) {
    _api("/plan/versions").then(function (d) {
      var v = d.versionen || [];
      if (v.length < 2) {
        body.textContent = "(keine Plan-Aenderung — " + v.length + " Version)";
        if (v.length === 1) {
          var pre = document.createElement("pre");
          pre.className = "dd-plan";
          pre.textContent = v[0].text || "";
          body.appendChild(pre);
        }
        return;
      }
      var alt = (v[v.length - 2].text || "").split("\n");
      var neu = (v[v.length - 1].text || "").split("\n");
      var max = Math.max(alt.length, neu.length);
      var out = document.createElement("div");
      out.className = "dd-diff";
      for (var i = 0; i < max; i++) {
        var a = alt[i] || "";
        var n = neu[i] || "";
        if (a === n) {
          var row = document.createElement("div");
          row.className = "dd-diff-zeile gleich";
          row.textContent = "  " + a;
          out.appendChild(row);
        } else {
          if (a) {
            var minus = document.createElement("div");
            minus.className = "dd-diff-minus";
            minus.textContent = "- " + a;
            out.appendChild(minus);
          }
          if (n) {
            var plus = document.createElement("div");
            plus.className = "dd-diff-plus";
            plus.textContent = "+ " + n;
            out.appendChild(plus);
          }
        }
      }
      body.appendChild(out);
    });
  }

  function _machDraggable(box, handle) {
    var key = "werkstatt-detail-pos";
    try {
      var gespeichert = localStorage.getItem(key);
      if (gespeichert) {
        var pos = JSON.parse(gespeichert);
        if (pos && typeof pos.left === "number") {
          box.style.left = pos.left + "px";
          box.style.top = pos.top + "px";
          box.style.right = "auto";
        }
      }
    } catch (e) {}
    var startX = 0, startY = 0, startL = 0, startT = 0, dragging = false;
    function onStart(ev) {
      // Klicks auf Tabs/Close nicht als Drag interpretieren
      if (ev.target.closest(".dd-tab") || ev.target.closest(".dd-close")) return;
      ev.preventDefault();
      var t = ev.touches ? ev.touches[0] : ev;
      var rect = box.getBoundingClientRect();
      startX = t.clientX; startY = t.clientY;
      startL = rect.left; startT = rect.top;
      dragging = true;
      box.style.left = startL + "px";
      box.style.top = startT + "px";
      box.style.right = "auto";
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onEnd);
      document.addEventListener("touchmove", onMove);
      document.addEventListener("touchend", onEnd);
    }
    function onMove(ev) {
      if (!dragging) return;
      var t = ev.touches ? ev.touches[0] : ev;
      box.style.left = (startL + t.clientX - startX) + "px";
      box.style.top = (startT + t.clientY - startY) + "px";
    }
    function onEnd() {
      dragging = false;
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onEnd);
      document.removeEventListener("touchmove", onMove);
      document.removeEventListener("touchend", onEnd);
      try {
        var r = box.getBoundingClientRect();
        localStorage.setItem(key, JSON.stringify({left: r.left, top: r.top}));
      } catch (e) {}
    }
    handle.addEventListener("mousedown", onStart);
    handle.addEventListener("touchstart", onStart);
  }

  function oeffne(tab) {
    var d = _el("detail-drawer");
    if (!d) return;
    d.dataset.offen = "true";
    _setTab(tab || "plan");
  }

  function schliesse() {
    var d = _el("detail-drawer");
    if (d) d.dataset.offen = "false";
  }

  function setProjekt(p) {
    if (p) aktuellesProjekt = p;
  }

  window.WerkstattDetail = { oeffne: oeffne, schliesse: schliesse, setProjekt: setProjekt };

  document.addEventListener("DOMContentLoaded", function () {
    var d = _el("detail-drawer");
    if (!d) return;
    d.querySelectorAll(".dd-tab").forEach(function (b) {
      b.addEventListener("click", function () { _setTab(b.dataset.tab); });
    });
    var schliessenBtn = _el("dd-close");
    if (schliessenBtn) schliessenBtn.addEventListener("click", schliesse);
    // Drag am Tab-Header
    var tabsNav = d.querySelector(".dd-tabs");
    if (tabsNav) {
      tabsNav.style.cursor = "move";
      tabsNav.title = "Ziehen zum Verschieben";
      _machDraggable(d, tabsNav);
    }
  });
})();
