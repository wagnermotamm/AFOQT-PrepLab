const STORE = "afoqt-banco-original-v1";
const BANK_VERSION = 3;
const LETTERS = "ABCDE";

const NAMES = {
  "verbal-analogies": "Analogias verbais",
  "arithmetic-reasoning": "Raciocínio aritmético",
  "word-knowledge": "Conhecimento de palavras",
  "math-knowledge": "Conhecimento de matemática",
  "reading-comprehension": "Compreensão de leitura",
  "situational-judgment": "Julgamento situacional",
  "self-description": "Inventário de autodescrição",
  "physical-science": "Ciência física",
  "table-reading": "Leitura de tabela",
  "instrument-comprehension": "Compreensão de instrumentos",
  "block-counting": "Contagem de blocos",
  "aviation-information": "Informação de aviação"
};

const TIPS = {
  "verbal-analogies": "O segundo par tem de repetir a mesma relação do primeiro: oposição, equivalência, parte, função, grau ou sequência.",
  "arithmetic-reasoning": "Escreva a relação que falta: distância, tempo, parte, média ou volume. Desconfie de soma no lugar de multiplicação.",
  "word-knowledge": "Procure o equivalente mais próximo. Uma palavra da mesma área, mas com outro sentido, é armadilha.",
  "math-knowledge": "Substitua os valores na expressão ou expanda a fatoração. A alternativa certa precisa fechar a conta inteira.",
  "reading-comprehension": "A resposta deste lote está dita na passagem. Não complete com o que seria razoável, mas não foi escrito.",
  "situational-judgment": "A rubrica de treino prefere segurança, integridade, respeito e clareza. Não é o gabarito oficial do exame.",
  "self-description": "Não há resposta certa. O item só mostra o formato de concordância.",
  "physical-science": "Confira a unidade pedida e a operação: produto, quociente ou os dois passos da fórmula.",
  "table-reading": "X escolhe a coluna, de cima. Y escolhe a linha, à esquerda. Não some X com Y.",
  "instrument-comprehension": "Leia um dado de cada vez: subida ou descida, inclinação e rumo. A frase certa conserva os três.",
  "block-counting": "Conte só o cubo que encosta uma face inteira. Canto e aresta não entram.",
  "aviation-information": "Separe o par de forças e, na conta de balanceamento, divida o momento total pelo peso total."
};

