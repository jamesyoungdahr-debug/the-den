const FIELDS = ["title","quality","source","codec","hdr","audio","group","language"], OPS = ["contains","equals","regex"]; let FORMATS = [], PROFILE = null;

async function fapi(method, path, body) {
  const res = await fetch("/api/formats" + path, {
    method,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!res.ok) {
    let d = res.statusText;
    try {
      d = (await res.json()).detail || d;
    } catch (e) {}
    throw new Error(d);
  }
  return res.status === 204 ? null : await res.json();
}

function fshow(elId, text, ok) {
  const el = document.getElementById(elId);
  el.textContent = text;
  el.className = "holt-message " + (ok ? "holt-message-positive" : "holt-message-warning");
  el.style.display = "block";
}

async function loadFormats() {
  try {
    let profiles;
    [FORMATS, profiles] = await Promise.all([fapi("GET",""), fapi("GET","/profiles")]);
    PROFILE = profiles[0] || null;
    document.getElementById("profile-qualities").value = PROFILE ? PROFILE.allowed_qualities : "";
    document.getElementById("profile-min-score").value = PROFILE ? PROFILE.min_format_score : 0;
    document.getElementById("profile-upgrade-score").value = PROFILE ? PROFILE.upgrade_until_score : 0;
    renderCutoff();
    renderFormats();
    document.getElementById("profile-qualities").oninput = renderCutoff;
  } catch (err) {
    fshow("format-result", err.message, false);
  }
}

function renderCutoff() {
  const qualities = document.getElementById("profile-qualities").value.split(",").map(s => s.trim()).filter(Boolean);
  const sel = document.getElementById("profile-cutoff");
  sel.innerHTML = "";
  for (const q of qualities) {
    const opt = document.createElement("option");
    opt.value = q;
    opt.textContent = q;
    if (PROFILE && PROFILE.cutoff === q) opt.selected = true;
    sel.appendChild(opt);
  }
}

function renderFormats() {
  const container = document.getElementById("format-list");
  if (!container) return;

  container.innerHTML = "";
  if (FORMATS.length === 0) {
    const empty = document.createElement("div");
    empty.className = "holt-empty";
    empty.textContent = "No formats";
    container.appendChild(empty);
    return;
  }

  for (const f of FORMATS) {
    const row = document.createElement("div");
    row.className = "holt-row";

    const main = document.createElement("div");
    main.className = "holt-row-main";

    const title = document.createElement("div");
    title.className = "holt-row-title";
    title.textContent = f.name;
    main.appendChild(title);

    const meta = document.createElement("div");
    meta.className = "holt-row-meta";
    if (f.rules.length === 0) {
      meta.textContent = "no rules";
    } else {
      meta.textContent = f.rules.map(r => `${r.negate ? "not " : ""}${r.field} ${r.op} "${r.value}"`).join(" · ");
    }
    main.appendChild(meta);

    if (f.builtin) {
      const badge = document.createElement("span");
      badge.className = "holt-badge holt-badge-pending";
      badge.innerHTML = '<span class="dot"></span>built-in';
      main.appendChild(badge);
    }

    row.appendChild(main);

    const scoreInput = document.createElement("input");
    scoreInput.type = "number";
    scoreInput.step = "1";
    scoreInput.style.width = "80px";
    scoreInput.dataset.score = f.id;
    scoreInput.value = PROFILE && PROFILE.scores[f.id] !== undefined ? PROFILE.scores[f.id] : 0;

    scoreInput.onchange = async function() {
      try {
        await fapi("PATCH", `/profiles/${PROFILE.id}`, { scores: { [f.id]: Number(this.value) } });
        fshow("format-result", "Saved score", true);
      } catch (err) {
        fshow("format-result", err.message, false);
      }
    };

    const actions = document.createElement("div");
    actions.className = "holt-row-actions";

    const editBtn = document.createElement("a");
    editBtn.href = "#";
    editBtn.className = "holt-btn holt-btn-quiet holt-btn-sm";
    editBtn.textContent = "edit";
    editBtn.onclick = function(ev) {
      ev.preventDefault();
      openFormat(f);
    };

    actions.appendChild(editBtn);

    if (!f.builtin) {
      const deleteBtn = document.createElement("a");
      deleteBtn.href = "#";
      deleteBtn.className = "holt-btn holt-btn-quiet holt-btn-sm";
      deleteBtn.textContent = "delete";
      deleteBtn.onclick = async function(ev) {
        ev.preventDefault();
        if (confirm("Delete this format?")) {
          try {
            await fapi("DELETE", `/${f.id}`);
            loadFormats();
          } catch (err) {
            fshow("format-result", err.message, false);
          }
        }
      };
      actions.appendChild(deleteBtn);
    }

    row.appendChild(scoreInput);
    row.appendChild(actions);

    container.appendChild(row);
  }
}

async function saveProfile() {
  try {
    const allowedQualities = document.getElementById("profile-qualities").value;
    const cutoff = document.getElementById("profile-cutoff").value;
    const minScore = Number(document.getElementById("profile-min-score").value);
    
    const payload = {};
    if (allowedQualities !== undefined) payload.allowed_qualities = allowedQualities;
    if (cutoff !== undefined) payload.cutoff = cutoff;
    if (minScore !== undefined) payload.min_format_score = minScore;
    payload.upgrade_until_score = Number(document.getElementById("profile-upgrade-score").value);

    PROFILE = await fapi("PATCH", `/profiles/${PROFILE.id}`, payload);
    fshow("format-result", "Profile saved", true);
  } catch (err) {
    fshow("format-result", err.message, false);
  }
}

function ruleRow(rule) {
  const row = document.createElement("div");
  row.style.display = "flex";
  row.style.gap = "6px";
  row.style.alignItems = "center";

  const fieldSel = document.createElement("select");
  fieldSel.dataset.field = "";
  for (const f of FIELDS) {
    const opt = document.createElement("option");
    opt.value = f;
    opt.textContent = f;
    if (rule && rule.field === f) opt.selected = true;
    fieldSel.appendChild(opt);
  }

  const opSel = document.createElement("select");
  opSel.dataset.op = "";
  for (const o of OPS) {
    const opt = document.createElement("option");
    opt.value = o;
    opt.textContent = o;
    if (rule && rule.op === o) opt.selected = true;
    opSel.appendChild(opt);
  }

  const valueInput = document.createElement("input");
  valueInput.type = "text";
  valueInput.placeholder = "value";
  valueInput.style.flex = "1";

  if (rule) valueInput.value = rule.value;

  const negateLabel = document.createElement("label");
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.dataset.negate = "";
  if (rule && rule.negate) checkbox.checked = true;
  negateLabel.appendChild(checkbox);
  negateLabel.appendChild(document.createTextNode("not"));

  const removeLink = document.createElement("a");
  removeLink.href = "#";
  removeLink.textContent = "remove";
  removeLink.className = "holt-btn holt-btn-quiet holt-btn-sm";
  removeLink.onclick = function(e) {
    e.preventDefault();
    row.remove();
  };

  row.appendChild(fieldSel);
  row.appendChild(opSel);
  row.appendChild(valueInput);
  row.appendChild(negateLabel);
  row.appendChild(removeLink);

  return row;
}

function addRule(rule) {
  const container = document.getElementById("format-rules");
  container.appendChild(ruleRow(rule));
}

function readRules() {
  const rows = document.querySelectorAll("#format-rules > div");
  const rules = [];
  for (const row of rows) {
    const fieldSel = row.querySelector('select[data-field]');
    const opSel = row.querySelector('select[data-op]');
    const valueInput = row.querySelector('input[type="text"]');
    const negateCheckbox = row.querySelector('input[data-negate]');

    if (!fieldSel || !opSel || !valueInput) continue;

    rules.push({
      field: fieldSel.value,
      op: opSel.value,
      value: valueInput.value,
      negate: !!negateCheckbox.checked
    });
  }
  return rules;
}

function openFormat(f) {
  const dialog = document.getElementById("format-dialog");
  const titleEl = document.getElementById("format-dialog-title");
  const idEl = document.getElementById("format-id");
  const nameEl = document.getElementById("format-name");
  const rulesContainer = document.getElementById("format-rules");
  const scoreInput = document.getElementById("format-score");

  if (f) {
    titleEl.textContent = "Edit format";
    idEl.value = f.id;
    nameEl.value = f.name;
    nameEl.disabled = f.builtin;
  } else {
    titleEl.textContent = "New format";
    idEl.value = "";
    nameEl.value = "";
    nameEl.disabled = false;
  }

  rulesContainer.innerHTML = "";
  if (f && f.rules.length > 0) {
    for (const rule of f.rules) addRule(rule);
  } else {
    addRule({field:"title", op:"contains", value:"", negate:false});
  }

  scoreInput.value = PROFILE && f ? (PROFILE.scores[f.id] ?? 0) : 0;

  dialog.showModal();
}

async function saveFormat() {
  const name = document.getElementById("format-name").value;
  const rules = readRules();
  const id = document.getElementById("format-id").value;
  const score = Number(document.getElementById("format-score").value);

  try {
    let result;
    if (id) {
      result = await fapi("PUT", `/${id}`, { name, rules });
    } else {
      result = await fapi("POST", "", { name, rules });
    }

    if (PROFILE) {
      await fapi("PATCH", `/profiles/${PROFILE.id}`, { scores: { [result.id]: score } });
    }

    document.getElementById("format-dialog").close();
    fshow("format-result", "Format saved", true);
    loadFormats();
  } catch (err) {
    fshow("format-result", err.message, false);
  }
}

async function testTitle() {
  const title = document.getElementById("format-test-title").value.trim();
  if (!title) return;

  try {
    const r = await fapi("POST", "/test", { title });
    let text = `score ${r.score} · ${r.formats.length ? r.formats.join(", ") : "no formats matched"} · ${r.attrs.quality} ${r.attrs.source} ${r.attrs.codec} ${r.attrs.hdr} ${r.attrs.audio} ${r.attrs.group}`;
    text = text.replace(/\s+/g, " ");
    fshow("format-test-result", text, true);
  } catch (err) {
    fshow("format-test-result", err.message, false);
  }
}

if (document.getElementById("format-list")) loadFormats();