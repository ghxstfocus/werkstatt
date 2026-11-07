// Runs-Liste (OP-233): OPs aus docs/STATUS.md via /api/projects/{name}/ops
(function () {
  "use strict";
  var aktuellesProjekt = "werkstatt";

  function _el(id) { return document.getElementById(id); }

  function _rendere(ops) {
    var box = _el("runs-liste");
    if (!box) return;
    box.innerHTML = "";
    var offen = 0, done = 0;
    ops.forEach(function (op) {
      var div = document.createElement("div");
      div.className = "runs-eintrag";
      div.dataset.status = op.status;
      div.dataset.opId = op.id;
      div.title = op.titel;
      var id = document.createElement("span");
      id.className = "runs-id";
      id.textContent = op.id;
      var status = document.createElement("span");
      status.className = "runs-status";
      status.textContent = op.status;
      div.appendChild(id);
      div.appendChild(document.createTextNode(op.titel.length > 22 ? op.titel.slice(0, 22) + "…" : op.titel));
      div.appendChild(status);
      box.appendChild(div);
      if (op.status === "open") offen++;
      else if (op.status === "done") done++;
    });
    var c = _el("runs-counter");
    if (c) c.textContent = offen + " offen / " + done + " done";
  }

  function lade(projekt) {
    if (projekt) aktuellesProjekt = projekt;
    fetch("/api/projects/" + encodeURIComponent(aktuellesProjekt) + "/ops",
          {credentials: "same-origin"})
      .then(function (r) { return r.ok ? r.json() : {ops: []}; })
      .then(function (d) { _rendere(d.ops || []); })
      .catch(function () {});
  }

  window.WerkstattRuns = { lade: lade };
  document.addEventListener("DOMContentLoaded", function () { lade(); });
  setInterval(function () { lade(); }, 30000);
})();