const state = {
  questions: [],
  byId: new Map(),
  bySubtest: new Map(),
  blueprints: null,
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

function shuffle(list) {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function shuffledIndexes(length) {
  const original = [...Array(length).keys()];
  let order = shuffle(original);
  let guard = 0;
  while (order.every((value, index) => value === index) && guard < 8) {
    order = shuffle(original);
    guard += 1;
  }
  return order;
}

function word(n, one, many) {
  return `${n} ${n === 1 ? one : many}`;
}

function formatClock(ms) {
  const total = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h) return [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
  return [m, s].map((n) => String(n).padStart(2, "0")).join(":");
}

function formatWritten(ms) {
  const total = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h) return `${h} h ${m} min ${String(s).padStart(2, "0")} s`;
  if (m) return `${m} min ${String(s).padStart(2, "0")} s`;
  return `${s} s`;
}

function percent(ok, total) {
  if (!total) return 0;
  return Math.round((ok / total) * 100);
}

function question(id) {
  return state.byId.get(id);
}

function flatSlots() {
  const slots = [];
  state.session.sections.forEach((section, sectionIndex) => {
    if (section.kind === "break") {
      slots.push({ kind: "break", sectionIndex });
      return;
    }
    section.questionIds.forEach((id, index) => {
      slots.push({ kind: "question", id, sectionIndex, index });
    });
  });
  return slots;
}

function currentSection() {
  return state.session.sections[state.session.sectionIndex];
}

function currentSlot() {
  const section = currentSection();
  if (section.kind === "break") return { kind: "break", sectionIndex: state.session.sectionIndex };
  return {
    kind: "question",
    id: section.questionIds[state.session.index],
    sectionIndex: state.session.sectionIndex,
    index: state.session.index
  };
}

function isScored(id) {
  return Boolean(question(id).scored);
}

function chosenOption(id) {
  const stored = state.session.answers[id];
  if (stored === undefined) return null;
  return question(id).options[stored];
}

function isCorrect(id) {
  const option = chosenOption(id);
  return Boolean(option && option.correct);
}

function statusOf(id) {
  if (!Object.prototype.hasOwnProperty.call(state.session.answers, id)) return "blank";
  if (!isScored(id)) return "marked";
  return isCorrect(id) ? "ok" : "bad";
}

function counts() {
  const tally = { ok: 0, bad: 0, blank: 0, marked: 0, scored: 0 };
  state.session.sections.forEach((section) => {
    (section.questionIds || []).forEach((id) => {
      const status = statusOf(id);
      tally[status] += 1;
      if (isScored(id)) {
        tally.scored += 1;
        if (status === "blank") tally.blank += 0;
      }
    });
  });
  tally.blank = 0;
  tally.marked = 0;
  tally.ok = 0;
  tally.bad = 0;
  state.session.sections.forEach((section) => {
    (section.questionIds || []).forEach((id) => {
      const status = statusOf(id);
      if (status === "ok") tally.ok += 1;
      else if (status === "bad") tally.bad += 1;
      else if (status === "marked") tally.marked += 1;
      else tally.blank += 1;
    });
  });
  return tally;
}

function scoredSoFar() {
  let ok = 0;
  let total = 0;
  state.session.sections.forEach((section) => {
    (section.questionIds || []).forEach((id) => {
      if (!isScored(id) || statusOf(id) === "blank") return;
      total += 1;
      if (statusOf(id) === "ok") ok += 1;
    });
  });
  return { ok, total };
}

function sectionStats(section) {
  const tally = { ok: 0, bad: 0, blank: 0, marked: 0, scored: 0 };
  (section.questionIds || []).forEach((id) => {
    const status = statusOf(id);
    tally[status] += 1;
    if (isScored(id)) tally.scored += 1;
  });
  return tally;
}

function remainingMs(section) {
  if (!section || !section.endsAt) return section ? section.minutes * 60 * 1000 : 0;
  return section.endsAt - Date.now();
}

function startClock(section) {
  if (!section || section.startedAt) return;
  section.startedAt = Date.now();
  section.endsAt = section.startedAt + section.minutes * 60 * 1000;
}

function usedIds(exceptIndex) {
  const used = new Set();
  state.session.sections.forEach((section, index) => {
    if (index === exceptIndex) return;
    (section.questionIds || []).forEach((id) => used.add(id));
  });
  return used;
}

function pickQuestions(subtest, count, used, prefer) {
  const pool = (state.bySubtest.get(subtest) || []).filter((item) => !used.has(item.id));
  const order = prefer === "hard"
    ? ["advanced", "intermediate", "basic"]
    : prefer === "easy"
      ? ["basic", "intermediate", "advanced"]
      : null;
  if (!order) return shuffle(pool).slice(0, count);
  const chosen = [];
  order.forEach((level) => {
    shuffle(pool.filter((item) => item.difficulty === level && !chosen.includes(item))).forEach((item) => {
      if (chosen.length < count) chosen.push(item);
    });
  });
  return chosen;
}

function assignSection(section, prefer) {
  const picked = pickQuestions(section.subtest, section.requested, usedIds(-1), prefer);
  section.questionIds = picked.map((item) => item.id);
  section.shortfall = Math.max(0, section.requested - picked.length);
  picked.forEach((item) => {
    state.session.optionOrder[item.id] = shuffledIndexes(item.options.length);
  });
}

function upgradeUpcoming() {
  if (!state.session || !state.session.cyber || state.session.upgraded) return;
  const progress = scoredSoFar();
  if (progress.total < 8 || progress.ok / progress.total <= 0.8) return;
  state.session.sections.forEach((section, index) => {
    if (section.kind === "break" || section.startedAt || index === state.session.sectionIndex) return;
    const picked = pickQuestions(section.subtest, section.requested, usedIds(index), "hard");
    section.questionIds = picked.map((item) => item.id);
    section.shortfall = Math.max(0, section.requested - picked.length);
    section.upgraded = true;
    picked.forEach((item) => {
      state.session.optionOrder[item.id] = shuffledIndexes(item.options.length);
    });
  });
  state.session.upgraded = true;
}

function makeSection(spec, cyber) {
  const [subtest, count, minutes] = spec;
  if (subtest === "break") {
    return {
      kind: "break",
      name: "Intervalo",
      minutes,
      requested: 0,
      questionIds: [],
      shortfall: 0,
      startedAt: null,
      endsAt: null,
      locked: false
    };
  }
  const section = {
    kind: subtest === "self-description" ? "sdi" : "test",
    subtest,
    name: NAMES[subtest] || subtest,
    minutes,
    requested: count,
    questionIds: [],
    shortfall: 0,
    startedAt: null,
    endsAt: null,
    locked: false,
    upgraded: false
  };
  return section;
}

function startSession(blueprintKey) {
  const blueprint = state.blueprints[blueprintKey];
  state.session = {
    bankVersion: BANK_VERSION,
    blueprint: blueprintKey,
    name: blueprint.name,
    description: blueprint.description,
    cyber: blueprintKey === "cyber-track",
    upgraded: false,
    sections: blueprint.sections.map((spec) => makeSection(spec)),
    sectionIndex: 0,
    index: 0,
    answers: {},
    optionOrder: {},
    hints: {},
    startedAt: Date.now(),
    finishedAt: null
  };
  const prefer = state.session.cyber ? "easy" : "mixed";
  state.session.sections.forEach((section) => {
    if (section.kind !== "break") assignSection(section, prefer);
  });
  startClock(state.session.sections[0]);
  state.view = "exam";
  save();
  render({ scroll: "top" });
  announce(`Seção iniciada: ${currentSection().name}.`);
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
    if (
      !data.session
      || data.session.bankVersion !== BANK_VERSION
      || !state.blueprints[data.session.blueprint]
    ) return;
    const ids = [];
    data.session.sections.forEach((section) => (section.questionIds || []).forEach((id) => ids.push(id)));
    if (!ids.every((id) => state.byId.has(id))) return;
    state.session = data.session;
    state.view = data.view === "results" || data.view === "exam" ? data.view : "home";
    if (state.session.finishedAt && state.view === "exam") state.view = "results";
  } catch (error) {
    localStorage.removeItem(STORE);
  }
}

