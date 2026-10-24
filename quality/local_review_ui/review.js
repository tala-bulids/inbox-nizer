"use strict";
const token = location.hash.slice(1);
const el = (id) => document.getElementById(id);
let state;
let busy = false;
// Embedded/private browsers may deny storage. Remembering a name is optional;
// neither initialization nor reviewing may depend on storage being available.
try { el("reviewer").value = localStorage.getItem("local-reviewer-name") || ""; }
catch { el("reviewer").value = ""; }
el("reviewer").addEventListener("input", () => {
  el("reviewer").setCustomValidity("");
  controls();
  try { localStorage.setItem("local-reviewer-name", el("reviewer").value); }
  catch { /* The typed name remains available in this tab. */ }
});
function controls() {
  const noRow = !state?.row;
  const noName = !el("reviewer").value.trim();
  el("reviewer-help").textContent = noName ? "Enter your name once, then choose a label. Your choice saves automatically." : "Your name is set. Choose a label to save and continue.";
  document.querySelectorAll("#labels button").forEach((b) => { b.disabled = busy || noRow; });
  el("ambiguous").disabled = busy || noRow;
  el("skip").disabled = busy || noRow;
  el("previous").disabled = busy || !state || state.cursor === 0;
  el("remaining").disabled = busy;
}
function show() {
  const row = state.row;
  el("progress").textContent = `${state.completed} / ${state.queued} reviewed · ${state.skipped} skipped · ${row ? `Email ${state.cursor + 1} of ${state.queued}` : "End of queue"}`;
  el("email").hidden = !row;
  el("decisions").hidden = !row;
  el("remaining").hidden = !!row || state.completed === state.queued;
  el("ambiguous").hidden = !row;
  el("skip").hidden = !row;
  if (row) {
    el("subject").textContent = row.subject || "(No subject)";
    el("sender").textContent = row.sender;
    el("date").textContent = row.date;
    el("body").textContent = row.body || "(Empty body)";
    el("body").scrollTop = 0;
    el("prior").textContent = row.ambiguous === "yes" ? `Saved: Ambiguous · ${row.reviewer}` : row.gold_label ? `Saved: ${row.gold_label} · ${row.reviewer}` : "Read the email, then choose a label.";
    el("labels").replaceChildren();
    state.labels.forEach((label) => {
      const button = document.createElement("button");
      button.textContent = label;
      button.classList.toggle("selected", row.gold_label === label);
      button.addEventListener("click", () => action("label", label));
      el("labels").append(button);
    });
  }
  controls();
}
async function request(path, body) {
  const response = await fetch(path, {method: body ? "POST" : "GET", cache: "no-store", headers: {"X-Review-Token": token, ...(body ? {"Content-Type": "application/json"} : {})}, ...(body ? {body: JSON.stringify(body)} : {})});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Could not save. Reload to check progress.");
  return data;
}
async function action(kind, label = "") {
  if (busy || !state) return;
  if (["label", "ambiguous"].includes(kind) && !el("reviewer").value.trim()) {
    el("reviewer").setCustomValidity("Enter your reviewer name before saving a label.");
    el("reviewer").focus();
    el("reviewer").reportValidity();
    return;
  }
  busy = true;
  controls();
  el("error").textContent = "";
  el("save").textContent = "Saving…";
  try {
    state = await request("/action", {action: kind, label, reviewer: el("reviewer").value, revision: state.revision, cursor: state.cursor});
    el("save").textContent = ["label", "ambiguous"].includes(kind) ? "Saved to development.csv ✓" : "Position saved ✓";
    show();
  } catch (error) {
    el("save").textContent = "Save not confirmed";
    el("error").textContent = error.message;
  } finally { busy = false; controls(); }
}
for (const kind of ["previous", "ambiguous", "skip", "remaining"]) el(kind).addEventListener("click", () => action(kind));
controls();
request("/state").then((data) => {state = data; show(); el("save").textContent = "Ready";}).catch((error) => {el("save").textContent = "Could not load"; el("error").textContent = error.message;});
