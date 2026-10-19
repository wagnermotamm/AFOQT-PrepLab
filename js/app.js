const STORE = "afoqt-treino-v1";
const LETTERS = "ABCDE";

const COMPOSITE_TEXT = {
  "Piloto": "Mede o que o panfleto liga ao treino de piloto: quantidade, atitude da aeronave pelos instrumentos, conceitos aeronáuticos e velocidade de percepção.",
  "Navegador-Técnico": "Compartilha parte do composto de piloto, sem atitude da aeronave e sem conceitos aeronáuticos. Entram aptidão verbal, aptidão espacial, velocidade de percepção e ciências.",
  "Aptidão acadêmica": "Junta os subtestes que formam os compostos Verbal e Quantitativo.",
  "Verbal": "Mede relações entre palavras e sinônimos.",
  "Quantitativo": "Mede raciocínio com relações aritméticas e o uso de termos e fórmulas."
};

const state = {
  bank: null,
  view: "home",
  session: null
};

let popBtn = null;

const app = () => document.getElementById("app");

function esc(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[ch]));
}

function escapeReg(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function decorate(text, glossary) {
  const items = [...(glossary || [])]
    .filter((item) => item.word && item.meaning)
    .sort((a, b) => b.word.length - a.word.length);
  let source = String(text ?? "");
  const slots = [];
  items.forEach((item) => {
    const re = new RegExp(`(?<![A-Za-z0-9])${escapeReg(item.word)}(?![A-Za-z0-9])`, "gi");
    source = source.replace(re, (match) => {
      const index = slots.length;
      slots.push({ match, meaning: item.meaning });
      return `\u0001${index}\u0001`;
    });
  });
  return source.split(/\u0001(\d+)\u0001/).map((part, index) => {
    if (index % 2 === 0) return esc(part);
    const slot = slots[Number(part)];
    return `<button type="button" class="term" data-meaning="${esc(slot.meaning)}">${esc(slot.match)}</button>`;
  }).join("");
}

function meaningOf(question, word) {
  const found = (question.glossary || []).find((item) => item.word === word);
  return found ? found.meaning : "";
}

function termButton(label, meaning) {
  return `<button type="button" class="term" data-meaning="${esc(meaning)}">${esc(label)}</button>`;
}

function fractionHtml(num, den) {
  return `<span class="frac"><span>${esc(num)}</span><span>${esc(den)}</span></span>`;
}

function fmtAxis(n) {
  return n > 0 ? `+${n}` : String(n);
}

function shuffle(list) {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function shuffledOptions(ids) {
  const original = ids.join("|");
  let order = shuffle(ids);
  let guard = 0;
  while (order.join("|") === original && guard < 6) {
    order = shuffle(ids);
    guard += 1;
  }
  return order;
}

function byId(id) {
  return state.bank.questions.find((question) => question.id === id);
}

function themeById(id) {
  return state.bank.themes.find((theme) => theme.id === id);
}

function catalog() {
  const tested = state.bank.themes.map((theme) => ({
    ...theme,
    kind: "test",
    sample: state.bank.questions.filter((question) => question.theme === theme.id).length
  }));
  const info = state.bank.notIncluded.map((theme) => ({ ...theme, kind: "info" }));
  return [...tested, ...info].sort((a, b) => a.part - b.part);
}

function elapsed() {
  const session = state.session;
  if (!session) return 0;
  const end = session.finishedAt || Date.now();
  return Math.max(0, end - session.startedAt);
}

function formatClock(ms) {
  const total = Math.floor(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
}

function formatWritten(ms) {
  const total = Math.floor(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h) return `${h} h ${m} min ${String(s).padStart(2, "0")} s`;
  if (m) return `${m} min ${String(s).padStart(2, "0")} s`;
  return `${s} s`;
}

function statusOf(id) {
  const session = state.session;
  if (!Object.prototype.hasOwnProperty.call(session.answers, id)) return "blank";
  return session.answers[id] === byId(id).correct ? "ok" : "bad";
}

function counts() {
  const tally = { ok: 0, bad: 0, blank: 0, total: state.session.questionIds.length };
  state.session.questionIds.forEach((id) => {
    tally[statusOf(id)] += 1;
  });
  return tally;
}

function percent(ok, total) {
  if (!total) return 0;
  return Math.round((ok / total) * 100);
}

function currentQuestion() {
  return byId(state.session.questionIds[state.session.index]);
}

function isRevealed(question) {
  return Boolean(state.session.finishedAt)
    || Object.prototype.hasOwnProperty.call(state.session.answers, question.id);
}

function save() {
  if (!state.session) {
    localStorage.removeItem(STORE);
    return;
  }
  localStorage.setItem(STORE, JSON.stringify({ view: state.view, session: state.session }));
}

function restore() {
  try {
    const raw = localStorage.getItem(STORE);
    if (!raw) return;
    const data = JSON.parse(raw);
    if (!data.session || data.session.version !== state.bank.version) return;
    const known = new Set(state.bank.questions.map((question) => question.id));
    if (!data.session.questionIds.every((id) => known.has(id))) return;
    state.session = data.session;
    state.view = data.view === "exam" || data.view === "results" ? data.view : "home";
    if (state.session.finishedAt && state.view === "exam") state.view = "results";
  } catch (error) {
    localStorage.removeItem(STORE);
  }
}

function validate(bank) {
  if (!bank || !Array.isArray(bank.themes) || !Array.isArray(bank.questions)) {
    return ["banco incompleto"];
  }
  const themes = new Set(bank.themes.map((theme) => theme.id));
  const seen = new Set();
  const errors = [];
  bank.questions.forEach((question) => {
    if (seen.has(question.id)) errors.push(`id repetido: ${question.id}`);
    seen.add(question.id);
    if (!themes.has(question.theme)) errors.push(`tema inválido: ${question.id}`);
    const options = Array.isArray(question.options) ? question.options : [];
    if (options.length < 2) {
      errors.push(`opções inválidas: ${question.id}`);
      return;
    }
    if (!options.some((option) => option.id === question.correct)) {
      errors.push(`gabarito inválido: ${question.id}`);
    }
    if (question.usesTable) {
      if (!bank.table || !Array.isArray(bank.table.x) || !Array.isArray(bank.table.rows)) {
        errors.push(`tabela ausente: ${question.id}`);
        return;
      }
      const col = bank.table.x.indexOf(question.x);
      const row = bank.table.rows.find((item) => item.y === question.y);
      const value = row && col >= 0 ? String(row.cells[col]) : "";
      const correct = options.find((option) => option.id === question.correct);
      if (!correct || correct.text !== value) errors.push(`tabela divergente: ${question.id}`);
    }
  });
  return errors;
}

function startSession(themeId) {
  const questions = state.bank.questions.filter((question) => !themeId || question.theme === themeId);
  const optionOrder = {};
  questions.forEach((question) => {
    optionOrder[question.id] = shuffledOptions(question.options.map((option) => option.id));
  });
  state.session = {
    version: state.bank.version,
    themeId: themeId || null,
    questionIds: questions.map((question) => question.id),
    optionOrder,
    answers: {},
    hints: {},
    index: 0,
    startedAt: Date.now(),
    finishedAt: null
  };
  state.view = "exam";
  save();
  render({ scroll: "top" });
}

function go(index) {
  const max = state.session.questionIds.length - 1;
  state.session.index = Math.max(0, Math.min(max, index));
  state.view = "exam";
  save();
  render({ scroll: "top" });
}

function nextBlank(from) {
  const ids = state.session.questionIds;
  for (let step = 1; step <= ids.length; step += 1) {
    const index = (from + step) % ids.length;
    if (!Object.prototype.hasOwnProperty.call(state.session.answers, ids[index])) return index;
  }
  return -1;
}

function firstProblem() {
  const ids = state.session.questionIds;
  let blank = -1;
  for (let index = 0; index < ids.length; index += 1) {
    const status = statusOf(ids[index]);
    if (status === "bad") return index;
    if (status === "blank" && blank < 0) blank = index;
  }
  return blank >= 0 ? blank : 0;
}

function ask(title, text, okLabel, cancelLabel) {
  return new Promise((resolve) => {
    const root = document.createElement("div");
    root.className = "modal-back";
    root.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true">
        <h2>${esc(title)}</h2>
        <p>${esc(text)}</p>
        <div class="row-actions">
          <button type="button" class="quiet" data-cancel>${esc(cancelLabel)}</button>
          <button type="button" class="primary" data-ok>${esc(okLabel)}</button>
        </div>
      </div>`;
    const close = (value) => {
      root.remove();
      resolve(value);
    };
    root.querySelector("[data-ok]").addEventListener("click", () => close(true));
    root.querySelector("[data-cancel]").addEventListener("click", () => close(false));
    document.body.appendChild(root);
    root.querySelector("[data-ok]").focus();
  });
}

function announce(message) {
  const live = document.getElementById("live");
  if (live) live.textContent = message;
}

function closePop() {
  const pop = document.getElementById("pop");
  if (pop) pop.hidden = true;
  popBtn = null;
}

function openPop(button) {
  const pop = document.getElementById("pop");
  if (popBtn === button && !pop.hidden) {
    closePop();
    return;
  }
  popBtn = button;
  pop.hidden = false;
  pop.querySelector("[data-word]").textContent = button.textContent.trim();
  pop.querySelector("[data-mean]").textContent = button.dataset.meaning || "";
  const rect = button.getBoundingClientRect();
  const width = Math.min(300, window.innerWidth - 16);
  let left = rect.left;
  if (left + width > window.innerWidth - 8) left = window.innerWidth - width - 8;
  pop.style.width = `${width}px`;
  pop.style.left = `${Math.max(8, left)}px`;
  pop.style.top = `${rect.bottom + 8}px`;
  const height = pop.offsetHeight;
  if (rect.bottom + 8 + height > window.innerHeight) {
    pop.style.top = `${Math.max(8, rect.top - height - 8)}px`;
  }
}

function headerHtml() {
  const inRun = state.session && state.view !== "home";
  const tally = inRun ? counts() : null;
  const scope = state.session && state.session.themeId
    ? themeById(state.session.themeId).name
    : "Simulado completo";
  const meta = inRun
    ? `${scope} · ${tally.total} perguntas`
    : "Questões de exemplo do panfleto oficial";
  const chips = tally ? `
    <div class="scorechips">
      <span class="chip ok">${tally.ok} ${tally.ok === 1 ? "certa" : "certas"}</span>
      <span class="chip bad">${tally.bad} ${tally.bad === 1 ? "errada" : "erradas"}</span>
      <span class="chip wait">${tally.blank} em branco</span>
    </div>` : "";
  const clock = inRun ? `<div class="clock" id="timer">${formatClock(elapsed())}</div>` : "";
  let action = "";
  if (state.view === "exam" && state.session && !state.session.finishedAt) {
    action = `<button type="button" class="ghost" data-action="finish">Encerrar</button>`;
  } else if (state.session && state.view !== "home") {
    action = `<button type="button" class="ghost" data-action="home">Início</button>`;
  }
  return `
    <header class="top">
      <div class="brand">
        <strong>AFOQT · TREINO</strong>
        <span>${esc(meta)}</span>
      </div>
      <div class="top-side">
        ${chips}
        ${clock}
        ${action}
      </div>
    </header>`;
}

function navHtml() {
  if (!state.session || state.view === "home") return "";
  const groups = [];
  state.session.questionIds.forEach((id, index) => {
    const theme = themeById(byId(id).theme);
    const last = groups[groups.length - 1];
    if (!last || last.theme.id !== theme.id) groups.push({ theme, items: [] });
    groups[groups.length - 1].items.push({ id, index });
  });
  const finished = Boolean(state.session.finishedAt);
  const groupsHtml = groups.map((group) => {
    const buttons = group.items.map(({ id, index }) => {
      const status = statusOf(id);
      const classes = ["qbtn"];
      if (status === "ok") classes.push("is-ok");
      if (status === "bad") classes.push("is-bad");
      if (status === "blank" && finished) classes.push("is-blank-done");
      if (state.view === "exam" && index === state.session.index) classes.push("is-current");
      const name = status === "ok" ? "certa" : status === "bad" ? "errada" : "sem resposta";
      const mark = status === "ok" ? "✓" : status === "bad" ? "✗" : finished ? "–" : "";
      return `<button type="button" class="${classes.join(" ")}" data-action="goto" data-index="${index}" aria-label="Pergunta ${index + 1}, ${name}"><b>${index + 1}</b><small>${mark}</small></button>`;
    }).join("");
    return `<section class="qgroup"><p>Parte ${group.theme.part} · ${esc(group.theme.name)}</p><div class="qgrid">${buttons}</div></section>`;
  }).join("");
  return `
    <nav class="qnav" aria-label="Todas as perguntas">
      <h2>Perguntas</h2>
      <p class="legend"><span><i>✓</i> certa</span><span><i>✗</i> errada</span><span>número = em branco</span></p>
      <div class="qnav-scroll">${groupsHtml}</div>
    </nav>`;
}

function stemHtml(question) {
  if (question.display === "fraction-sum") {
    const parts = question.terms.map(([num, den]) => fractionHtml(num, den)).join('<span class="op">+</span>');
    return `<div class="math-stem"><div class="formula">${parts}</div><p class="stem">${decorate(question.prompt, question.glossary)}</p></div>`;
  }
  if (question.display === "neg-ninth-sqrt") {
    const left = termButton("−1/9", meaningOf(question, "−1/9"));
    const right = termButton("√81", meaningOf(question, "√81"));
    return `<p class="stem">${decorate(question.prompt, question.glossary)} <span class="formula-inline">(${left}) × ${right}</span> ${decorate(question.trail, question.glossary)}</p>`;
  }
  return `<p class="stem">${decorate(question.prompt, question.glossary)}</p>`;
}

function tableHtml(question, revealed) {
  if (!question.usesTable) return "";
  const table = state.bank.table;
  const head = table.x.map((x) => `<th class="${revealed && x === question.x ? "hit-axis" : ""}">${fmtAxis(x)}</th>`).join("");
  const body = table.rows.map((row) => {
    const cells = row.cells.map((value, index) => {
      const hit = revealed && table.x[index] === question.x && row.y === question.y;
      return `<td class="${hit ? "hit" : ""}">${value}</td>`;
    }).join("");
    return `<tr><th class="${revealed && row.y === question.y ? "hit-axis" : ""}">${fmtAxis(row.y)}</th>${cells}</tr>`;
  }).join("");
  return `
    <p class="axes"><span>X = ${fmtAxis(question.x)}</span><span>Y = ${fmtAxis(question.y)}</span></p>
    <table class="gridtab">
      <caption>X é a coluna, no topo. Y é a linha, à esquerda. Depois de responder, o cruzamento certo fica marcado.</caption>
      <thead><tr><th>Y \\ X</th>${head}</tr></thead>
      <tbody>${body}</tbody>
    </table>`;
}

function optionsHtml(question) {
  const session = state.session;
  const revealed = isRevealed(question);
  const picked = session.answers[question.id];
  const order = session.optionOrder[question.id];
  return `<div class="options">${order.map((optionId, index) => {
    const option = question.options.find((item) => item.id === optionId);
    const isCorrect = optionId === question.correct;
    let cls = "option";
    let flag = "";
    if (revealed && isCorrect) {
      cls += " good";
      flag = "Correta";
    } else if (revealed && picked === optionId) {
      cls += " bad";
      flag = "Sua escolha";
    }
    return `
      <div class="${cls}" role="button" tabindex="${revealed ? "-1" : "0"}" data-action="answer" data-option="${esc(optionId)}" aria-disabled="${revealed}">
        <span class="badge">${LETTERS[index]}</span>
        <span class="otext">${decorate(option.text, question.glossary)}</span>
        <span class="flag">${flag}</span>
      </div>`;
  }).join("")}</div>`;
}

function feedbackHtml(question) {
  const picked = state.session.answers[question.id];
  const reviewBlank = !picked && state.session.finishedAt;
  if (!picked && !reviewBlank) return "";
  const ok = picked === question.correct;
  const order = state.session.optionOrder[question.id];
  const correct = question.options.find((option) => option.id === question.correct);
  const letter = LETTERS[order.indexOf(question.correct)];
  const paras = (question.explanation || []).map((line) => `<p>${esc(line)}</p>`).join("");
  const correctLine = `<p>A alternativa correta, nesta ordem, é ${letter}. ${esc(correct.text)}.</p>`;
  if (reviewBlank) return `<div class="feedback"><strong>Em branco.</strong>${correctLine}${paras}</div>`;
  if (ok) return `<div class="feedback good"><strong>Certa.</strong>${paras}</div>`;
  return `<div class="feedback bad"><strong>Errada.</strong>${correctLine}${paras}</div>`;
}

function hintHtml(question) {
  if (state.session.hints[question.id]) {
    return `<div class="hint"><p class="hint-k">Dica</p><p>${esc(question.hint)}</p></div>`;
  }
  return `<button type="button" class="hint-btn" data-action="hint">Ver dica</button>`;
}

function examHtml() {
  const session = state.session;
  const question = currentQuestion();
  const theme = themeById(question.theme);
  const total = session.questionIds.length;
  const index = session.index;
  const revealed = isRevealed(question);
  const review = session.finishedAt
    ? `<p class="banner">Revisão. A resposta desta tentativa continua travada. O tempo exibido é o tempo final.</p>`
    : "";
  const blankIndex = nextBlank(index);
  const blankBtn = blankIndex >= 0 && !session.finishedAt
    ? `<button type="button" class="quiet" data-action="blank-next">Próxima em branco</button>`
    : "";
  const back = session.finishedAt
    ? `<button type="button" class="quiet" data-action="results">Voltar ao resultado</button>`
    : "";
  return `
    ${review}
    <article class="sheet">
      <div class="sheet-top">
        <p>Parte ${theme.part} · ${esc(theme.name)}</p>
        <p>Pergunta ${index + 1} de ${total}</p>
      </div>
      <p class="how">${esc(theme.direction)}</p>
      ${stemHtml(question)}
      <p class="dict-note">Palavra sublinhada: significado em português. A dica explica o caminho sem entregar a letra.</p>
      ${tableHtml(question, revealed)}
      ${hintHtml(question)}
      ${optionsHtml(question)}
      ${feedbackHtml(question)}
      <div class="pager">
        <button type="button" class="quiet" data-action="prev" ${index === 0 ? "disabled" : ""}>Anterior</button>
        <div class="row-actions">
          ${blankBtn}
          ${back}
          <button type="button" class="primary" data-action="next" ${index === total - 1 ? "disabled" : ""}>Próxima</button>
        </div>
      </div>
    </article>`;
}

function resultsHtml() {
  const tally = counts();
  const pct = percent(tally.ok, tally.total);
  const phrase = pct >= 90
    ? "Quase todas as questões de exemplo ficaram claras."
    : pct >= 70
      ? "A maior parte fechou. Vale refazer o que errou, com a dica."
      : pct >= 50
        ? "Metade do caminho está feita. O dicionário e a dica mostram o raciocínio de cada tema."
        : "Refaça um tema de cada vez e leia a dica antes de marcar.";
  const byTheme = new Map();
  state.session.questionIds.forEach((id) => {
    const themeId = byId(id).theme;
    if (!byTheme.has(themeId)) byTheme.set(themeId, { ok: 0, bad: 0, blank: 0 });
    byTheme.get(themeId)[statusOf(id)] += 1;
  });
  const bars = [...byTheme.entries()].map(([themeId, item]) => {
    const theme = themeById(themeId);
    const total = item.ok + item.bad + item.blank;
    return `
      <div class="bar-row">
        <div>Parte ${theme.part} · ${esc(theme.name)}</div>
        <div class="track" aria-hidden="true"><span style="width:${percent(item.ok, total)}%"></span></div>
        <div class="bar-meta">${item.ok}/${total} · ${item.bad} ${item.bad === 1 ? "errada" : "erradas"} · ${item.blank} em branco</div>
      </div>`;
  }).join("");
  const scope = state.session.themeId
    ? `do tema ${themeById(state.session.themeId).name}`
    : "do simulado completo";
  const okWord = tally.ok === 1 ? "certa" : "certas";
  const badWord = tally.bad === 1 ? "errada" : "erradas";
  return `
    <article class="sheet">
      <p class="kicker">Resultado ${esc(scope)}</p>
      <div class="score-wrap">
        <p class="score-num">${pct}<small>%</small></p>
        <div>
          <h2>Sua nota</h2>
          <p class="score-copy">${tally.ok} ${okWord}, ${tally.bad} ${badWord} e ${tally.blank} em branco, de ${tally.total}. A nota é o percentual de acertos sobre o total. ${phrase}</p>
          <p class="score-copy">Tempo: <strong>${formatWritten(elapsed())}</strong> (${formatClock(elapsed())}).</p>
        </div>
      </div>
      <div class="bars">${bars}</div>
      <div class="row-actions">
        <button type="button" class="primary" data-action="review">Rever questões</button>
        <button type="button" class="quiet" data-action="retry">Novo simulado deste conjunto</button>
        <button type="button" class="quiet" data-action="home">Início</button>
      </div>
    </article>`;
}

function homeHtml(errors) {
  const total = state.bank.questions.length;
  const themes = state.bank.themes.length;
  const outside = state.bank.notIncluded.reduce((sum, item) => sum + item.sample, 0);
  const rows = catalog().map((row) => {
    const inSim = row.kind === "test" ? String(row.sample) : "fora da nota";
    const tags = (row.composites || []).map((name) => `<span class="tag">${esc(name)}</span>`).join("");
    const why = row.kind === "info" ? `<p class="why">${esc(row.why)}</p>` : "";
    const action = row.kind === "test"
      ? `<button type="button" class="mini" data-action="start" data-theme="${esc(row.id)}">Treinar</button>`
      : "";
    return `
      <tr class="${row.kind === "info" ? "is-out" : ""}">
        <td><span class="partno">${row.part}</span></td>
        <td><strong>${esc(row.name)}</strong><span class="theme-en">${esc(row.english)}</span><div class="tags">${tags}</div>${why}</td>
        <td>${inSim}</td>
        <td>${row.sample}</td>
        <td>${row.realItems} itens · ${row.realMinutes} min</td>
        <td>${action}</td>
      </tr>`;
  }).join("");
  const composites = Object.keys(COMPOSITE_TEXT).map((name) => {
    const parts = catalog().filter((row) => (row.composites || []).includes(name));
    const list = parts.map((row) => `Parte ${row.part} ${row.name}`).join(", ");
    return `<p><strong>${esc(name)}.</strong> ${esc(COMPOSITE_TEXT[name])} Neste panfleto: ${esc(list)}.</p>`;
  }).join("");
  let resume = "";
  if (state.session && !state.session.finishedAt) {
    const tally = counts();
    const done = tally.ok + tally.bad;
    resume = `
      <div class="resume">
        <div><strong>Há um simulado em andamento.</strong><br>${done} de ${tally.total} respondidas · ${formatWritten(elapsed())}</div>
        <div class="row-actions">
          <button type="button" class="primary" data-action="resume">Continuar</button>
          <button type="button" class="quiet" data-action="discard">Descartar</button>
        </div>
      </div>`;
  } else if (state.session && state.session.finishedAt) {
    const tally = counts();
    resume = `
      <div class="resume">
        <div><strong>Último resultado:</strong> ${percent(tally.ok, tally.total)}% em ${formatWritten(elapsed())}.</div>
        <button type="button" class="quiet" data-action="results">Abrir resultado</button>
      </div>`;
  }
  const errorBox = errors.length ? `<p class="banner">O banco tem inconsistências: ${esc(errors.join(" · "))}</p>` : "";
  return `
    <main class="home">
      ${errorBox}
      <section class="hero">
        <p class="kicker">AFOQT Information Pamphlet</p>
        <h1>Simulado de treino</h1>
        <p class="lede">As perguntas escritas do panfleto, com dicionário em português, uma dica em cada item e a ordem das alternativas mudando a cada tentativa. O teste real é em inglês.</p>
        <p class="lede"><a href="treino.html">Abrir o banco original da estrutura de 2026</a>. Esse outro treino não usa as questões deste panfleto.</p>
        ${resume}
        <div class="stats">
          <div class="stat"><b>${total}</b><span>perguntas neste simulado</span></div>
          <div class="stat"><b>${themes}</b><span>temas com gabarito</span></div>
          <div class="stat"><b>12</b><span>partes no panfleto</span></div>
        </div>
        <div class="hero-actions">
          <button type="button" class="primary" data-action="start">Iniciar as ${total}</button>
        </div>
      </section>
      <section class="panel">
        <h2>Partes do panfleto</h2>
        <p class="note">Sete partes entram na nota. As outras cinco ficam listadas para mostrar a separação: quatro dependem de figura e uma não tem certo nem errado. Há ${outside} exemplos nessas cinco partes.</p>
        <table class="catalog">
          <thead>
            <tr>
              <th>Parte</th>
              <th>Tema</th>
              <th>No simulado</th>
              <th>Amostra</th>
              <th>Prova real</th>
              <th></th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </section>
      <section class="panel" style="padding:18px">
        <h2>Durante a prova</h2>
        <div class="steps">
          <div><strong>Menu sempre visível</strong>Dá para sair da pergunta sem responder e voltar depois. Verde é certa, vermelho é errada.</div>
          <div><strong>Resposta na hora</strong>O primeiro clique trava a questão e mostra se estava certa. A letra muda de lugar a cada tentativa.</div>
          <div><strong>Dicionário e dica</strong>Toque na palavra sublinhada para o sentido em português. A dica mostra o raciocínio sem dizer a letra.</div>
          <div><strong>Tempo e nota</strong>O relógio corre do início ao encerramento. No fim, a nota é o percentual de acertos, também por tema.</div>
        </div>
      </section>
      <details class="fold">
        <summary>Os cinco compostos da prova real</summary>
        ${composites}
      </details>
      <p class="foot">Banco local: <code>data/questions.json</code>. Abra por <code>iniciar.bat</code> para o navegador conseguir ler o arquivo. As alternativas A–E da tela não são as letras impressas no panfleto.</p>
    </main>`;
}

function render(options = {}) {
  closePop();
  const nav = document.querySelector(".qnav");
  const navTop = nav ? nav.scrollTop : 0;
  const errors = state.bank ? validate(state.bank) : [];
  let main = "";
  if (state.view === "exam") main = `<div class="layout">${navHtml()}${examHtml()}</div>`;
  else if (state.view === "results") main = `<div class="layout">${navHtml()}${resultsHtml()}</div>`;
  else main = homeHtml(errors);
  app().innerHTML = `${headerHtml()}${main}`;
  const nextNav = document.querySelector(".qnav");
  if (nextNav && options.scroll !== "top") nextNav.scrollTop = navTop;
  if (options.scroll === "top") {
    window.scrollTo(0, 0);
    document.querySelector(".qbtn.is-current")?.scrollIntoView({ block: "nearest" });
  }
  if (options.scroll === "feedback") {
    document.querySelector(".feedback")?.scrollIntoView({ block: "nearest" });
  }
}

function renderFetchError() {
  app().innerHTML = `
    <main class="error">
      <p class="kicker">Banco não carregou</p>
      <h1>Abra o simulado pelo iniciar.bat</h1>
      <p>O banco fica em <code>data/questions.json</code>. O navegador não deixa a página solta ler esse arquivo. Dê dois cliques em <code>iniciar.bat</code>, na mesma pasta. Ele sobe um servidor local e abre o simulado.</p>
    </main>`;
}

function tick() {
  const timer = document.getElementById("timer");
  if (!timer || !state.session || state.session.finishedAt) return;
  timer.textContent = formatClock(elapsed());
}

async function onClick(event) {
  const term = event.target.closest(".term");
  if (term) {
    event.preventDefault();
    openPop(term);
    return;
  }
  if (event.target.closest("#pop")) return;
  closePop();
  const el = event.target.closest("[data-action]");
  if (!el || el.disabled) return;
  const action = el.dataset.action;
  if (action === "start") {
    const themeId = el.dataset.theme || null;
    if (state.session && !state.session.finishedAt) {
      const replace = await ask(
        "Começar de novo?",
        "Há um simulado em andamento. Um novo embaralha as alternativas e zera o tempo.",
        "Começar de novo",
        "Continuar o atual"
      );
      if (!replace) {
        state.view = "exam";
        save();
        render({ scroll: "top" });
        return;
      }
    }
    startSession(themeId);
    return;
  }
  if (action === "resume") {
    state.view = "exam";
    save();
    render({ scroll: "top" });
    return;
  }
  if (action === "discard") {
    const ok = await ask("Descartar o simulado?", "O tempo e as respostas desta tentativa serão apagados.", "Descartar", "Cancelar");
    if (!ok) return;
    state.session = null;
    state.view = "home";
    save();
    render();
    return;
  }
  if (action === "home") {
    state.view = "home";
    save();
    render({ scroll: "top" });
    return;
  }
  if (action === "results") {
    state.view = "results";
    save();
    render({ scroll: "top" });
    return;
  }
  if (action === "goto") {
    go(Number(el.dataset.index));
    return;
  }
  if (action === "prev") {
    go(state.session.index - 1);
    return;
  }
  if (action === "next") {
    go(state.session.index + 1);
    return;
  }
  if (action === "blank-next") {
    const index = nextBlank(state.session.index);
    if (index >= 0) go(index);
    return;
  }
  if (action === "hint") {
    state.session.hints[currentQuestion().id] = true;
    save();
    render();
    return;
  }
  if (action === "answer") {
    const question = currentQuestion();
    if (state.session.finishedAt || Object.prototype.hasOwnProperty.call(state.session.answers, question.id)) return;
    state.session.answers[question.id] = el.dataset.option;
    save();
    const ok = el.dataset.option === question.correct;
    render({ scroll: "feedback" });
    announce(ok ? "Resposta certa." : "Resposta errada.");
    return;
  }
  if (action === "finish") {
    const tally = counts();
    if (tally.blank > 0) {
      const ok = await ask(
        "Encerrar agora?",
        `Ainda há ${tally.blank} sem resposta. Elas ficam em branco e não somam ponto.`,
        "Ver resultado",
        "Voltar à prova"
      );
      if (!ok) return;
    }
    state.session.finishedAt = Date.now();
    state.view = "results";
    save();
    render({ scroll: "top" });
    announce(`Resultado: ${percent(tally.ok, tally.total)} por cento.`);
    return;
  }
  if (action === "review") {
    state.session.index = firstProblem();
    state.view = "exam";
    save();
    render({ scroll: "top" });
    return;
  }
  if (action === "retry") {
    startSession(state.session.themeId);
  }
}

function onKey(event) {
  if (event.key === "Escape") {
    closePop();
    return;
  }
  if (document.querySelector(".modal-back") || state.view !== "exam" || !state.session) return;
  if (event.target.closest(".term")) return;
  if (event.key === "ArrowRight" && state.session.index < state.session.questionIds.length - 1) {
    event.preventDefault();
    go(state.session.index + 1);
  } else if (event.key === "ArrowLeft" && state.session.index > 0) {
    event.preventDefault();
    go(state.session.index - 1);
  } else if (/^[1-5]$/.test(event.key) && !event.altKey && !event.ctrlKey && !event.metaKey) {
    const question = currentQuestion();
    if (state.session.finishedAt || Object.prototype.hasOwnProperty.call(state.session.answers, question.id)) return;
    const optionId = state.session.optionOrder[question.id][Number(event.key) - 1];
    if (!optionId) return;
    state.session.answers[question.id] = optionId;
    save();
    render({ scroll: "feedback" });
    announce(optionId === question.correct ? "Resposta certa." : "Resposta errada.");
  }
}

async function boot() {
  try {
    const response = await fetch("data/questions.json");
    if (!response.ok) throw new Error(String(response.status));
    state.bank = await response.json();
  } catch (error) {
    renderFetchError();
    return;
  }
  restore();
  render();
  setInterval(tick, 250);
}

document.addEventListener("click", onClick);
document.addEventListener("keydown", onKey);
boot();