function go(sectionIndex, index) {
  const section = state.session.sections[sectionIndex];
  if (!section) return;
  state.session.sectionIndex = sectionIndex;
  state.session.index = section.kind === "break" ? 0 : Math.max(0, Math.min(index || 0, section.questionIds.length - 1));
  startClock(section);
  save();
  render({ scroll: "top" });
}

function step(delta) {
  const slots = flatSlots();
  const current = currentSlot();
  const at = slots.findIndex((slot) => {
    if (slot.kind !== current.kind || slot.sectionIndex !== current.sectionIndex) return false;
    if (slot.kind === "break") return true;
    return slot.index === current.index;
  });
  const next = slots[at + delta];
  if (!next) return;
  go(next.sectionIndex, next.index || 0);
}

function finish() {
  state.session.finishedAt = Date.now();
  state.view = "results";
  save();
  const tally = counts();
  render({ scroll: "top" });
  announce(`Treino encerrado. ${percent(tally.ok, tally.ok + tally.bad)} por cento das respondidas e pontuáveis.`);
}

function expireSection(section) {
  if (!section || section.locked || !section.endsAt || Date.now() < section.endsAt) return false;
  section.locked = true;
  return true;
}

function tick() {
  const timer = document.getElementById("timer");
  if (!state.session || state.view === "home") return;
  if (state.session.finishedAt) {
    if (timer) timer.textContent = formatClock(Date.now() - state.session.startedAt);
    return;
  }
  const section = currentSection();
  const justLocked = expireSection(section);
  if (timer) {
    const label = section.locked ? "00:00" : formatClock(remainingMs(section));
    timer.textContent = label;
  }
  if (justLocked && state.view === "exam") {
    const nextIndex = state.session.sectionIndex + 1;
    if (nextIndex < state.session.sections.length) {
      go(nextIndex, 0);
      announce("O tempo da seção acabou. A próxima seção começou.");
    } else {
      finish();
    }
  }
}

