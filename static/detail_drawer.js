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
    // Sonderfall: Rollen-Tab → in Rollen-Modus zurueck
    if (name === "__rolle__" && window.__letzteRolle) {
      oeffneRolle(window.__letzteRolle);
      return;
    }
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

  function _renderRolle(body, rolle) {
    var titel = document.createElement("div");
    titel.className = "dd-rolle-titel";
    titel.textContent = rolle.toUpperCase();
    body.appendChild(titel);

    var status = document.createElement("div");
    status.className = "dd-rolle-leer";
    status.textContent = "lade...";
    body.appendChild(status);

    fetch("/api/projects/" + encodeURIComponent(aktuellesProjekt) +
          "/role/" + encodeURIComponent(rolle),
          {credentials: "same-origin"})
      .then(function (r) { return r.ok ? r.json() : {events: []}; })
      .then(function (d) {
        body.innerHTML = "";
        body.appendChild(titel);
        var events = d.events || [];
        if (events.length === 0) {
          var leer = document.createElement("div");
          leer.className = "dd-rolle-leer";
          leer.textContent = "keine Events fuer Rolle " + rolle;
          body.appendChild(leer);
          return;
        }
        var liste = document.createElement("div");
        liste.className = "dd-rolle-liste";
        events.forEach(function (ev) {
          var karte = document.createElement("div");
          karte.className = "dd-rolle-event";
          karte.dataset.kind = ev.kind;

          var head = document.createElement("div");
          head.className = "dd-rolle-head";
          var kind = document.createElement("span");
          kind.className = "dd-rolle-kind";
          kind.textContent = ev.kind;
          var ts = document.createElement("span");
          ts.className = "dd-rolle-ts";
          var m = (ev.ts || "").match(/T(\d{2}:\d{2}:\d{2})/);
          ts.textContent = m ? m[1] : "";
          head.appendChild(kind);
          head.appendChild(ts);
          karte.appendChild(head);

          var payload = ev.payload || {};
          var skip = ["audit_id", "agent", "project", "kind",
                      "timestamp", "run_id", "ts"];
          var zeilen = Object.keys(payload).filter(function (k) {
            if (skip.indexOf(k) >= 0) return false;
            var v = payload[k];
            return v !== null && v !== undefined && v !== "";
          });

          if (zeilen.length === 0) {
            var nix = document.createElement("div");
            nix.className = "dd-rolle-empty";
            nix.textContent = "(keine Details)";
            karte.appendChild(nix);
          } else {
            zeilen.forEach(function (k) {
              var v = payload[k];
              var zeile = document.createElement("div");
              zeile.className = "dd-rolle-feld";
              var lbl = document.createElement("span");
              lbl.className = "dd-rolle-key";
              lbl.textContent = k;
              var val = document.createElement("span");
              val.className = "dd-rolle-val";
              if (typeof v === "string") {
                if (v.length > 300) {
                  var det = document.createElement("details");
                  var sum = document.createElement("summary");
                  sum.textContent = v.slice(0, 120) + " ... (" + v.length + " Z.)";
                  var pre = document.createElement("pre");
                  pre.textContent = v;
                  pre.className = "dd-rolle-pre";
                  det.appendChild(sum);
                  det.appendChild(pre);
                  val.appendChild(det);
                } else {
                  val.textContent = v;
                }
              } else if (typeof v === "number" || typeof v === "boolean") {
                val.textContent = String(v);
              } else {
                var pre2 = document.createElement("pre");
                pre2.className = "dd-rolle-pre";
                try { pre2.textContent = JSON.stringify(v, null, 2); }
                catch (e) { pre2.textContent = String(v); }
                val.appendChild(pre2);
              }
              zeile.appendChild(lbl);
              zeile.appendChild(val);
              karte.appendChild(zeile);
            });
          }
          liste.appendChild(karte);
        });
        body.appendChild(liste);
      })
      .catch(function (err) {
        body.innerHTML = "";
        body.appendChild(titel);
        var fehler = document.createElement("div");
        fehler.className = "dd-rolle-leer";
        fehler.textContent = "Fehler: " + err;
        body.appendChild(fehler);
      });
  }

  function oeffneRolle(rolle) {
    var d = _el("detail-drawer");
    if (!d) return;
    d.dataset.offen = "true";
    window.__letzteRolle = rolle;

    // Dynamischen Rollen-Tab anlegen oder updaten
    var tabsNav = d.querySelector(".dd-tabs");
    if (tabsNav) {
      var rollenTab = tabsNav.querySelector(".dd-tab.dd-rolle-tab");
      if (!rollenTab) {
        rollenTab = document.createElement("button");
        rollenTab.className = "dd-tab dd-rolle-tab";
        rollenTab.dataset.tab = "__rolle__";
        rollenTab.addEventListener("click", function () {
          if (window.__letzteRolle) oeffneRolle(window.__letzteRolle);
        });
        var closeBtn = tabsNav.querySelector(".dd-close");
        if (closeBtn) {
          tabsNav.insertBefore(rollenTab, closeBtn);
        } else {
          tabsNav.appendChild(rollenTab);
        }
      }
      rollenTab.textContent = rolle.charAt(0).toUpperCase() + rolle.slice(1);
    }

    // Nur Rollen-Tab aktiv, andere inaktiv
    d.querySelectorAll(".dd-tab").forEach(function (b) {
      b.classList.toggle("aktiv", b.dataset.tab === "__rolle__");
    });

    var body = _el("dd-body");
    if (!body) return;
    body.innerHTML = "";
    _renderRolle(body, rolle);
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

  window.WerkstattDetail = {
    oeffne: oeffne,
    oeffneRolle: oeffneRolle,
    schliesse: schliesse,
    setProjekt: setProjekt
  };

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