function safeFigure(figure) {
  const source = String(figure || "");
  if (!source.startsWith("<svg") || /<script/i.test(source)) return "";
  return source;
}

function headerHtml() {
  const running = state.session && state.view !== "home";
  const tally = running ? counts() : null;
  const section = running ? currentSection() : null;
  const meta = running
    ? `${state.session.name} · ${section.name}`
    : "Treino original. Não é endossado pela USAF.";
  const chips = tally ? `
    <div class="scorechips">
      <span class="chip ok">${word(tally.ok, "certa", "certas")}</span>
      <span class="chip bad">${word(tally.bad, "errada", "erradas")}</span>
      <span class="chip wait">${word(tally.blank, "em branco", "em branco")}</span>
    </div>` : "";
  const clock = running && !state.session.finishedAt
    ? `<div class="clock" id="timer">${section.locked ? "00:00" : formatClock(remainingMs(section))}</div>`
    : running
      ? `<div class="clock" id="timer">${formatClock(Date.now() - state.session.startedAt)}</div>`
      : "";
  let action = "";
  if (state.view === "exam" && state.session && !state.session.finishedAt) {
    action = `<button type="button" class="ghost" data-action="finish">Encerrar</button>`;
  } else if (state.view !== "home") {
    action = `<button type="button" class="ghost" data-action="home">Início</button>`;
  }
  return `
    <header class="top">
      <div class="brand">
        <strong>AFOQT · BANCO ORIGINAL</strong>
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
  const groups = state.session.sections.map((section, sectionIndex) => {
    if (section.kind === "break") {
      const current = state.session.sectionIndex === sectionIndex ? " is-current" : "";
      return `
        <div class="qgroup">
          <p>Intervalo</p>
          <div class="qgrid">
            <button type="button" class="qbtn${current}" data-action="goto" data-section="${sectionIndex}" data-index="0"><b>P</b><small>pausa</small></button>
          </div>
        </div>`;
    }
    const buttons = section.questionIds.map((id, index) => {
      const status = state.session.finishedAt || statusOf(id) !== "blank" || section.locked
        ? statusOf(id)
        : "open";
      const cls = [
        "qbtn",
        status === "ok" ? "is-ok" : "",
        status === "bad" ? "is-bad" : "",
        status === "marked" ? "is-blank-done" : "",
        state.session.finishedAt && status === "blank" ? "is-blank-done" : "",
        state.session.sectionIndex === sectionIndex && state.session.index === index ? "is-current" : ""
      ].filter(Boolean).join(" ");
      const mark = status === "ok" ? "✓" : status === "bad" ? "✕" : status === "marked" ? "•" : "–";
      return `<button type="button" class="${cls}" data-action="goto" data-section="${sectionIndex}" data-index="${index}"><b>${index + 1}</b><small>${mark}</small></button>`;
    }).join("");
    return `<div class="qgroup"><p>${esc(section.name)}</p><div class="qgrid">${buttons}</div></div>`;
  }).join("");
  return `
    <aside class="qnav">
      <h2>Perguntas</h2>
      <p class="legend"><i>✓</i> certa <i>✕</i> errada <i>–</i> em branco <i>•</i> sem nota</p>
      <div class="qnav-scroll">${groups}</div>
    </aside>`;
}

function optionHtml(item, position, originalIndex) {
  const option = item.options[originalIndex];
  const stored = state.session.answers[item.id];
  const revealed = state.session.finishedAt || stored !== undefined;
  const chosen = stored === originalIndex;
  let cls = "option";
  let flag = "";
  if (revealed && item.scored && option.correct) {
    cls += " good";
    flag = "correta";
  } else if (revealed && item.scored && chosen) {
    cls += " bad";
    flag = "sua escolha";
  } else if (revealed && !item.scored && chosen) {
    cls += " good";
    flag = "marcada";
  }
  const lockedChoice = revealed || currentSection().locked;
  return `
    <div role="button" tabindex="0" class="${cls}" data-action="answer" data-option="${originalIndex}" ${lockedChoice ? "aria-disabled=\"true\"" : ""}>
      <span class="badge">${LETTERS[position]}</span>
      <span>${decorate(option.text, item.glossary)}</span>
      <span class="flag">${flag}</span>
    </div>`;
}

function feedbackHtml(item) {
  const stored = state.session.answers[item.id];
  if (stored === undefined && !state.session.finishedAt) return "";
  if (!item.scored) {
    return `<div class="feedback"><strong>Resposta registrada.</strong><p>Este inventário não entra na nota e não tem alternativa correta.</p></div>`;
  }
  if (stored === undefined) {
    return `<div class="feedback"><strong>Em branco.</strong><p>${esc(item.explanation)}</p></div>`;
  }
  const option = item.options[stored];
  const good = option.correct;
  const rubric = item.status === "training_rubric"
    ? "<p>Rubrica de treino. Esta escolha não é um gabarito oficial do exame.</p>"
    : "";
  if (good) {
    return `<div class="feedback good"><strong>Certa.</strong>${rubric}<p>${esc(item.explanation)}</p><p>${esc(item.whyCorrect)}</p></div>`;
  }
  return `<div class="feedback bad"><strong>Errada.</strong>${rubric}<p>${esc(option.whyWrong || "")}</p><p>${esc(item.explanation)}</p></div>`;
}

function examHtml() {
  const section = currentSection();
  if (section.kind === "break") {
    const left = section.locked ? "00:00" : formatClock(remainingMs(section));
    return `
      ${headerHtml()}
      <div class="layout">
        ${navHtml()}
        <article class="sheet">
          <p class="kicker">Intervalo publicado</p>
          <h2>15 minutos</h2>
          <p>Na administração descrita pela Pearson VUE há um intervalo depois do julgamento situacional. No treino ele pode ser pulado.</p>
          <p class="section-note">Tempo restante nesta tela: ${left}.</p>
          <div class="row-actions">
            <button type="button" class="primary" data-action="skip-break">Pular intervalo</button>
          </div>
        </article>
      </div>`;
  }
  const item = question(section.questionIds[state.session.index]);
  const order = state.session.optionOrder[item.id];
  const figure = safeFigure(item.figure);
  const shortfall = section.shortfall
    ? `<p class="banner">O formato publicado pede ${section.requested} itens. Este banco tem ${section.questionIds.length} originais neste subteste, sem repetir questão.</p>`
    : "";
  const hard = section.upgraded
    ? `<p class="banner">A trilha subiu a dificuldade desta seção porque o acerto anterior passou de 80%.</p>`
    : "";
  const tip = state.session.hints[item.id]
    ? `<div class="hint"><p class="hint-k">Dica</p><p>${esc(TIPS[item.subtest] || "")}</p></div>`
    : `<button type="button" class="hint-btn" data-action="hint">Ver dica</button>`;
  const locked = section.locked ? `<p class="banner">O tempo desta seção acabou. Dá para reler, e a resposta já marcada permanece.</p>` : "";
  return `
    ${headerHtml()}
    <div class="layout">
      ${navHtml()}
      <article class="sheet">
        <div class="sheet-top">
          <p>${esc(section.name)} · ${state.session.index + 1} de ${section.questionIds.length}</p>
          <p>${esc(item.difficulty)} · ${esc(item.topic)}</p>
        </div>
        ${shortfall}
        ${hard}
        ${locked}
        <h2 class="stem ${item.stem.length > 420 ? "long" : ""}">${decorate(item.stem, item.glossary)}</h2>
        ${figure ? `<div class="figure">${figure}</div>` : ""}
        <p class="dict-note">Palavra sublinhada abre o sentido em português e não escolhe a alternativa.</p>
        ${tip}
        <div class="options">
          ${order.map((originalIndex, position) => optionHtml(item, position, originalIndex)).join("")}
        </div>
        <div id="feedback">${feedbackHtml(item)}</div>
        <div class="pager">
          <button type="button" class="quiet" data-action="prev">Anterior</button>
          <button type="button" class="quiet" data-action="next">Próxima</button>
        </div>
        <p class="foot">Fonte conceitual: ${esc(item.concept)}. <a href="${esc(item.sourceUrl)}" target="_blank" rel="noreferrer">Abrir a referência</a></p>
      </article>
    </div>`;
}

function indexOfGroup(ids) {
  let ok = 0;
  let total = 0;
  state.session.sections.forEach((section) => {
    if (!ids.includes(section.subtest)) return;
    const tally = sectionStats(section);
    ok += tally.ok;
    total += tally.scored;
  });
  return { ok, total, percent: percent(ok, total) };
}

function resultsHtml() {
  const tally = counts();
  const answered = tally.ok + tally.bad;
  const score = percent(tally.ok, tally.scored);
  const verbal = indexOfGroup(["verbal-analogies", "word-knowledge", "reading-comprehension"]);
  const quantitative = indexOfGroup(["arithmetic-reasoning", "math-knowledge"]);
  const rows = state.session.sections.filter((section) => section.kind !== "break").map((section) => {
    const stats = sectionStats(section);
    if (section.kind === "sdi") {
      return `<div class="bar-row"><span>${esc(section.name)}</span><div class="track"><span style="width:0"></span></div><span class="bar-meta">sem nota · ${stats.marked} marcadas</span></div>`;
    }
    const value = percent(stats.ok, stats.scored);
    return `<div class="bar-row"><span>${esc(section.name)}</span><div class="track"><span style="width:${value}%"></span></div><span class="bar-meta">${stats.ok}/${stats.scored} · ${value}%</span></div>`;
  }).join("");
  const cyberNote = state.session.cyber
    ? `<p>Esta trilha não substitui o Cyber Knowledge Test. O DAFMAN trata esse exame à parte. ${state.session.upgraded ? "A dificuldade das seções ainda não iniciadas foi elevada depois de mais de 80% de acerto." : "A dificuldade ficaria mais alta se o acerto passasse de 80% com pelo menos 8 respostas pontuáveis."}</p>`
    : "";
  return `
    ${headerHtml()}
    <main class="home">
      <section class="hero">
        <p class="kicker">Resultado de treino</p>
        <div class="score-wrap">
          <p class="score-num">${score}<small>%</small></p>
          <p class="score-copy">${word(tally.ok, "acerto", "acertos")} em ${word(tally.scored, "item pontuável", "itens pontuáveis")}. ${word(tally.blank, "ficou em branco", "ficaram em branco")}. Tempo total: ${formatWritten(state.session.finishedAt - state.session.startedAt)}. ${answered} respostas pontuáveis foram dadas.</p>
        </div>
        <p>Índice verbal de treino, analogias + palavras + leitura: ${verbal.ok}/${verbal.total} (${verbal.percent}%). Índice quantitativo de treino, aritmética + matemática: ${quantitative.ok}/${quantitative.total} (${quantitative.percent}%). Estes percentuais não são percentis oficiais do AFOQT.</p>
        ${cyberNote}
        <div class="bars">${rows}</div>
        <div class="row-actions">
          <button type="button" class="primary" data-action="review">Rever questões</button>
          <button type="button" class="quiet" data-action="retry">Nova tentativa</button>
          <button type="button" class="quiet" data-action="home">Início</button>
        </div>
      </section>
    </main>`;
}

function homeHtml() {
  const order = ["full", "verbal", "quantitative", "aviation", "science", "spatial", "judgment", "cyber-track"];
  const cards = order.map((key) => {
    const blueprint = state.blueprints[key];
    const minutes = blueprint.sections.reduce((sum, spec) => sum + spec[2], 0);
    const steps = blueprint.sections.length;
    return `
      <article class="card">
        <h2>${esc(blueprint.name)}</h2>
        <p>${esc(blueprint.description)}</p>
        <p>${steps === 1 ? "1 etapa" : `${steps} etapas`} · ${minutes} min no cronômetro publicado</p>
        <button type="button" class="mini" data-action="start" data-blueprint="${esc(key)}">Começar</button>
      </article>`;
  }).join("");
  let resume = "";
  if (state.session && !state.session.finishedAt) {
    resume = `
      <div class="resume">
        <div><strong>Há um treino em andamento.</strong><br>${esc(state.session.name)}</div>
        <div class="row-actions">
          <button type="button" class="primary" data-action="resume">Continuar</button>
          <button type="button" class="quiet" data-action="discard">Descartar</button>
        </div>
      </div>`;
  }
  const scored = state.questions.filter((item) => item.scored).length;
  return `
    ${headerHtml()}
    <main class="home">
      <section class="hero">
        <p class="kicker">Estrutura Pearson VUE · agosto de 2026</p>
        <h1>Banco original de treino</h1>
        <p class="lede">${scored} questões pontuáveis e originais, mais um inventário sem nota. O enunciado fica em inglês. A explicação fica em português. O resultado é percentual de treino, não percentil oficial.</p>
        <p class="lede"><a href="index.html">Voltar ao panfleto antigo</a>. As questões daquele arquivo não entram neste banco.</p>
        ${resume}
      </section>
      <div class="cards">${cards}</div>
      <p class="foot">O julgamento situacional usa uma rubrica local. O inventário de autodescrição não corrige personalidade. A página da prova pede 16 itens de julgamento e 240 de autodescrição; este banco traz 8 cenários originais e 16 itens de familiarização.</p>
    </main>`;
}

function render(options) {
  closePop();
  const root = app();
  if (state.view === "exam" && state.session) root.innerHTML = examHtml();
  else if (state.view === "results" && state.session) root.innerHTML = resultsHtml();
  else root.innerHTML = homeHtml();
  if (options && options.scroll === "feedback") {
    const node = document.getElementById("feedback");
    if (node) node.scrollIntoView({ block: "nearest" });
  } else if (options && options.scroll === "top") {
    window.scrollTo(0, 0);
  }
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

function ask(title, message, confirmLabel, cancelLabel) {
  return new Promise((resolve) => {
    const root = document.createElement("div");
    root.className = "modal-back";
    root.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true">
        <h2>${esc(title)}</h2>
        <p>${esc(message)}</p>
        <div class="row-actions">
          <button type="button" class="quiet" data-cancel>${esc(cancelLabel)}</button>
          <button type="button" class="primary" data-ok>${esc(confirmLabel)}</button>
        </div>
      </div>`;
    root.addEventListener("click", (event) => {
      if (event.target === root || event.target.closest("[data-cancel]")) {
        root.remove();
        resolve(false);
      } else if (event.target.closest("[data-ok]")) {
        root.remove();
        resolve(true);
      }
    });
    document.body.appendChild(root);
    root.querySelector("[data-ok]").focus();
  });
}

async function onClick(event) {
  const term = event.target.closest(".term");
  if (term) {
    event.preventDefault();
    event.stopPropagation();
    openPop(term);
    return;
  }
  if (event.target.closest("#pop")) return;
  closePop();
  const el = event.target.closest("[data-action]");
  if (!el || el.disabled || el.getAttribute("aria-disabled") === "true") return;
  const action = el.dataset.action;
  if (action === "start") {
    if (state.session && !state.session.finishedAt) {
      const replace = await ask(
        "Começar outro treino?",
        "Há uma tentativa em andamento. A nova embaralha as alternativas e zera o cronômetro.",
        "Começar de novo",
        "Continuar a atual"
      );
      if (!replace) {
        state.view = "exam";
        save();
        render({ scroll: "top" });
        return;
      }
    }
    startSession(el.dataset.blueprint);
    return;
  }
  if (action === "resume") {
    state.view = "exam";
    startClock(currentSection());
    save();
    render({ scroll: "top" });
    return;
  }
  if (action === "discard") {
    const ok = await ask("Descartar o treino?", "O tempo e as respostas desta tentativa serão apagados.", "Descartar", "Cancelar");
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
  if (action === "goto") {
    go(Number(el.dataset.section), Number(el.dataset.index));
    return;
  }
  if (action === "prev") {
    step(-1);
    return;
  }
  if (action === "next") {
    step(1);
    return;
  }
  if (action === "skip-break") {
    currentSection().locked = true;
    const nextIndex = state.session.sectionIndex + 1;
    if (nextIndex < state.session.sections.length) go(nextIndex, 0);
    else finish();
    return;
  }
  if (action === "hint") {
    const section = currentSection();
    const item = question(section.questionIds[state.session.index]);
    state.session.hints[item.id] = true;
    save();
    render();
    return;
  }
  if (action === "answer") {
    const section = currentSection();
    if (section.locked || state.session.finishedAt) return;
    const item = question(section.questionIds[state.session.index]);
    if (Object.prototype.hasOwnProperty.call(state.session.answers, item.id)) return;
    state.session.answers[item.id] = Number(el.dataset.option);
    upgradeUpcoming();
    save();
    render({ scroll: "feedback" });
    if (!item.scored) announce("Resposta registrada. Este item não entra na nota.");
    else announce(isCorrect(item.id) ? "Resposta certa." : "Resposta errada.");
    return;
  }
  if (action === "finish") {
    const tally = counts();
    if (tally.blank > 0) {
      const ok = await ask(
        "Encerrar agora?",
        `Ainda há ${word(tally.blank, "item em branco", "itens em branco")}. Eles não somam ponto.`,
        "Ver resultado",
        "Voltar ao treino"
      );
      if (!ok) return;
    }
    finish();
    return;
  }
  if (action === "review") {
    state.view = "exam";
    state.session.sectionIndex = 0;
    state.session.index = 0;
    save();
    render({ scroll: "top" });
    return;
  }
  if (action === "retry") {
    startSession(state.session.blueprint);
  }
}

function onKey(event) {
  if (event.key === "Escape") {
    closePop();
    return;
  }
  if (document.querySelector(".modal-back") || state.view !== "exam" || !state.session) return;
  if (event.target.closest("input, textarea")) return;
  if (event.key === "ArrowRight") {
    event.preventDefault();
    step(1);
  } else if (event.key === "ArrowLeft") {
    event.preventDefault();
    step(-1);
  }
}

function renderFetchError() {
  app().innerHTML = `
    <main class="error">
      <h1>O banco não abriu</h1>
      <p>Inicie o servidor na pasta do simulador. O arquivo <code>banco/export/questions.json</code> não carrega por <code>file://</code>.</p>
      <p>No Windows, dê um duplo clique em <code>iniciar.bat</code>.</p>
    </main>`;
}

async function boot() {
  try {
    const [questionsResponse, blueprintResponse] = await Promise.all([
      fetch(`banco/export/questions.json?v=${BANK_VERSION}`),
      fetch(`banco/export/blueprints.json?v=${BANK_VERSION}`)
    ]);
    if (!questionsResponse.ok || !blueprintResponse.ok) throw new Error("http");
    state.questions = await questionsResponse.json();
    state.blueprints = await blueprintResponse.json();
  } catch (error) {
    renderFetchError();
    return;
  }
  state.questions.forEach((item) => {
    state.byId.set(item.id, item);
    if (!state.bySubtest.has(item.subtest)) state.bySubtest.set(item.subtest, []);
    state.bySubtest.get(item.subtest).push(item);
  });
  restore();
  render();
  setInterval(tick, 250);
}

document.addEventListener("click", onClick);
document.addEventListener("keydown", onKey);
boot();
