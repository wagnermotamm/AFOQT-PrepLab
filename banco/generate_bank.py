# -*- coding: utf-8 -*-
"""Gera um banco original de treino do AFOQT e valida cada item antes de gravar.

As questões são autorais. Não reproduzem o panfleto oficial nem simulados comerciais.
Os gabaritos de cálculo são refeitos por uma segunda conta. Julgamento situacional
usa uma rubrica de treino e não é apresentado como gabarito da USAF.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "afoqt.sqlite"
EXPORT = ROOT / "export"
REPORTS = ROOT.parent / "relatorios"
ACCESSED = "2026-10-13"

SOURCES = [
    {
        "source_key": "pearson-vue-afoqt",
        "institution": "Pearson VUE / U.S. Air Force",
        "title": "Air Force Officer Qualifying Test (AFOQT)",
        "url": "https://www.pearsonvue.com/us/en/afoqt.html",
        "published": "",
        "updated": "2026-08-06",
        "accessed": ACCESSED,
        "doc_type": "página oficial de administração",
        "license_notes": "Página comercial/institucional. Usada só para estrutura, tempos e regras publicadas. Nenhum item de prova foi copiado.",
        "relevant": "12 subtestes, 516 respostas, tempos, intervalo, áreas de resultado e regra de que a nota oficial é percentil.",
        "verification": "Página lida em 2026-10-13. O rodapé informa Last updated 2026-08-06.",
        "role": "oficial",
    },
    {
        "source_key": "dafman-36-2664",
        "institution": "Department of the Air Force",
        "title": "DAFMAN 36-2664, Personnel Assessment Program",
        "url": "https://static.e-publishing.af.mil/production/1/af_a1/publication/dafman36-2664/dafman36-2664.pdf",
        "published": "2025-01-17",
        "updated": "2025-07-15",
        "accessed": ACCESSED,
        "doc_type": "manual oficial",
        "license_notes": "Publicação do governo dos EUA, sem restrição de releasability declarada no próprio manual. Não contém o banco de itens operacionais.",
        "relevant": "Doze subtestes, cinco compostos de aptidão, percentis 1–99, mínimos da Tabela A2.1, intervalo de nova tentativa e separação entre treino amplo e o teste controlado.",
        "verification": "PDF oficial lido. Capa: 17 January 2025, Incorporating Change 1, 15 July 2025, Certified Current 15 July 2025.",
        "role": "oficial",
    },
    {
        "source_key": "afrotc-rutgers",
        "institution": "Air Force ROTC Detachment 485, Rutgers",
        "title": "Página institucional AFOQT",
        "url": "https://afrotc.rutgers.edu/afoqt",
        "published": "",
        "updated": "2025-11",
        "accessed": ACCESSED,
        "doc_type": "página educacional de destacamento",
        "license_notes": "Página de um destacamento. Usada como confirmação da estrutura já publicada pela Pearson e dos mínimos do DAFMAN. Itens de prova não são reproduzidos.",
        "relevant": "Repete a estrutura de 516 itens e explica que o composto quantitativo usa Arithmetic Reasoning e Math Knowledge. Aponta o material aprovado no sítio do PCSM.",
        "verification": "Página lida em 2026-10-13. O texto diz Current as of November 2025.",
        "role": "oficial-educacional",
    },
    {
        "source_key": "pcsmdmz-form-t",
        "institution": "Air Force Personnel Center",
        "title": "Form T — material de preparação indicado pelo destacamento",
        "url": "https://access.afpc.af.mil/pcsmdmz/Form%20T.HTML",
        "published": "",
        "updated": "",
        "accessed": ACCESSED,
        "doc_type": "ponteiro oficial de estudo",
        "license_notes": "Endereço publicado pelo destacamento AFROTC como material aprovado. Este banco não extrai nem redistribui esse material.",
        "relevant": "Indica onde a própria Força publica a preparação autorizada. Não foi minerado para gerar questões.",
        "verification": "URL citada na página do destacamento lida em 2026-10-13. O conteúdo protegido não foi copiado.",
        "role": "oficial",
    },
    {
        "source_key": "afpt-997-2015",
        "institution": "U.S. Air Force / AFROTC",
        "title": "AFOQT Information Pamphlet, AFPT 997, Form T",
        "url": "https://afrotc.rutgers.edu/sites/default/files/pdf/afpt-997_afoqt-practice-pamphlet_cao01aug15.pdf",
        "published": "2015-08-01",
        "updated": "2015-08-01",
        "accessed": ACCESSED,
        "doc_type": "panfleto histórico de familiarização",
        "license_notes": "Documento governamental antigo. Serve para ver o formato Form T de 2015. As questões de exemplo não foram copiadas.",
        "relevant": "Introduziu Reading Comprehension, Situational Judgment e o nome Physical Science. Os números de Situational Judgment desse PDF (50) não coincidem com a página Pearson de 2026 (16).",
        "verification": "PDF acessível em 2026-10-13. Tratado como histórico, não como planta da prova atual.",
        "role": "oficial-historico",
    },
    {
        "source_key": "airforce-pamphlet-legacy",
        "institution": "U.S. Air Force",
        "title": "AFOQT Information Pamphlet hospedado em airforce.com",
        "url": "https://www.airforce.com/content/dam/airforce/en/pdf/AFOQT_PracticePamphlet.pdf",
        "published": "",
        "updated": "",
        "accessed": ACCESSED,
        "doc_type": "panfleto desatualizado ainda no ar",
        "license_notes": "Documento governamental. A cópia pública ainda descreve General Science, Rotated Blocks, Hidden Figures e inventário de 220 itens.",
        "relevant": "Não descreve a prova administrada em 2026. Mantido no catálogo para não confundir com a estrutura Pearson.",
        "verification": "PDF lido em 2026-10-13. A tabela de subtestes é a anterior à Form T vigente.",
        "role": "oficial-desatualizado",
    },
    {
        "source_key": "faa-phak",
        "institution": "Federal Aviation Administration",
        "title": "Pilot's Handbook of Aeronautical Knowledge, FAA-H-8083-25C",
        "url": "https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/phak",
        "published": "",
        "updated": "",
        "accessed": ACCESSED,
        "doc_type": "manual técnico governamental",
        "license_notes": "Obra do governo dos EUA. Usada como mapa de assuntos. Nenhum exercício ou parágrafo foi copiado.",
        "relevant": "Construção, princípios de voo, aerodinâmica, controles, sistemas, instrumentos, peso e balanceamento, desempenho, meteorologia e navegação.",
        "verification": "Página oficial lida em 2026-10-13. A edição listada é FAA-H-8083-25C, com os capítulos 1 a 17.",
        "role": "oficial",
    },
    {
        "source_key": "faa-afh",
        "institution": "Federal Aviation Administration",
        "title": "Airplane Flying Handbook, FAA-H-8083-3C",
        "url": "https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/airplane_handbook",
        "published": "",
        "updated": "",
        "accessed": ACCESSED,
        "doc_type": "manual técnico governamental",
        "license_notes": "Obra do governo dos EUA. Conceitos de manobra e atitude apenas. Texto não copiado.",
        "relevant": "Manobras, energia, recuperação de atitude anormal, pousos e decolagens.",
        "verification": "Página oficial lida em 2026-10-13. A edição listada é FAA-H-8083-3C.",
        "role": "oficial",
    },
    {
        "source_key": "faa-ifh",
        "institution": "Federal Aviation Administration",
        "title": "Instrument Flying Handbook, FAA-H-8083-15B",
        "url": "https://www.faa.gov/regulations_policies/handbooks_manuals/aviation",
        "published": "2012",
        "updated": "2014-10-10",
        "accessed": ACCESSED,
        "doc_type": "manual técnico governamental",
        "license_notes": "A página oficial de manuais lista a edição de 2012, errata de 2014 e adendos. Espelhos comerciais do PDF não foram usados.",
        "relevant": "Instrumentos de atitude, rumo e interpretação do voo por instrumentos.",
        "verification": "Índice oficial de manuais lido em 2026-10-13. Uma revisão nova foi recomendada ao FAA em 2025 e ainda não substitui a edição listada.",
        "role": "oficial",
    },
    {
        "source_key": "afdp-1",
        "institution": "LeMay Center, U.S. Air Force",
        "title": "Air Force Doctrine Publication 1, The Air Force",
        "url": "https://www.doctrine.af.mil/Operational-Level-Doctrine/AFDP-1-The-Air-Force/",
        "published": "2021-03-10",
        "updated": "2021-03-10",
        "accessed": ACCESSED,
        "doc_type": "doutrina",
        "license_notes": "Doutrina pública. Não é gabarito do Situational Judgment Test.",
        "relevant": "Contexto de profissão, missão e forma de empregar a força. Fundo conceitual apenas.",
        "verification": "Página oficial lida em 2026-10-13. Last Published: 10 March 2021.",
        "role": "oficial",
    },
    {
        "source_key": "afdp-1-1",
        "institution": "LeMay Center, U.S. Air Force",
        "title": "Air Force Doctrine Publication 1-1, Mission Command",
        "url": "https://www.doctrine.af.mil/Operational-Level-Doctrine/AFDP-1-1-Mission-Command/",
        "published": "2023-08-14",
        "updated": "2023-08-14",
        "accessed": ACCESSED,
        "doc_type": "doutrina",
        "license_notes": "Doutrina pública. Não define a resposta oficial de nenhum item de julgamento.",
        "relevant": "Intenção, iniciativa disciplinada e responsabilidade. Fundo do treino de julgamento, não chave de correção.",
        "verification": "Página oficial lida em 2026-10-13. Published: 14 August 2023.",
        "role": "oficial",
    },
    {
        "source_key": "openstax-prealgebra",
        "institution": "OpenStax, Rice University",
        "title": "Prealgebra 2e",
        "url": "https://openstax.org/books/prealgebra-2e/pages/preface",
        "published": "",
        "updated": "",
        "accessed": ACCESSED,
        "doc_type": "livro didático aberto",
        "license_notes": "Referência de assuntos. Nenhum exercício do livro foi copiado. A licença do livro restringe o uso da obra em si; as questões numéricas deste banco foram criadas à parte.",
        "relevant": "Aritmética, frações, porcentagem, razão e problemas de taxa.",
        "verification": "Usado como mapa de assuntos. Exercícios do livro não foram lidos para reprodução.",
        "role": "educacional-aberto",
    },
    {
        "source_key": "openstax-intermediate",
        "institution": "OpenStax, Rice University",
        "title": "Intermediate Algebra 2e",
        "url": "https://openstax.org/books/intermediate-algebra-2e/pages/preface",
        "published": "",
        "updated": "",
        "accessed": ACCESSED,
        "doc_type": "livro didático aberto",
        "license_notes": "Mesma regra: assuntos sim, exercícios do livro não.",
        "relevant": "Equações, sistemas e polinômios em nível intermediário.",
        "verification": "Mapa de assuntos. Exercícios não copiados.",
        "role": "educacional-aberto",
    },
    {
        "source_key": "openstax-college",
        "institution": "OpenStax, Rice University",
        "title": "College Algebra 2e",
        "url": "https://openstax.org/books/college-algebra-2e/pages/preface",
        "published": "",
        "updated": "",
        "accessed": ACCESSED,
        "doc_type": "livro didático aberto",
        "license_notes": "O prefácio declara CC BY-NC-SA 4.0. Por isso nenhum texto, figura ou exercício do livro entra no banco. Só a lista pública de capítulos foi usada como mapa.",
        "relevant": "Pré-requisitos, equações, funções, sistemas, geometria analítica e contagem.",
        "verification": "Prefácio lido em 2026-10-13. Licença confirmada no próprio texto.",
        "role": "educacional-aberto",
    },
    {
        "source_key": "openstax-physics",
        "institution": "OpenStax, Rice University",
        "title": "Physics",
        "url": "https://openstax.org/books/physics/pages/1-introduction",
        "published": "",
        "updated": "",
        "accessed": ACCESSED,
        "doc_type": "livro didático aberto",
        "license_notes": "Mapa de assuntos de física do ensino médio. Fórmulas usadas são relações padrão, não problemas do livro.",
        "relevant": "Força, movimento, energia, eletricidade e máquinas simples, alinhado ao que a Pearson descreve em Physical Science.",
        "verification": "URL oficial conferida como endereço do livro. Problemas do livro não foram copiados.",
        "role": "educacional-aberto",
    },
    {
        "source_key": "nasa-aero",
        "institution": "NASA Glenn Research Center",
        "title": "Beginner's Guide to Aeronautics",
        "url": "https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/",
        "published": "",
        "updated": "",
        "accessed": ACCESSED,
        "doc_type": "página educacional governamental",
        "license_notes": "Não foi possível ler a página nesta sessão (tempo esgotado). Nenhuma questão cita um capítulo específico desta obra.",
        "relevant": "Reservada como fonte complementar de forças aerodinâmicas. Não usada para redigir itens.",
        "verification": "Acesso em 2026-10-13 expirou. Status: não verificada nesta sessão.",
        "role": "complementar-nao-verificada",
    },
    {
        "source_key": "original-lexicon",
        "institution": "Banco de treino local",
        "title": "Léxico e relações semânticas autorais",
        "url": "https://dictionary.cambridge.org/dictionary/learner-english/",
        "published": "",
        "updated": "",
        "accessed": ACCESSED,
        "doc_type": "método de referência, sem extração",
        "license_notes": "O Cambridge Learner's Dictionary não foi copiado nem raspado. Os pares de sinônimos e analogias foram redigidos para este banco.",
        "relevant": "Word Knowledge e Verbal Analogies. O URL permanece como dicionário de consulta humana, não como texto-fonte.",
        "verification": "Nenhuma definição do Cambridge foi armazenada.",
        "role": "referencia-nao-extraida",
    },
]


@dataclass
class Item:
    subtest: str
    topic: str
    subtopic: str
    difficulty: str
    stem: str
    options: list
    explanation: str
    why_correct: str
    source_key: str
    concept: str
    seconds: int
    tags: list
    status: str
    check_kind: str = ""
    check_value: str = ""
    figure: str = ""
    glossary: list = field(default_factory=list)
    scored: int = 1


def nfmt(value: float) -> str:
    if abs(value - round(value)) < 1e-8:
        return str(int(round(value)))
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text


def independent_product(left: int, right: int) -> int:
    total = 0
    for _ in range(abs(right)):
        total += abs(left)
    if (left < 0) ^ (right < 0):
        return -total
    return total


def axis_token(token: str) -> int:
    return int(token.replace("−", "-").replace("+", ""))


def recompute_number(stem: str) -> str | None:
    match = re.search(r"steady (\d+(?:\.\d+)?) miles per hour for (\d+(?:\.\d+)?) hours", stem)
    if match and "How many miles does it travel?" in stem:
        return nfmt(float(match.group(1)) * float(match.group(2)))
    match = re.search(
        r"travels (\d+(?:\.\d+)?) miles per hour for (\d+(?:\.\d+)?) hours\. On a map, 1 inch represents (\d+) miles",
        stem,
    )
    if match:
        miles = float(match.group(1)) * float(match.group(2))
        return nfmt(miles / int(match.group(3)))
    match = re.search(r"spent \$(\d+) on two kinds of tickets, priced at \$(\d+) and \$(\d+)", stem)
    if match:
        total, low, high = (int(part) for part in match.groups())
        pair = low + high
        if pair == 0 or total % pair != 0:
            return None
        return str(total // pair)
    match = re.search(r"What is (\d+) percent of (\d+)\?", stem)
    if match:
        percent, base = int(match.group(1)), int(match.group(2))
        if percent == 0 or (base * percent) % 100 != 0:
            return None
        return str(base * percent // 100)
    match = re.search(r"(\d+) feet long, (\d+) feet wide, and (\d+) feet high", stem)
    if match:
        length, width, height = (int(part) for part in match.groups())
        return str(independent_product(independent_product(length, width), height))
    match = re.search(r"cover (\d+) miles at a steady (\d+) miles per hour", stem)
    if match:
        distance, speed = int(match.group(1)), int(match.group(2))
        if speed == 0 or distance % speed != 0:
            return None
        return str(distance // speed)
    match = re.search(r"Three inspection scores are (\d+), (\d+), and (\d+)", stem)
    if match:
        scores = [int(part) for part in match.groups()]
        if sum(scores) % 3 != 0:
            return None
        return str(sum(scores) // 3)
    match = re.search(r"The value of \(−(\d+)/(\d+)\) × √(\d+) is", stem)
    if match:
        numerator, root, shown = (int(part) for part in match.groups())
        if root != shown or root <= 0:
            return None
        value = -numerator / root * (root ** 0.5)
        if abs(value - round(value)) > 1e-8:
            return None
        return str(int(round(value)))
    if stem.startswith("In table T"):
        rows = {}
        for row in re.finditer(r"The row ([+\-−]?\d+) reads: ([0-9, ]+)\.", stem):
            y = axis_token(row.group(1))
            rows[y] = [int(part) for part in row.group(2).split(",")]
        asked = re.search(r"X = ([+\-−]?\d+) and Y = ([+\-−]?\d+)", stem)
        if not asked or len(rows) != 7:
            return None
        x, y = axis_token(asked.group(1)), axis_token(asked.group(2))
        columns = [-3, -2, -1, 0, 1, 2, 3]
        if y not in rows or x not in columns or len(rows[y]) != 7:
            return None
        return str(rows[y][columns.index(x)])
    match = re.search(r"mass (\d+) kilograms accelerates at (\d+) meters per second squared", stem)
    if match:
        mass, accel = int(match.group(1)), int(match.group(2))
        return str(independent_product(mass, accel))
    match = re.search(r"A force of (\d+) newtons moves an object (\d+) meters", stem)
    if match:
        return str(independent_product(int(match.group(1)), int(match.group(2))))
    match = re.search(r"A resistor of (\d+) ohms is connected across (\d+) volts", stem)
    if match:
        resistance, voltage = int(match.group(1)), int(match.group(2))
        if resistance == 0 or voltage % resistance != 0:
            return None
        return str(voltage // resistance)
    match = re.search(r"mass of (\d+) grams and a volume of (\d+) cubic centimeters", stem)
    if match:
        mass, volume = int(match.group(1)), int(match.group(2))
        if volume == 0 or mass % volume != 0:
            return None
        return str(mass // volume)
    match = re.search(r"A force of (\d+) newtons is spread over (\d+) square meters", stem)
    if match:
        force, area = int(match.group(1)), int(match.group(2))
        if area == 0 or force % area != 0:
            return None
        return str(force // area)
    match = re.search(r"does (\d+) joules of work in (\d+) seconds", stem)
    if match:
        work, seconds = int(match.group(1)), int(match.group(2))
        if seconds == 0 or work % seconds != 0:
            return None
        return str(work // seconds)
    match = re.search(r"mass (\d+) kilograms moves at (\d+) meters per second", stem)
    if match:
        mass, speed = int(match.group(1)), int(match.group(2))
        squared = independent_product(speed, speed)
        if squared % 2 != 0:
            return None
        return str(independent_product(mass, squared // 2))
    match = re.search(r"If y = (\d+)x \+ (\d+), what is y when x = (\d+)\?", stem)
    if match:
        slope, intercept, x_value = (int(part) for part in match.groups())
        return str(independent_product(slope, x_value) + intercept)
    match = re.search(r"If y = (\d+)x - (\d+), what is y when x = (\d+)\?", stem)
    if match:
        slope, intercept, x_value = (int(part) for part in match.groups())
        return str(independent_product(slope, x_value) - intercept)
    match = re.search(r"If y = (\d+)x, what is y when x = (\d+)\?", stem)
    if match:
        return str(independent_product(int(match.group(1)), int(match.group(2))))
    match = re.search(
        r"(\d+) pounds at arm (\d+) inches and (\d+) pounds at arm (\d+) inches",
        stem,
    )
    if match:
        weight_1, arm_1, weight_2, arm_2 = (int(part) for part in match.groups())
        moment = independent_product(weight_1, arm_1) + independent_product(weight_2, arm_2)
        total = weight_1 + weight_2
        if total == 0 or moment % total != 0:
            return None
        return str(moment // total)
    match = re.search(r"holds (\d+) gallons usable and the engine burns (\d+) gallons per hour", stem)
    if match:
        gallons, burn = int(match.group(1)), int(match.group(2))
        if burn == 0 or gallons % burn != 0:
            return None
        return str(gallons // burn)
    match = re.search(r"The wind is (\d+) knots from 30 degrees off the nose", stem)
    if match:
        wind = int(match.group(1))
        if wind % 2 != 0:
            return None
        return str(wind // 2)
    match = re.search(
        r"Occupied cells, written as \(x, y, z\), are: (.+?)\. The marked cube is at grid position x=(-?\d+), y=(-?\d+), z=(-?\d+)",
        stem,
    )
    if match:
        cells = {(int(x), int(y), int(z)) for x, y, z in re.findall(r"\((-?\d+),(-?\d+),(-?\d+)\)", match.group(1))}
        marked = (int(match.group(2)), int(match.group(3)), int(match.group(4)))
        if marked not in cells:
            return None
        count = 0
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            if (marked[0] + dx, marked[1] + dy, marked[2] + dz) in cells:
                count += 1
        return str(count)
    return None


def rng_for(text: str) -> random.Random:
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
    return random.Random(seed)


def choose(stem: str, correct: str, wrongs: list[tuple[str, str]]) -> list[tuple[str, bool, str]]:
    cleaned = []
    used = {correct}
    for text, why in wrongs:
        if text not in used:
            cleaned.append((text, why))
            used.add(text)
    numeric = re.fullmatch(r"(-?\d+(?:\.\d+)?)(.*)", correct)
    if len(cleaned) < 4 and numeric:
        value = float(numeric.group(1))
        suffix = numeric.group(2)
        scale = max(1, int(abs(value) * 0.08))
        offsets = [scale, -scale, scale + 1, -(scale + 1), 2 * scale, -2 * scale, 1, -1, 2, -2]
        rng_for(stem + "|numeric-distractors").shuffle(offsets)
        for offset in offsets:
            candidate = value + offset
            text = f"{nfmt(candidate)}{suffix}"
            if text not in used:
                cleaned.append((text, "É um valor próximo, mas resulta de um erro de cálculo ou arredondamento."))
                used.add(text)
            if len(cleaned) >= 4:
                break
    if len(cleaned) < 4:
        raise ValueError(f"menos de quatro distratores específicos: {stem}")
    bag = [(correct, True, "")] + [(text, False, why) for text, why in cleaned[:4]]
    rng_for(stem).shuffle(bag)
    return bag


def add(bucket: list[Item], item: Item, seen: set[str]) -> None:
    key = " ".join(item.stem.lower().split())
    if key in seen:
        return
    seen.add(key)
    bucket.append(item)


def arithmetic(limit: int) -> list[Item]:
    out: list[Item] = []
    seen: set[str] = set()
    speeds = list(range(24, 96, 3))
    hours = [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 6]
    for speed in speeds:
        for hour in hours:
            miles = speed * hour
            stem = (
                f"A maintenance truck travels at a steady {nfmt(speed)} miles per hour for "
                f"{nfmt(hour)} hours. How many miles does it travel?"
            )
            wrongs = [
                (nfmt(speed * (hour + 1)), "Soma uma hora que a viagem não teve."),
                (nfmt(speed + hour), "Soma velocidade e tempo em vez de multiplicar."),
                (nfmt(miles / 2), "Usa metade do tempo."),
                (nfmt(speed * hour * 2), "Dobra a distância sem motivo no enunciado."),
            ]
            add(out, Item(
                "arithmetic-reasoning", "rate-time-distance", "constant-speed",
                "basic" if hour == int(hour) else "intermediate", stem,
                choose(stem, nfmt(miles), wrongs),
                f"Distância = velocidade × tempo. {nfmt(speed)} × {nfmt(hour)} = {nfmt(miles)} milhas.",
                f"A conta independente dá {nfmt(miles)}.",
                "openstax-prealgebra", "distance = rate × time", 70,
                ["rate", "time", "distance"], "approved_calculation", "number", nfmt(miles),
            ), seen)
            if len(out) >= limit:
                return out[:limit]
    scales = [10, 12, 15, 20, 25, 40]
    for speed in range(30, 80, 5):
        for hour in (2, 2.5, 3, 4):
            for scale in scales:
                miles = speed * hour
                if miles % scale != 0:
                    continue
                inches = miles / scale
                stem = (
                    f"A car travels {nfmt(speed)} miles per hour for {nfmt(hour)} hours. "
                    f"On a map, 1 inch represents {scale} miles. How long is the trip on the map?"
                )
                wrongs = [
                    (f"{nfmt(miles)} inches", "Esta é a distância real, não a do mapa."),
                    (f"{nfmt(inches * 2)} inches", "Dobra a escala."),
                    (f"{nfmt(miles / (scale * 2))} inches", "Usa o dobro da escala."),
                    (f"{nfmt(speed / scale)} inches", "Esquece de multiplicar pelo tempo."),
                ]
                add(out, Item(
                    "arithmetic-reasoning", "rate-time-distance", "map-scale", "intermediate", stem,
                    choose(stem, f"{nfmt(inches)} inches", wrongs),
                    f"A distância real é {nfmt(speed)} × {nfmt(hour)} = {nfmt(miles)} milhas. "
                    f"No mapa, divida por {scale}: {nfmt(inches)} polegadas.",
                    f"A segunda conta, milhas ÷ escala, confirma {nfmt(inches)}.",
                    "openstax-prealgebra", "map distance = actual distance / scale", 80,
                    ["map", "scale"], "approved_calculation", "number", nfmt(inches),
                ), seen)
                if len(out) >= limit:
                    return out[:limit]
    for total in range(180, 900, 36):
        for low, high in ((4, 5), (3, 6), (2, 7), (5, 7), (6, 9)):
            pair = low + high
            if total % pair != 0:
                continue
            count = total // pair
            stem = (
                f"A club spent ${total} on two kinds of tickets, priced at ${low} and ${high}. "
                f"The same number of tickets was bought at each price. How many ${high} tickets were bought?"
            )
            wrongs = [
                (str(total // high), "Divide o total só pelo preço maior."),
                (str(count * 2), "Conta os dois tipos em vez de um só."),
                (str(max(1, count - low)), "Subtrai um preço da quantidade."),
                (str(total // low), "Divide o total só pelo preço menor."),
            ]
            add(out, Item(
                "arithmetic-reasoning", "money", "equal-counts", "intermediate", stem,
                choose(stem, str(count), wrongs),
                f"Um par custa ${pair}. {total} ÷ {pair} = {count}. Essa é a quantidade de cada preço.",
                f"A equação {low}n + {high}n = {total} tem solução n = {count}.",
                "openstax-prealgebra", "equal counts, combined price", 80,
                ["money", "pairs"], "approved_calculation", "number", str(count),
            ), seen)
            if len(out) >= limit:
                return out[:limit]
    for part, whole in ((2, 5), (2, 8), (3, 10), (4, 16), (5, 20), (6, 24), (7, 28), (9, 36)):
        for base in (40, 50, 80, 120, 150, 200, 240, 320):
            if base % whole != 0:
                continue
            value = base * part // whole
            percent = round(100 * part / whole)
            stem = f"What is {percent} percent of {base}?"
            wrongs = [
                (str(base // percent if percent else 0), "Divide a base pela porcentagem."),
                (str(value * 2), "Dobra o resultado."),
                (str(base - value), "Calcula o complemento, não a parte pedida."),
                (str(percent), "Repete a porcentagem como se fosse a quantidade."),
            ]
            add(out, Item(
                "arithmetic-reasoning", "percent", "percent-of-a-number", "basic", stem,
                choose(stem, str(value), wrongs),
                f"{percent}% = {part}/{whole}. {part}/{whole} de {base} = {value}.",
                f"A conta {base} × {part} ÷ {whole} dá {value}.",
                "openstax-prealgebra", "percent of a number", 50,
                ["percent"], "approved_calculation", "number", str(value),
            ), seen)
            if len(out) >= limit:
                return out[:limit]
    for length in range(6, 30, 2):
        for width in range(4, 20, 2):
            for height in (3, 5, 8, 10):
                volume = length * width * height
                stem = f"A rectangular container is {length} feet long, {width} feet wide, and {height} feet high. What is its volume in cubic feet?"
                wrongs = [
                    (str(length * width), "Calcula só a área da base."),
                    (str(length + width + height), "Soma as arestas em vez de multiplicar."),
                    (str(volume // 2), "Usa metade da altura."),
                    (str(2 * (length * width + length * height + width * height)), "Calcula a área da superfície."),
                ]
                add(out, Item(
                    "arithmetic-reasoning", "geometry", "rectangular-volume", "basic", stem,
                    choose(stem, str(volume), wrongs),
                    f"Volume = comprimento × largura × altura = {length} × {width} × {height} = {volume}.",
                    "O produto das três dimensões foi refeito.",
                    "openstax-prealgebra", "volume of a rectangular prism", 60,
                    ["volume"], "approved_calculation", "number", str(volume),
                ), seen)
                if len(out) >= limit:
                    return out[:limit]
    for distance in range(48, 600, 6):
        for speed in range(12, 72, 3):
            if speed == 0 or distance % speed != 0:
                continue
            hours = distance // speed
            if hours < 1 or hours > 12:
                continue
            if independent_product(speed, hours) != distance:
                continue
            stem = (
                f"A convoy must cover {distance} miles at a steady {speed} miles per hour. "
                "How many hours does the trip take?"
            )
            wrongs = [
                (str(distance * speed), "Multiplica distância por velocidade."),
                (str(distance), "Responde a distância."),
                (str(speed), "Responde a velocidade."),
                (str(hours + 2), "Erra o quociente em duas horas."),
            ]
            add(out, Item(
                "arithmetic-reasoning", "rate-time-distance", "time-required", "basic", stem,
                choose(stem, str(hours), wrongs),
                f"Tempo = distância ÷ velocidade = {distance} ÷ {speed} = {hours} horas.",
                "A divisão foi refeita a partir dos dois números do enunciado.",
                "openstax-prealgebra", "time = distance / rate", 60,
                ["rate", "time"], "approved_calculation", "number", str(hours),
            ), seen)
            if len(out) >= limit:
                return out[:limit]
    for first in range(4, 40, 2):
        for second in range(5, 50, 3):
            for third in range(6, 42, 4):
                total = first + second + third
                if total % 3 != 0:
                    continue
                average = total // 3
                stem = f"Three inspection scores are {first}, {second}, and {third}. What is their average?"
                wrongs = [
                    (str(total), "Para na soma e não divide por três."),
                    (str(first + second), "Soma só os dois primeiros."),
                    (str(max(first, second, third)), "Escolhe o maior, não a média."),
                    (str(average + 3), "Erra o quociente."),
                ]
                add(out, Item(
                    "arithmetic-reasoning", "averages", "three-number-mean", "basic", stem,
                    choose(stem, str(average), wrongs),
                    f"Média = ({first} + {second} + {third}) ÷ 3 = {total} ÷ 3 = {average}.",
                    "A soma e a divisão por três foram refeitas.",
                    "openstax-prealgebra", "arithmetic mean of three values", 50,
                    ["average"], "approved_calculation", "number", str(average),
                ), seen)
                if len(out) >= limit:
                    return out[:limit]
    return out[:limit]


def math_knowledge(limit: int) -> list[Item]:
    out: list[Item] = []
    seen: set[str] = set()
    for a in range(2, 18):
        for b in range(2, 18):
            if a == b:
                continue
            product = a * b
            stem = f"Which expression is a factor pair of {product}x² − {product}?"
            correct = f"({a}x + {a})({b}x − {b})"
            wrongs = [
                (f"({a}x − {b})({b}x + {a})", "O produto dos extremos não cancela o termo do meio."),
                (f"({a}x − {a})({b}x − {b})", "Os sinais iguais não produzem a diferença de quadrados."),
                (f"({product}x − 1)(x + {product})", "Não recupera o fator comum pedido."),
                (f"({a}x + {b})({b}x + {a})", "Não há fator comum {product} nem a forma (x² − 1)."),
            ]
            add(out, Item(
                "math-knowledge", "algebra", "common-factor", "advanced", stem,
                choose(stem, correct, wrongs),
                f"{product}(x² − 1) = {product}(x − 1)(x + 1). "
                f"({a}x + {a})({b}x − {b}) = {a * b}(x + 1)(x − 1).",
                "A expansão devolve o polinômio original, sem termo linear.",
                "openstax-intermediate", "factor a difference of squares after the common factor", 70,
                ["factoring"], "approved_relation", "text", correct,
            ), seen)
            if len(out) >= limit:
                return out[:limit]
    for numerator in (1, 2, 3, 4, 5, 6, 7, 8, 9):
        for root in (4, 9, 16, 25, 36, 49, 64, 81):
            value = -numerator / root * (root ** 0.5)
            if abs(value - round(value)) > 1e-8:
                continue
            shown = int(round(value))
            stem = f"The value of (−{numerator}/{root}) × √{root} is"
            wrongs = [
                ("0", "A expressão não vale zero."),
                (str(abs(shown)), "Esquece o sinal negativo."),
                (str(-root), "Multiplica pelo radicando inteiro, não pela raiz."),
                (str(int(root ** 0.5)), "Responde só a raiz, sem a fração."),
            ]
            add(out, Item(
                "math-knowledge", "arithmetic", "roots-and-fractions", "intermediate", stem,
                choose(stem, str(shown), wrongs),
                f"A raiz positiva de {root} é {int(root ** 0.5)}. "
                f"(−{numerator}/{root}) × {int(root ** 0.5)} = {shown}.",
                "Primeiro a raiz, depois a fração. A segunda conta confirma o mesmo valor.",
                "openstax-prealgebra", "multiply a fraction by a square root", 55,
                ["roots", "fractions"], "approved_calculation", "number", str(shown),
                glossary=[["square root", "Raiz quadrada. Aqui usa-se o valor positivo."]],
            ), seen)
            if len(out) >= limit:
                return out[:limit]
    for p, q, s, t in ((2, 3, 1, -1), (3, 1, 2, 1), (4, -1, 1, 2), (1, 2, 3, -1), (5, 1, 2, -3)):
        for target_u in range(-4, 6):
            for target_v in range(-4, 6):
                right_1 = p * target_u + q * target_v
                right_2 = s * target_u + t * target_v
                det = p * t - q * s
                if det == 0:
                    continue
                stem = (
                    f"If {p}u + {q}v = {right_1} and {s}u + {t}v = {right_2}, "
                    f"what is the solution for u and v?"
                )
                correct = f"u = {target_u}, v = {target_v}"
                wrongs = [
                    (f"u = {target_v}, v = {target_u}", "Troca as duas incógnitas."),
                    (f"u = {target_u + 1}, v = {target_v}", "Erra u em uma unidade."),
                    (f"u = {target_u}, v = {target_v + 1}", "Erra v em uma unidade."),
                    (f"u = {-target_u}, v = {-target_v}", "Inverte os dois sinais."),
                    (f"u = {target_u - 1}, v = {target_v}", "Erra u em uma unidade para baixo."),
                    (f"u = {target_u}, v = {target_v - 1}", "Erra v em uma unidade para baixo."),
                    (f"u = {target_u + 1}, v = {target_v - 1}", "Compensa as incógnitas no sentido errado."),
                ]
                add(out, Item(
                    "math-knowledge", "algebra", "linear-systems", "advanced", stem,
                    choose(stem, correct, wrongs),
                    f"Substituindo u = {target_u} e v = {target_v}, as duas equações fecham: "
                    f"{right_1} e {right_2}.",
                    "A solução foi conferida nas duas equações, não só em uma.",
                    "openstax-college", "solve a 2×2 linear system", 80,
                    ["systems"], "approved_calculation", "text", correct,
                ), seen)
                if len(out) >= limit:
                    return out[:limit]
    for slope in range(2, 9):
        for x_value in range(1, 13):
            for intercept in range(-6, 7):
                if intercept > 0:
                    expression = f"{slope}x + {intercept}"
                elif intercept < 0:
                    expression = f"{slope}x - {abs(intercept)}"
                else:
                    expression = f"{slope}x"
                value = independent_product(slope, x_value) + intercept
                stem = f"If y = {expression}, what is y when x = {x_value}?"
                wrongs = [
                    (str(slope + x_value + intercept), "Soma os números em vez de multiplicar a inclinação por x."),
                    (str(independent_product(slope, x_value)), "Esquece a constante." if intercept else "Repete só o produto, sem alterar o caso sem constante."),
                    (str(value + slope), "Soma a inclinação depois do resultado."),
                    (str(intercept), "Responde só a constante."),
                ]
                add(out, Item(
                    "math-knowledge", "algebra", "linear-evaluation", "basic", stem,
                    choose(stem, str(value), wrongs),
                    f"y = {slope} × {x_value} + ({intercept}) = {value}.",
                    "O produto da inclinação por x e a soma da constante foram refeitos.",
                    "openstax-college", "evaluate a linear expression", 45,
                    ["linear"], "approved_calculation", "number", str(value),
                ), seen)
                if len(out) >= limit:
                    return out[:limit]
    return out[:limit]


def table_reading(limit: int) -> list[Item]:
    out: list[Item] = []
    seen: set[str] = set()
    axes = [-3, -2, -1, 0, 1, 2, 3]
    serial = 0
    while len(out) < limit:
        rng = random.Random(1000 + serial)
        serial += 1
        cells = list(range(20, 69))
        rng.shuffle(cells)
        grid = {}
        index = 0
        for y in axes:
            for x in axes:
                grid[(x, y)] = cells[index]
                index += 1
        x = axes[serial % 7]
        y = axes[(serial // 7) % 7]
        value = grid[(x, y)]
        neighbors = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1)):
            nx, ny = x + dx, y + dy
            if (nx, ny) in grid and grid[(nx, ny)] != value:
                neighbors.append(grid[(nx, ny)])
        while len(neighbors) < 4:
            neighbors.append(value + len(neighbors) + 3)
        stem = (
            f"In table T{serial}, X is the column and Y is the row. "
            f"The columns, from left to right, are −3, −2, −1, 0, +1, +2, +3. "
            f"The rows, from top to bottom, are +3, +2, +1, 0, −1, −2, −3. "
            f"The row +3 reads: " + ", ".join(str(grid[(col, 3)]) for col in axes) + ". "
            f"The row +2 reads: " + ", ".join(str(grid[(col, 2)]) for col in axes) + ". "
            f"The row +1 reads: " + ", ".join(str(grid[(col, 1)]) for col in axes) + ". "
            f"The row 0 reads: " + ", ".join(str(grid[(col, 0)]) for col in axes) + ". "
            f"The row −1 reads: " + ", ".join(str(grid[(col, -1)]) for col in axes) + ". "
            f"The row −2 reads: " + ", ".join(str(grid[(col, -2)]) for col in axes) + ". "
            f"The row −3 reads: " + ", ".join(str(grid[(col, -3)]) for col in axes) + ". "
            f"Which number is at X = {x if x <= 0 else '+' + str(x)} and Y = {y if y <= 0 else '+' + str(y)}?"
        )
        wrongs = [(str(number), "É uma célula vizinha, não o cruzamento pedido.") for number in neighbors[:4]]
        add(out, Item(
            "table-reading", "grid-lookup", "xy-intersection", "basic", stem,
            choose(stem, str(value), wrongs),
            f"A coluna {x} e a linha {y} se cruzam em {value}. Não some X com Y.",
            "O valor foi lido de novo na grade gerada.",
            "pearson-vue-afoqt", "X selects the column and Y selects the row", 11,
            ["table", "speed"], "approved_calculation", "number", str(value),
        ), seen)
    return out[:limit]


def science(limit: int) -> list[Item]:
    out: list[Item] = []
    seen: set[str] = set()
    facts = [
        ("A newton is the SI unit of", "force", ["mass", "energy", "power", "pressure"],
         "O newton mede força. Massa é quilograma, energia é joule, potência é watt e pressão é pascal."),
        ("Electrical resistance is measured in", "ohms", ["amperes", "volts", "watts", "joules"],
         "Resistência se mede em ohms. Ampere é corrente, volt é tensão e watt é potência."),
        ("The tendency of an object to resist a change in motion is", "inertia", ["velocity", "pressure", "frequency", "density"],
         "Inércia é a resistência à mudança do movimento. Não é a velocidade em si."),
        ("Work, in the mechanical sense, is", "force times distance", ["mass times velocity", "force divided by area", "mass times acceleration", "distance divided by time"],
         "Trabalho mecânico é força vezes deslocamento na direção da força."),
        ("A simple machine that is a bar turning about a fulcrum is a", "lever", ["pulley", "inclined plane", "wedge", "wheel and axle"],
         "A alavanca é a barra que gira em torno do fulcro. Polia, plano, cunha e roda são outras máquinas."),
        ("Density is", "mass divided by volume", ["mass times velocity", "force times distance", "volume divided by time", "weight times height"],
         "Densidade é massa por volume."),
        ("According to Newton's third law, forces occur", "in pairs of equal magnitude and opposite direction", ["only when objects are at rest", "as a single unbalanced force", "only in a vacuum", "in pairs that always point the same way"],
         "A terceira lei fala de pares de ação e reação, de mesmo módulo e sentidos opostos."),
        ("Kinetic energy depends on", "mass and speed", ["only color", "only direction of the compass", "only the object's name", "only altitude above the sea"],
         "Energia cinética depende da massa e da velocidade."),
        ("A current of electrical charge is measured in", "amperes", ["ohms", "newtons", "pascals", "candelas"],
         "Corrente elétrica se mede em amperes."),
        ("The mechanical advantage of an ideal lever is greater than 1 when", "the effort arm is longer than the load arm", ["the fulcrum is removed", "the load arm is longer than the effort arm", "both arms are equal and friction is infinite", "the bar has no length"],
         "Na alavanca ideal, a vantagem mecânica é braço da força dividido pelo braço da carga."),
    ]
    for prompt, correct, distractors, why in facts:
        stem = prompt
        wrongs = [(text, why) for text in distractors]
        add(out, Item(
            "physical-science", "concepts", "core-vocabulary", "basic", stem,
            choose(stem, correct, wrongs),
            why, why, "openstax-physics", prompt, 30,
            ["concept"], "approved_relation", "text", correct,
        ), seen)
    for mass in range(2, 25):
        for accel in range(2, 12):
            force = mass * accel
            stem = f"A crate of mass {mass} kilograms accelerates at {accel} meters per second squared. What net force, in newtons, acts on it?"
            wrongs = [
                (str(mass + accel), "Soma massa e aceleração."),
                (str(force + mass), "Soma a massa ao produto."),
                (str(accel), "Responde só a aceleração."),
                (str(mass * accel * 2), "Dobra a força."),
            ]
            add(out, Item(
                "physical-science", "mechanics", "newton-second-law", "basic", stem,
                choose(stem, str(force), wrongs),
                f"F = m × a = {mass} × {accel} = {force} newtons.",
                "A segunda conta, massa vezes aceleração, repete o mesmo produto.",
                "openstax-physics", "F = ma", 30,
                ["force"], "approved_calculation", "number", str(force),
            ), seen)
            if len(out) >= limit:
                return out[:limit]
    for force in (10, 20, 25, 40, 50):
        for distance in (2, 3, 4, 5, 8):
            work = force * distance
            stem = f"A force of {force} newtons moves an object {distance} meters in the direction of the force. How much work, in joules, is done?"
            wrongs = [
                (str(force + distance), "Soma força e distância."),
                (str(force), "Ignora a distância."),
                (str(work // 2 if work % 2 == 0 else work + 5), "Não usa o produto completo."),
                (str(distance), "Ignora a força."),
            ]
            add(out, Item(
                "physical-science", "energy", "mechanical-work", "intermediate", stem,
                choose(stem, str(work), wrongs),
                f"Trabalho = força × distância = {force} × {distance} = {work} joules.",
                "A conta foi refeita pelo produto.",
                "openstax-physics", "W = Fd when force and displacement are parallel", 30,
                ["work"], "approved_calculation", "number", str(work),
            ), seen)
            if len(out) >= limit:
                return out[:limit]
    for voltage in (6, 12, 18, 24):
        for resistance in (2, 3, 4, 6):
            if voltage % resistance != 0:
                continue
            current = voltage // resistance
            stem = f"A resistor of {resistance} ohms is connected across {voltage} volts. What current, in amperes, flows?"
            wrongs = [
                (str(voltage * resistance), "Multiplica em vez de dividir."),
                (str(voltage), "Confunde tensão com corrente."),
                (str(resistance), "Confunde resistência com corrente."),
                (str(current + resistance), "Soma a resistência ao resultado."),
            ]
            add(out, Item(
                "physical-science", "electricity", "ohm-law", "intermediate", stem,
                choose(stem, str(current), wrongs),
                f"I = V / R = {voltage} / {resistance} = {current} amperes.",
                "A lei de Ohm foi aplicada de novo na verificação.",
                "openstax-physics", "I = V / R", 30,
                ["ohm"], "approved_calculation", "number", str(current),
            ), seen)
            if len(out) >= limit:
                return out[:limit]
    for mass in range(4, 48, 2):
        for volume in range(2, 10):
            if volume == 0 or mass % volume != 0:
                continue
            density = mass // volume
            stem = (
                f"A sample has a mass of {mass} grams and a volume of {volume} cubic centimeters. "
                "What is its density in grams per cubic centimeter?"
            )
            wrongs = [
                (str(mass * volume), "Multiplica massa por volume."),
                (str(mass), "Responde a massa."),
                (str(volume), "Responde o volume."),
                (str(density + volume), "Soma o volume ao quociente."),
            ]
            add(out, Item(
                "physical-science", "matter", "density", "basic", stem,
                choose(stem, str(density), wrongs),
                f"Densidade = massa ÷ volume = {mass} ÷ {volume} = {density}.",
                "A divisão foi refeita.",
                "openstax-physics", "density = mass / volume", 30,
                ["density"], "approved_calculation", "number", str(density),
            ), seen)
            if len(out) >= limit:
                return out[:limit]
    for force in range(20, 160, 5):
        for area in (2, 4, 5, 8, 10):
            if force % area != 0:
                continue
            pressure = force // area
            stem = (
                f"A force of {force} newtons is spread over {area} square meters. "
                "What is the pressure in pascals?"
            )
            wrongs = [
                (str(force * area), "Multiplica força por área."),
                (str(force), "Responde a força."),
                (str(area), "Responde a área."),
                (str(pressure + area), "Soma a área ao quociente."),
            ]
            add(out, Item(
                "physical-science", "fluids", "pressure", "intermediate", stem,
                choose(stem, str(pressure), wrongs),
                f"Pressão = força ÷ área = {force} ÷ {area} = {pressure} pascals.",
                "A divisão foi refeita.",
                "openstax-physics", "pressure = force / area", 30,
                ["pressure"], "approved_calculation", "number", str(pressure),
            ), seen)
            if len(out) >= limit:
                return out[:limit]
    for work in range(20, 240, 10):
        for seconds in (2, 4, 5, 8, 10):
            if work % seconds != 0:
                continue
            power = work // seconds
            stem = f"A machine does {work} joules of work in {seconds} seconds. What is the power in watts?"
            wrongs = [
                (str(work * seconds), "Multiplica trabalho por tempo."),
                (str(work), "Responde o trabalho."),
                (str(seconds), "Responde o tempo."),
                (str(power + seconds), "Soma o tempo ao quociente."),
            ]
            add(out, Item(
                "physical-science", "energy", "power", "intermediate", stem,
                choose(stem, str(power), wrongs),
                f"Potência = trabalho ÷ tempo = {work} ÷ {seconds} = {power} watts.",
                "A divisão foi refeita.",
                "openstax-physics", "power = work / time", 30,
                ["power"], "approved_calculation", "number", str(power),
            ), seen)
            if len(out) >= limit:
                return out[:limit]
    for mass in (2, 4, 6, 8, 10, 12):
        for speed in (2, 4, 6, 8, 10):
            squared = independent_product(speed, speed)
            kinetic = independent_product(mass, squared // 2)
            stem = (
                f"An object of mass {mass} kilograms moves at {speed} meters per second. "
                "What is its kinetic energy in joules? Use KE = 1/2 mv²."
            )
            wrongs = [
                (str(mass * speed), "Multiplica massa pela velocidade, sem o quadrado nem o meio."),
                (str(independent_product(mass, squared)), "Esquece o fator 1/2."),
                (str(squared), "Responde só o quadrado da velocidade."),
                (str(kinetic + mass), "Soma a massa ao resultado."),
            ]
            add(out, Item(
                "physical-science", "energy", "kinetic-energy", "advanced", stem,
                choose(stem, str(kinetic), wrongs),
                f"KE = 1/2 × {mass} × {speed}² = 1/2 × {mass} × {squared} = {kinetic} joules.",
                "O quadrado e o fator 1/2 foram refeitos por soma repetida.",
                "openstax-physics", "KE = 1/2 mv^2", 40,
                ["kinetic"], "approved_calculation", "number", str(kinetic),
            ), seen)
            if len(out) >= limit:
                return out[:limit]
    return out[:limit]


def instruments(limit: int) -> list[Item]:
    out: list[Item] = []
    seen: set[str] = set()
    headings = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
    pitches = ["climbing", "level", "descending", "steeply climbing", "steeply descending"]
    banks = ["no bank", "banked right", "banked left", "steeply banked right", "steeply banked left"]
    for heading in headings:
        for pitch in pitches:
            for bank in banks:
                stem = (
                    "Use the training convention of a fixed miniature airplane and a moving horizon. "
                    f"The attitude indicator shows the airplane {pitch}, and it is {bank}. "
                    f"The heading indicator shows {heading}. Which statement matches both instruments?"
                )
                correct = f"The airplane is {pitch}, is {bank}, and is headed {heading}."
                pitch_index = pitches.index(pitch)
                bank_index = banks.index(bank)
                heading_index = headings.index(heading)
                other_pitch = pitches[(pitch_index + 1 + heading_index % 3) % len(pitches)]
                other_bank = banks[(bank_index + 1 + pitch_index % 3) % len(banks)]
                other_heading = headings[(heading_index + 1 + bank_index % 3) % len(headings)]
                wrongs = [
                    (f"The airplane is {other_pitch}, is {bank}, and is headed {heading}.", "Inverte a arfagem."),
                    (f"The airplane is {pitch}, is {other_bank}, and is headed {heading}.", "Inverte a inclinação lateral."),
                    (f"The airplane is {pitch}, is {bank}, and is headed {other_heading}.", "Troca o rumo."),
                    (f"The airplane is {other_pitch}, is {other_bank}, and is headed {other_heading}.", "Erra os três dados."),
                ]
                figure = horizon_svg(pitch, bank, heading)
                add(out, Item(
                    "instrument-comprehension", "attitude-and-heading", "three-parameter-read",
                    "intermediate", stem, choose(stem, correct, wrongs),
                    "Leia um eixo de cada vez: arfagem, inclinação e rumo. A frase certa conserva os três.",
                    "Os três parâmetros do item batem com a frase marcada.",
                    "faa-ifh", "fixed miniature airplane, moving horizon, plus heading", 12,
                    ["attitude", "heading"], "approved_relation", "text", correct, figure,
                    glossary=[
                        ["climbing", "Subindo. No horizonte artificial de aviãozinho fixo, aparece mais céu."],
                        ["descending", "Descendo. Aparece mais terra."],
                        ["banked right", "Inclinado para a direita do piloto: a asa direita desce."],
                        ["banked left", "Inclinado para a esquerda do piloto: a asa esquerda desce."],
                        ["steeply climbing", "Subida acentuada: o céu ocupa mais do mostrador."],
                        ["steeply descending", "Descida acentuada: a terra ocupa mais do mostrador."],
                        ["steeply banked right", "Inclinação forte para a direita do piloto."],
                        ["steeply banked left", "Inclinação forte para a esquerda do piloto."],
                        ["no bank", "Sem inclinação lateral. As asas estão niveladas."],
                    ],
                ), seen)
                if len(out) >= limit:
                    return out[:limit]
                false_stem = (
                    "Use the training convention of a fixed miniature airplane and a moving horizon. "
                    f"The instruments show {pitch}, {bank}, and a heading of {heading}. "
                    "Which statement is false?"
                )
                false_correct = f"The heading indicator shows {other_heading}."
                false_wrongs = [
                    (f"The attitude indicator shows {pitch}.", "Isso está de acordo com a arfagem indicada."),
                    (f"The bank indication is {bank}.", "Isso está de acordo com a inclinação indicada."),
                    (f"The heading indicator shows {heading}.", "Esse é o rumo indicado."),
                    (f"The airplane is {pitch} while {bank}.", "A combinação repete os dois dados de atitude."),
                ]
                add(out, Item(
                    "instrument-comprehension", "attitude-and-heading", "which-statement-is-false",
                    "advanced", false_stem, choose(false_stem, false_correct, false_wrongs),
                    f"O rumo indicado é {heading}, não {other_heading}. As outras frases repetem os instrumentos.",
                    "A frase falsa é a única que troca um dos três parâmetros.",
                    "faa-ifh", "identify the statement that contradicts the instruments", 12,
                    ["attitude", "false-statement"], "approved_relation", "text", false_correct, figure,
                ), seen)
                if len(out) >= limit:
                    return out[:limit]
    return out[:limit]


def horizon_svg(pitch: str, bank: str, heading: str) -> str:
    tilt = {
        "no bank": 0,
        "banked right": -18,
        "banked left": 18,
        "steeply banked right": -40,
        "steeply banked left": 40,
    }[bank]
    shift = {
        "climbing": 14,
        "level": 0,
        "descending": -14,
        "steeply climbing": 28,
        "steeply descending": -28,
    }[pitch]
    return (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 220 120'>"
        "<rect width='220' height='120' fill='#f7f1e6'/>"
        f"<g transform='translate(55 60)'><circle r='42' fill='#d7e6f2' stroke='#172838'/>"
        f"<g transform='rotate({tilt}) translate(0 {shift})'><rect x='-60' y='0' width='120' height='70' fill='#c4a574'/>"
        "<rect x='-60' y='-70' width='120' height='70' fill='#8fb4d6'/></g>"
        "<rect x='-16' y='-2' width='32' height='4' fill='#172838'/>"
        "<text y='56' text-anchor='middle' font-size='8' fill='#172838'>attitude</text></g>"
        f"<g transform='translate(160 60)'><circle r='42' fill='#fff' stroke='#172838'/>"
        f"<polygon points='0,-28 6,8 -6,8' fill='#8d2e2a' transform='rotate({heading_angle(heading)})'/>"
        "<text y='56' text-anchor='middle' font-size='8' fill='#172838'>heading</text></g></svg>"
    )


def heading_angle(name: str) -> int:
    order = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
    return order.index(name) * 45


def occupied(kind: str, size: int) -> set[tuple[int, int, int]]:
    cells = set()
    if kind == "wall":
        for x in range(size):
            for z in range(size):
                cells.add((x, 0, z))
    elif kind == "slab":
        for x in range(size):
            for y in range(size):
                cells.add((x, y, 0))
    elif kind == "stair":
        for x in range(size):
            for z in range(x + 1):
                cells.add((x, 0, z))
    else:
        for x in range(size):
            for y in range(max(1, size - 1)):
                cells.add((x, y, 0))
        for z in range(1, size):
            cells.add((0, 0, z))
    return cells


def touch_count(cells: set[tuple[int, int, int]], cell: tuple[int, int, int]) -> int:
    x, y, z = cell
    count = 0
    for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        if (x + dx, y + dy, z + dz) in cells:
            count += 1
    return count


def blocks(limit: int) -> list[Item]:
    out: list[Item] = []
    seen: set[str] = set()
    serial = 0
    kinds = ["wall", "slab", "stair", "corner"]
    while len(out) < limit and serial < 5000:
        kind = kinds[serial % 4]
        size = 2 + (serial % 3)
        cells = occupied(kind, size)
        ordered = sorted(cells)
        target = ordered[serial % len(ordered)]
        count = touch_count(cells, target)
        serial += 1
        label = f"B{serial}"
        cell_text = "; ".join(f"({x},{y},{z})" for x, y, z in ordered)
        stem = (
            f"Figure {label} is an original stack of equal cubes. "
            f"Cubes touch only when they share a full face. "
            f"Occupied cells, written as (x, y, z), are: {cell_text}. "
            f"The marked cube is at grid position x={target[0]}, y={target[1]}, z={target[2]}, "
            f"with z vertical. How many other cubes does the marked cube touch?"
        )
        candidates = [value for value in range(7) if value != count]
        local_rng = rng_for(stem + "|block-distractors")
        candidates.sort(key=lambda value: (abs(value - count), local_rng.random()))
        wrongs = [
            (str(candidate), "Conta uma face a mais ou a menos, ou inclui contato só de aresta ou canto.")
            for candidate in candidates[:4]
        ]
        add(out, Item(
            "block-counting", "face-adjacency", kind, "intermediate", stem,
            choose(stem, str(count), wrongs[:4]),
            f"O cubo marcado compartilha face com {count} vizinho(s). Contato só de aresta ou canto não entra.",
            "A vizinhança foi contada de novo nas seis direções.",
            "pearson-vue-afoqt", "count cubes that share a face with the marked cube", 12,
            ["spatial"], "approved_calculation", "number", str(count),
            figure=blocks_svg(cells, target),
        ), seen)
    return out[:limit]


def blocks_svg(cells: set[tuple[int, int, int]], marked: tuple[int, int, int]) -> str:
    def project(x: int, y: int, z: int) -> tuple[float, float]:
        return (40 + (x - y) * 16, 90 + (x + y) * 8 - z * 16)

    parts = ["<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 180 140'>",
             "<rect width='180' height='140' fill='#f7f1e6'/>"]
    for x, y, z in sorted(cells, key=lambda c: (c[0] + c[1] - c[2])):
        corners = [project(x + dx, y + dy, z + dz) for dx in (0, 1) for dy in (0, 1) for dz in (0, 1)]
        # eight corners in binary order 000,100,010,110,001,101,011,111 is not what the loop made.
        # Rebuild explicitly.
        c000 = project(x, y, z)
        c100 = project(x + 1, y, z)
        c010 = project(x, y + 1, z)
        c110 = project(x + 1, y + 1, z)
        c001 = project(x, y, z + 1)
        c101 = project(x + 1, y, z + 1)
        c011 = project(x, y + 1, z + 1)
        c111 = project(x + 1, y + 1, z + 1)
        fill = "#1b6b4c" if (x, y, z) == marked else "#d7c4a3"
        def poly(points: list[tuple[float, float]], color: str) -> str:
            body = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
            return f"<polygon points='{body}' fill='{color}' stroke='#172838' stroke-width='0.6'/>"
        parts.append(poly([c001, c101, c111, c011], "#efe2cb" if (x, y, z) != marked else "#8fd0b0"))
        parts.append(poly([c010, c110, c111, c011], fill))
        parts.append(poly([c100, c110, c111, c101], "#c4a574" if (x, y, z) != marked else "#147a55"))
    parts.append("</svg>")
    return "".join(parts)


def aviation(limit: int) -> list[Item]:
    out: list[Item] = []
    seen: set[str] = set()
    facts = [
        ("In steady, unaccelerated flight, thrust is opposed by", "drag",
         ["lift", "weight", "camber", "dihedral"],
         "A tração empurra para a frente. O arrasto se opõe a ela. Sustentação e peso formam o outro par."),
        ("The angle between the wing chord line and the relative wind is the", "angle of attack",
         ["angle of incidence", "pitch attitude", "dihedral angle", "sweep angle"],
         "Ângulo de ataque é corda contra vento relativo. Incidência é o ângulo em que a asa está presa."),
        ("A stall occurs when the wing exceeds its", "critical angle of attack",
         ["never-exceed speed only", "maximum taxi speed", "empty weight", "standard lapse rate"],
         "O estol está ligado ao ângulo de ataque crítico, não a um único número de velocidade."),
        ("Taxiway edge lights are", "blue",
         ["white", "green", "red", "amber"],
         "A borda da taxiway é azul. Branco é típico da borda da pista."),
        ("Runway edge lights are normally", "white",
         ["blue", "alternating red and green", "purple", "black"],
         "A borda da pista de pouso é branca. Azul identifica a taxiway."),
        ("The cowling is installed", "around the engine",
         ["on the tail skid", "inside the fuel tank", "at the wing tip only", "on the rudder pedals"],
         "Cowling é a carenagem em volta do motor."),
        ("The fuselage is", "the main body of the airplane",
         ["the left aileron", "the magnetic compass card", "a type of cloud", "the nose-wheel shimmy damper only"],
         "Fuselagem é o corpo principal do avião."),
        ("An altimeter is essentially", "an aneroid barometer",
         ["a gyroscope that shows heading", "a fuel-flow meter", "a stall-warning vane", "a transponder"],
         "O altímetro aneróide sente pressão estática e a apresenta como altitude."),
        ("Moving the center of gravity too far aft tends to", "reduce longitudinal stability",
         ["increase the tire pressure requirement only", "paint the wingtips", "change the magnetic variation", "stop carburetor ice"],
         "CG muito atrás diminui a estabilidade longitudinal."),
        ("Extending flaps generally", "increases both lift and drag",
         ["removes all drag", "decreases wing camber", "changes magnetic variation", "empties the fuel tanks"],
         "Flape aumenta a curvatura da asa e, com ela, sustentação e arrasto."),
        ("Standard sea-level pressure in inches of mercury is", "29.92",
         ["14.7", "1013", "15.00", "32.00"],
         "A pressão padrão ao nível do mar é 29,92 in Hg. 1013 é o valor em hectopascais, não em polegadas."),
        ("On a standard day, air temperature decreases about", "2 degrees Celsius per 1,000 feet",
         ["2 degrees Celsius per 100 feet", "10 degrees Celsius per 1,000 feet", "nothing until 18,000 feet", "1 degree Celsius per 10,000 feet"],
         "A razão padrão aproximada é 2 °C a cada 1.000 pés."),
        ("Dihedral primarily contributes to", "lateral stability",
         ["longitudinal trim only", "compass deviation", "fuel octane", "transponder coding"],
         "O diedro ajuda a estabilidade lateral, o retorno da asa que desceu."),
        ("The pitot tube is used in measuring", "airspeed",
         ["cabin altitude only", "fuel quantity", "oil temperature", "heading"],
         "O tubo de pitot capta pressão de impacto para o velocímetro."),
        ("If the airplane ammeter shows a sustained discharge, the battery is", "supplying electrical load because generation is insufficient",
         ["being charged above its limit", "disconnected from the airframe", "indicating a full fuel tank", "showing magnetic variation"],
         "Descarga contínua significa que a bateria entrega energia porque a geração não cobre o consumo."),
        ("Weight and balance uses moment as", "weight times arm",
         ["weight plus arm", "weight divided by drag", "arm divided by temperature", "lift times thrust"],
         "Momento é peso vezes braço."),
    ]
    for prompt, correct, distractors, why in facts:
        stem = prompt
        add(out, Item(
            "aviation-information", "concepts", "core-flight", "basic", stem,
            choose(stem, correct, [(text, why) for text in distractors]),
            why, why, "faa-phak", prompt, 24, ["aviation"], "approved_relation", "text", correct,
        ), seen)
    for weight_1, arm_1 in ((100, 20), (120, 25), (150, 30), (80, 40), (200, 15)):
        for weight_2, arm_2 in ((50, 60), (40, 70), (90, 10), (60, 50), (30, 80)):
            moment = weight_1 * arm_1 + weight_2 * arm_2
            total = weight_1 + weight_2
            if moment % total != 0:
                continue
            cg = moment // total
            stem = (
                f"An airplane is loaded with {weight_1} pounds at arm {arm_1} inches and "
                f"{weight_2} pounds at arm {arm_2} inches. What is the center of gravity, in inches?"
            )
            wrongs = [
                (str((arm_1 + arm_2) // 2), "Tira a média dos braços e esquece os pesos."),
                (str(moment), "Para no momento total e não divide pelo peso."),
                (str(total), "Responde o peso total."),
                (str(cg + 5), "Erra o quociente."),
            ]
            add(out, Item(
                "aviation-information", "weight-balance", "cg", "intermediate", stem,
                choose(stem, str(cg), wrongs),
                f"Momento total = {weight_1}×{arm_1} + {weight_2}×{arm_2} = {moment}. "
                f"CG = {moment} ÷ {total} = {cg} polegadas.",
                "A divisão foi refeita.",
                "faa-phak", "CG = total moment / total weight", 40,
                ["weight", "balance"], "approved_calculation", "number", str(cg),
            ), seen)
            if len(out) >= limit:
                return out[:limit]
    for gallons in (12, 18, 24, 30, 36, 42, 48):
        for burn in (6, 8, 9, 12):
            if gallons % burn != 0:
                continue
            hours = gallons // burn
            stem = f"A tank holds {gallons} gallons usable and the engine burns {burn} gallons per hour. How many hours of fuel are available?"
            wrongs = [
                (str(gallons * burn), "Multiplica em vez de dividir."),
                (str(gallons), "Responde a quantidade de combustível."),
                (str(burn), "Responde o consumo."),
                (str(hours + 2), "Erra o quociente."),
            ]
            add(out, Item(
                "aviation-information", "performance", "endurance", "basic", stem,
                choose(stem, str(hours), wrongs),
                f"Autonomia = {gallons} ÷ {burn} = {hours} horas.",
                "A divisão foi conferida de novo.",
                "faa-phak", "endurance = usable fuel / burn rate", 30,
                ["fuel"], "approved_calculation", "number", str(hours),
            ), seen)
            if len(out) >= limit:
                return out[:limit]
    for wind in (10, 16, 20, 24, 30, 40):
        stem = f"The wind is {wind} knots from 30 degrees off the nose. Using sin 30° = 1/2, what is the crosswind component in knots?"
        cross = wind // 2
        wrongs = [
            (str(wind), "Esse é o vento total, não a componente lateral."),
            (str(cross * 3), "Não aplica o seno de 30°."),
            ("0", "Trinta graus fora do nariz não é vento de proa puro."),
            (str(cross + wind), "Soma a componente ao vento total."),
        ]
        add(out, Item(
            "aviation-information", "performance", "crosswind", "advanced", stem,
            choose(stem, str(cross), wrongs),
            f"Componente lateral = vento × sen(30°) = {wind} × 1/2 = {cross} nós.",
            "A conta usa o seno informado no enunciado.",
            "faa-afh", "crosswind = wind × sin(angle off the nose)", 35,
            ["wind"], "approved_calculation", "number", str(cross),
        ), seen)
        if len(out) >= limit:
            return out[:limit]
    for weight_1 in range(40, 240, 10):
        for arm_1 in (10, 15, 20, 25, 30, 40):
            for weight_2 in range(20, 140, 10):
                for arm_2 in (10, 20, 30, 40, 50, 60, 80):
                    moment = independent_product(weight_1, arm_1) + independent_product(weight_2, arm_2)
                    total = weight_1 + weight_2
                    if total == 0 or moment % total != 0:
                        continue
                    cg = moment // total
                    stem = (
                        f"A loaded airplane has {weight_1} pounds at arm {arm_1} inches and "
                        f"{weight_2} pounds at arm {arm_2} inches. Where is the center of gravity, in inches from the datum?"
                    )
                    wrongs = [
                        (str((arm_1 + arm_2) // 2), "Média dos braços, sem ponderar pelos pesos."),
                        (str(moment), "Para no momento total."),
                        (str(total), "Responde o peso total."),
                        (str(abs(arm_1 - arm_2)), "Subtrai os braços."),
                    ]
                    add(out, Item(
                        "aviation-information", "weight-balance", "two-station-cg", "intermediate", stem,
                        choose(stem, str(cg), wrongs),
                        f"Momento = {weight_1}×{arm_1} + {weight_2}×{arm_2} = {moment}. "
                        f"CG = {moment} ÷ {total} = {cg} polegadas.",
                        "Os dois produtos e a divisão pelo peso total foram refeitos.",
                        "faa-phak", "CG = total moment / total weight", 45,
                        ["weight", "balance"], "approved_calculation", "number", str(cg),
                    ), seen)
                    if len(out) >= limit:
                        return out[:limit]
    return out[:limit]


ANTONYMS = [
    ("hot", "cold"), ("up", "down"), ("scarce", "abundant"), ("timid", "bold"),
    ("arid", "humid"), ("lenient", "strict"), ("permanent", "temporary"), ("accept", "reject"),
    ("arrive", "depart"), ("expand", "contract"), ("victory", "defeat"), ("ascend", "descend"),
    ("rural", "urban"), ("maximum", "minimum"), ("interior", "exterior"), ("optimism", "pessimism"),
    ("voluntary", "compulsory"), ("inhale", "exhale"), ("prosperity", "poverty"), ("convex", "concave"),
]
SYNONYMS = [
    ("begin", "start"), ("repair", "fix"), ("rapid", "swift"), ("cautious", "careful"),
    ("brief", "concise"), ("enormous", "huge"), ("assist", "help"), ("purchase", "buy"),
    ("error", "mistake"), ("vacant", "empty"), ("annual", "yearly"), ("conceal", "hide"),
    ("genuine", "real"), ("hazard", "danger"), ("imitate", "copy"), ("predict", "forecast"),
]
PARTS = [
    ("page", "book"), ("petal", "flower"), ("rung", "ladder"), ("brick", "wall"),
    ("finger", "hand"), ("room", "house"), ("key", "keyboard"), ("blade", "propeller"),
    ("stanza", "poem"), ("cabin", "aircraft"), ("spoke", "wheel"), ("toe", "foot"),
]
FUNCTIONS = [
    ("knife", "cut"), ("pen", "write"), ("brake", "slow"), ("lamp", "illuminate"),
    ("filter", "strain"), ("anchor", "secure"), ("scissors", "snip"), ("lock", "fasten"),
    ("oven", "bake"), ("umbrella", "shelter"), ("thermometer", "measure"), ("compass", "orient"),
]
DEGREES = [
    ("warm", "hot"), ("cool", "cold"), ("dislike", "hate"), ("like", "love"),
    ("breeze", "gale"), ("smile", "laugh"), ("tired", "exhausted"), ("fear", "terror"),
    ("drizzle", "downpour"), ("pleased", "delighted"),
]
SEQUENCES = [
    ("seed", "plant"), ("dawn", "morning"), ("plan", "execution"), ("draft", "revision"),
    ("spring", "summer"), ("question", "answer"), ("takeoff", "cruise"), ("mix", "bake"),
    ("ignition", "combustion"), ("caterpillar", "butterfly"),
]
RELATIONS = [
    ("antonym", ANTONYMS), ("synonym", SYNONYMS), ("part-whole", PARTS),
    ("function", FUNCTIONS), ("degree", DEGREES), ("sequence", SEQUENCES),
]
RELATION_PT = {
    "antonym": "antônimos",
    "synonym": "sinônimos",
    "part-whole": "parte e todo",
    "function": "objeto e função",
    "degree": "grau, do mais fraco para o mais forte",
    "sequence": "uma etapa e a seguinte",
}


def analogies(limit: int) -> list[Item]:
    out: list[Item] = []
    seen: set[str] = set()
    pool = []
    queues = []
    relation_pairs = {name: pairs for name, pairs in RELATIONS}
    for name, pairs in RELATIONS:
        for left, right in pairs:
            pool.append((name, left, right))
        queue = []
        for i, (left, right) in enumerate(pairs):
            for j, (left_2, right_2) in enumerate(pairs):
                if i != j:
                    queue.append((name, left, right, left_2, right_2))
        queues.append(queue)
    while len(out) < limit and any(queues):
        for queue in queues:
            if not queue or len(out) >= limit:
                continue
            name, left, right, left_2, right_2 = queue.pop(0)
            stem = f"{left} is to {right} as {left_2} is to"
            same_relation = [candidate for _, candidate in relation_pairs[name] if candidate != right_2]
            local_rng = rng_for(stem + "|analogy-distractors")
            local_rng.shuffle(same_relation)
            distractors = same_relation[:4]
            wrongs = [(word, f"Não completa a relação de {RELATION_PT[name]}.") for word in distractors]
            add(out, Item(
                "verbal-analogies", name, "pair-completion",
                "basic" if name in ("synonym", "antonym") else "intermediate",
                stem, choose(stem, right_2, wrongs),
                f"A relação é de {RELATION_PT[name]}. {left} combina com {right}; {left_2} combina com {right_2}.",
                "Só uma alternativa conserva a mesma relação do primeiro par.",
                "original-lexicon", name, 19, [name], "approved_relation", "text", right_2,
                glossary=[[left, f"Primeiro termo do par. A relação treinada é de {RELATION_PT[name]}."]],
            ), seen)
    return out[:limit]


WK_ROWS = """
abundant|plentiful|scarce|silent
scarce|sparse|crowded|rapid
lucid|clear|muddled|heavy
fragile|delicate|sturdy|loud
concise|brief|wordy|ancient
candid|frank|deceitful|liquid
diligent|industrious|lazy|round
prudent|cautious|reckless|purple
timid|shy|bold|metallic
arid|dry|wet|musical
hostile|unfriendly|kind|numeric
benevolent|kind|cruel|angular
futile|useless|effective|frozen
feasible|practicable|impossible|salty
genuine|authentic|fake|vertical
hazardous|dangerous|safe|woolen
impartial|neutral|biased|floral
intricate|complex|simple|sudden
lenient|merciful|harsh|cubic
malicious|spiteful|kind|hollow
novice|beginner|expert|golden
opaque|not transparent|clear|sweet
permanent|lasting|temporary|narrow
resolute|determined|wavering|dusty
subtle|slight|obvious|cubic
tedious|boring|engaging|ripe
tranquil|calm|stormy|bitter
vivid|bright|dull|legal
weary|tired|energetic|formal
yield|surrender|resist|polite
conceal|hide|reveal|spicy
compel|force|invite|silky
deter|discourage|encourage|cubic
eminent|prominent|unknown|liquid
expand|enlarge|shrink|sleepy
feeble|weak|strong|square
gloomy|dreary|cheerful|metallic
hasten|hurry|delay|floral
imitate|copy|invent|frozen
jeopardy|danger|safety|round
keen|eager|reluctant|dusty
linger|stay|leave|legal
meager|scanty|ample|formal
nimble|agile|clumsy|bitter
obstinate|stubborn|flexible|spicy
plausible|believable|absurd|silky
quaint|charmingly old|modern|numeric
rash|reckless|careful|angular
serene|peaceful|agitated|hollow
thrifty|frugal|wasteful|sudden
undermine|weaken|support|golden
verbose|wordy|concise|narrow
wary|cautious|careless|ripe
yearn|long|reject|square
zealous|enthusiastic|indifferent|dusty
abate|lessen|intensify|floral
baffle|confuse|clarify|metallic
candidly|frankly|falsely|frozen
deplete|exhaust|replenish|legal
elated|joyful|miserable|formal
forfeit|surrender|keep|bitter
grave|serious|playful|spicy
hamper|hinder|help|silky
inert|motionless|active|numeric
jovial|cheerful|sullen|angular
kinetic|related to motion|static|hollow
lax|slack|strict|sudden
morbid|gruesome|pleasant|golden
notable|remarkable|ordinary|narrow
omit|leave out|include|ripe
pious|devout|irreverent|square
quandary|dilemma|certainty|dusty
refute|disprove|confirm|floral
skeptical|doubtful|convinced|metallic
tardy|late|prompt|frozen
ultimate|final|initial|legal
vain|conceited|modest|formal
wholesome|healthy|harmful|bitter
""".strip().splitlines()


def word_knowledge(limit: int) -> list[Item]:
    out: list[Item] = []
    seen: set[str] = set()
    rows = [line.split("|") for line in WK_ROWS]
    for row_index, (word, synonym, opposite, unrelated) in enumerate(rows):
        stem = word.upper()
        nearby = []
        for distance in range(1, len(rows)):
            for candidate_index in (row_index - distance, row_index + distance):
                if 0 <= candidate_index < len(rows):
                    candidate_synonym = rows[candidate_index][1]
                    if candidate_synonym not in (word, synonym, opposite, unrelated) and candidate_synonym not in nearby:
                        nearby.append(candidate_synonym)
            if len(nearby) >= 3:
                break
        local_rng = rng_for(stem + "|word-distractors")
        local_rng.shuffle(nearby)
        built = [
            (opposite, f"{opposite} expressa o contrário ou uma direção semântica incompatível."),
            (unrelated, f"{unrelated} não é equivalente a {word}."),
        ]
        built.extend(
            (candidate, f"{candidate} pode parecer plausível no formato, mas não significa {word}.")
            for candidate in nearby[:2]
        )
        add(out, Item(
            "word-knowledge", "synonym", "single-word", "intermediate", stem,
            choose(stem, synonym, built),
            f"{word} está mais próximo de {synonym}. {opposite} não é esse sentido.",
            "A alternativa correta é o sinônimo combinado na montagem do item, e as outras foram escolhidas fora desse sentido.",
            "original-lexicon", f"synonym of {word}", 12, ["synonym"], "approved_relation", "text", synonym,
            glossary=[[word, f"Procure o equivalente mais próximo. O contrário próximo neste item é {opposite}."]],
        ), seen)
        if len(out) >= limit:
            break
    return out[:limit]


def reading(limit: int) -> list[Item]:
    out: list[Item] = []
    seen: set[str] = set()
    names = ["Lopez", "Nguyen", "Carter", "Ibrahim", "Silva", "Patel", "Brooks", "Okada"]
    tasks = ["inventory", "runway inspection", "radio check", "weather brief", "fuel sample", "tool audit"]
    for index in range(40):
        name = names[index % len(names)]
        task = tasks[index % len(tasks)]
        gallons = 12 + 3 * (index % 8)
        minutes = 15 * ((index % 4) + 2)
        errors = index % 5
        purpose = f"Lieutenant {name} was assigned to finish the {task} before the afternoon launch."
        passage = (
            f"{purpose} The log showed {gallons} gallons uploaded and a planned ground time of {minutes} minutes. "
            f"The lieutenant found {errors} recording errors and corrected them before signing the form. "
            f"The purpose of the afternoon was the launch, not a change to the aircraft's home station."
        )
        specs = [
            (f"How many gallons were uploaded?", f"{gallons} gallons", f"{gallons} gallons uploaded", "number-in-passage"),
            (f"How long was the planned ground time?", f"{minutes} minutes", f"ground time of {minutes} minutes", "number-in-passage"),
            (f"How many recording errors were corrected?", str(errors), f"found {errors} recording errors", "number-in-passage"),
            ("What was the lieutenant assigned to finish?", f"the {task}", f"finish the {task}", "phrase-in-passage"),
        ]
        for question, correct, span, subtopic in specs:
            stem = passage + "\n\n" + question
            if question.startswith("How many gallons"):
                candidates = [gallons - 6, gallons - 3, gallons + 3, gallons + 6]
                filtered = [
                    (f"{value} gallons", "É uma quantidade próxima, mas não é a registrada no texto.")
                    for value in candidates if value > 0
                ]
            elif question.startswith("How long"):
                candidates = [minutes - 15, minutes + 15, minutes + 30, max(5, minutes - 10)]
                filtered = [
                    (f"{value} minutes", "É um intervalo plausível, mas não é o tempo informado.")
                    for value in candidates if value > 0
                ]
            elif question.startswith("How many recording"):
                candidates = [value for value in range(0, 7) if value != errors]
                rng_for(stem + "|reading-counts").shuffle(candidates)
                filtered = [
                    (str(value), "É uma contagem próxima, mas não é a registrada na passagem.")
                    for value in candidates[:4]
                ]
            else:
                other_tasks = [candidate for candidate in tasks if candidate != task]
                rng_for(stem + "|reading-tasks").shuffle(other_tasks)
                filtered = [
                    (f"the {candidate}", "É uma tarefa do mesmo contexto, mas não a atribuída ao tenente.")
                    for candidate in other_tasks[:4]
                ]
            add(out, Item(
                "reading-comprehension", "explicit-detail", subtopic, "basic", stem,
                choose(stem, correct, filtered),
                f"A resposta está dita na passagem: {span}.",
                "O trecho correspondente foi localizado de novo no enunciado.",
                "pearson-vue-afoqt", "explicit detail from an original passage", 58,
                ["reading", "explicit"], "approved_calculation", "span", span,
            ), seen)
            if len(out) >= limit:
                return out[:limit]
    return out[:limit]


SJT = [
    ("A teammate skips a required checklist to save ten minutes. No one is watching.",
     "Stop the work and complete the checklist before continuing.",
     [("Finish the shortcut and mention it only if someone asks.", "Esconde um desvio conhecido."),
      ("Criticize the teammate in the group chat.", "Ataca a pessoa em vez de corrigir o ato."),
      ("Leave, so the delay is not associated with you.", "Abandona a responsabilidade."),
      ("Change the checklist after the fact so it matches what was skipped.", "Falsifica o registro.")],
     "Integridade e segurança vêm antes dos dez minutos. O checklist existe para ser cumprido."),
    ("You disagree with a peer's plan, and the briefing starts in five minutes.",
     "State the specific risk and one alternative during the briefing.",
     [("Stay silent to keep the mood pleasant.", "Omite um risco que você já vê."),
      ("Wait until after the mission and say you knew it would fail.", "Guarda a crítica para depois, quando não ajuda."),
      ("Announce that the peer is unqualified.", "Ataca a pessoa, não o plano."),
      ("Implement your own plan without telling anyone.", "Quebra a coordenação.")],
     "O julgamento útil entra no momento em que o plano ainda pode ser ajustado, com um fato e uma alternativa."),
    ("A subordinate asks you to overlook a repeated late arrival.",
     "Hear the cause, restate the standard, and set a specific next step.",
     [("Ignore it because the person is popular.", "O padrão passa a depender de simpatia."),
      ("Announce the punishment before hearing any fact.", "Pula a apuração."),
      ("Change the standard for the whole team without authority.", "Altera a regra por conta própria."),
      ("Tell the person to hide the lateness from the next supervisor.", "Ensina a ocultar o fato.")],
     "Ouvir não é o mesmo que abrir mão do padrão. O passo seguinte precisa ser concreto."),
    ("Two agencies give you conflicting instructions for the same task.",
     "Identify the conflict, pause the affected step, and ask the authority who can resolve it.",
     [("Follow the instruction you personally prefer.", "Escolhe no gosto, não na autoridade."),
      ("Do both at once even where they contradict.", "Executa duas ordens incompatíveis."),
      ("Tell each agency that the other already approved your choice.", "Inventa uma aprovação."),
      ("Wait indefinitely without telling either side.", "A demora sem aviso também é uma decisão.")],
     "Conflito de instrução pede pausa do passo afetado e escalada a quem pode decidir."),
    ("You notice a safety discrepancy five minutes before a scheduled start.",
     "Hold the start and correct or formally accept the discrepancy through the proper process.",
     [("Start on time and write the discrepancy afterward.", "O registro posterior não desfaz a exposição."),
      ("Ask a trainee to stand where the hazard is less visible.", "Esconde o perigo."),
      ("Tell the team the discrepancy is normal without checking.", "Inventa uma normalidade."),
      ("Leave the decision unsigned and depart.", "Sai do posto no momento da decisão.")],
     "Segurança atrasa o início quando o processo não autoriza seguir com a discrepância."),
    ("A peer takes credit for your section's work in front of a supervisor.",
     "Correct the record calmly, naming the team's actual contribution.",
     [("Say nothing and retaliate on the next project.", "Troca o fato por vingança."),
      ("Accuse the peer of fraud with no details.", "Sobe o tom sem o fato."),
      ("Email the whole base a complaint.", "Espalha o conflito para fora de quem decide."),
      ("Alter the peer's report that night.", "Mexe no documento às escondidas.")],
     "O registro pode ser corrigido com o fato e sem humilhar."),
    ("Your team is tired and a noncritical task can move to tomorrow without breaking a rule.",
     "Finish the required safety items and schedule the noncritical task.",
     [("Cancel the safety items because people are tired.", "Cansaço não apaga item de segurança."),
      ("Order an all-night session for pride.", "Gasta a equipe sem necessidade operacional."),
      ("Pretend the noncritical task is already done.", "Registra um fato falso."),
      ("Let each person decide alone whether safety items are optional.", "O padrão deixa de ser comum.")],
     "Separar o obrigatório do adiável é gestão de recurso, não relaxamento do padrão."),
    ("A new member does not understand a task you assigned.",
     "Demonstrate the standard, watch one repetition, and invite questions.",
     [("Repeat the order more loudly and leave.", "Volume não ensina o procedimento."),
      ("Do the task yourself and tell them they failed.", "Não desenvolve a pessoa."),
      ("Assign the task to someone else and never return to it.", "Empurra a lacuna para a frente."),
      ("Tell them to copy another unit's unofficial shortcut.", "Substitui o padrão por um atalho.")],
     "Instrução curta, uma repetição observada e espaço para pergunta corrigem a lacuna."),
]


def situational(limit: int) -> list[Item]:
    out: list[Item] = []
    seen: set[str] = set()
    for stem_body, best, wrongs, why in SJT:
        stem = (
            "Training item, not an official USAF key. Choose the most effective response. "
            + stem_body
        )
        add(out, Item(
            "situational-judgment", "interpersonal", "most-effective", "advanced", stem,
            choose(stem, best, wrongs),
            why + " Esta escolha segue a rubrica de treino: segurança, integridade, respeito e clareza. Não é o gabarito oficial do teste.",
            "A resposta marcada é a que a rubrica local classifica como mais efetiva. Ela não representa o consenso oficial de oficiais da USAF.",
            "afdp-1-1", "training rubric only: safety, integrity, respect, clarity", 131,
            ["judgment", "training-rubric"], "training_rubric", "text", best,
        ), seen)
        if len(out) >= limit:
            break
    return out[:limit]


SDI = [
    "I keep working on a task until it is finished.",
    "I prefer a plan written down before I start.",
    "I speak up when a procedure looks unsafe.",
    "I enjoy learning a skill that I am not yet good at.",
    "I would rather work with a team than alone.",
    "I get restless when a meeting has no agenda.",
    "I check my work a second time before I turn it in.",
    "I adapt quickly when the schedule changes.",
    "I ask for help before a small problem grows.",
    "I like competing against my own previous result.",
    "I stay calm when several people talk at once.",
    "I take responsibility when my part of a task fails.",
    "I prefer detailed instructions to a vague goal.",
    "I can wait without becoming rude.",
    "I like explaining a process to a new person.",
    "I notice small errors in written records.",
]


def self_description() -> list[Item]:
    out = []
    options = [
        ("A. Strongly disagree", False, "Não há alternativa correta."),
        ("B. Disagree", False, "Não há alternativa correta."),
        ("C. Neither agree nor disagree", False, "Não há alternativa correta."),
        ("D. Agree", False, "Não há alternativa correta."),
        ("E. Strongly agree", False, "Não há alternativa correta."),
    ]
    for index, statement in enumerate(SDI, start=1):
        stem = (
            "Familiarization only. There is no right or wrong answer, and this item is not scored. "
            "Do not use it to rehearse a personality profile. How well does this statement describe you? "
            + statement
        )
        out.append(Item(
            "self-description", "familiarization", "likert", "basic", stem, options,
            "O inventário oficial não é corrigido como prova de conhecimento. Este item só mostra o formato.",
            "Não existe resposta certa.",
            "pearson-vue-afoqt", "unscored self-description format", 11,
            ["unscored"], "familiarization_unscored", "", "", scored=0,
        ))
    return out


TOPICS = [
    ("rate-time-distance", "arithmetic-reasoning", "Distância, velocidade e tempo", "Aplicar distância = velocidade × tempo, inclusive com escala de mapa.", "básico a intermediário", "openstax-prealgebra", "Pearson descreve time-distance em Arithmetic Reasoning."),
    ("money", "arithmetic-reasoning", "Dinheiro e quantidades iguais", "Montar uma equação curta com dois preços.", "intermediário", "openstax-prealgebra", "Pearson cita proporções, razões e misturas."),
    ("percent", "arithmetic-reasoning", "Porcentagem", "Achar uma parte de um total.", "básico", "openstax-prealgebra", "Pearson cita percentages."),
    ("geometry", "arithmetic-reasoning", "Volume do prisma", "Multiplicar as três dimensões de um recipiente.", "básico", "openstax-prealgebra", "Geometria aplicada. A Pearson descreve problemas de raciocínio, sem listar esta fórmula."),
    ("averages", "arithmetic-reasoning", "Média aritmética", "Somar três valores e dividir por três.", "básico", "openstax-prealgebra", "Raciocínio aritmético complementar. Não há lista oficial de tipos de média."),
    ("algebra", "math-knowledge", "Álgebra", "Fatorar e resolver sistemas lineares.", "intermediário a avançado", "openstax-intermediate,openstax-college", "Pearson cita álgebra, expressões e sistemas."),
    ("arithmetic", "math-knowledge", "Frações e raízes", "Operar fração com raiz quadrada.", "intermediário", "openstax-prealgebra", "Pearson cita aritmética dentro de Math Knowledge."),
    ("grid-lookup", "table-reading", "Cruzamento de eixos", "Ler X como coluna e Y como linha sob limite de tempo.", "básico", "pearson-vue-afoqt", "Pearson descreve leitura de um gráfico simples de eixos."),
    ("concepts", "physical-science", "Conceitos de ciência física", "Distinguir grandeza, unidade e máquina simples.", "básico", "openstax-physics", "Pearson cita leis físicas, relações de força e máquinas simples."),
    ("mechanics", "physical-science", "Leis de Newton", "Calcular força resultante.", "básico", "openstax-physics", "Relação de força descrita pela Pearson."),
    ("energy", "physical-science", "Trabalho e energia", "Calcular trabalho mecânico.", "intermediário", "openstax-physics", "Conteúdo complementar de ciência física, não uma lista oficial de fórmulas."),
    ("electricity", "physical-science", "Eletricidade", "Aplicar a lei de Ohm.", "intermediário", "openstax-physics", "Conteúdo complementar alinhado a ciência física do ensino médio."),
    ("matter", "physical-science", "Densidade", "Dividir massa por volume.", "básico", "openstax-physics", "Conteúdo complementar de ciência física."),
    ("fluids", "physical-science", "Pressão", "Dividir força por área.", "intermediário", "openstax-physics", "Conteúdo complementar de ciência física."),
    ("attitude-and-heading", "instrument-comprehension", "Atitude e rumo", "Ler arfagem, inclinação e rumo sem trocar os eixos.", "intermediário", "faa-ifh,faa-afh", "Pearson descreve indicadores de atitude e bússola. A convenção gráfica usada aqui é a de treinamento FAA, não uma prancha oficial do teste."),
    ("face-adjacency", "block-counting", "Contato de faces", "Contar cubos que compartilham uma face inteira.", "intermediário", "pearson-vue-afoqt", "Pearson descreve a contagem de blocos ao redor de um bloco. As figuras são originais."),
    ("core-flight", "aviation-information", "Mecânica de voo e aeroporto", "Reconhecer forças, ângulos, luzes e instrumentos básicos.", "básico", "faa-phak", "Pearson cita mecânica de voo, aeronaves e normas de aeroporto. O detalhe técnico vem dos manuais FAA, não de um item oficial."),
    ("weight-balance", "aviation-information", "Peso e balanceamento", "Calcular o CG a partir de pesos e braços.", "intermediário", "faa-phak", "Assunto do capítulo de weight and balance do PHAK. Não há lista oficial de fórmulas do subteste."),
    ("performance", "aviation-information", "Desempenho simples", "Autonomia e componente de vento.", "básico a avançado", "faa-phak,faa-afh", "Aplicação de conceitos dos manuais FAA."),
    ("antonym", "verbal-analogies", "Antônimos", "Completar um par com a mesma oposição.", "básico", "original-lexicon", "Pearson descreve relações entre palavras, como comparação."),
    ("synonym", "verbal-analogies", "Sinônimos", "Completar um par de equivalentes.", "básico", "original-lexicon", "Pearson descreve o uso de palavras para estabelecer relações."),
    ("part-whole", "verbal-analogies", "Parte e todo", "Ver a relação de peça e conjunto.", "intermediário", "original-lexicon", "Tipo clássico de analogia, não uma lista oficial de pares."),
    ("function", "verbal-analogies", "Função", "Ligar um objeto ao que ele faz.", "intermediário", "original-lexicon", "Tipo clássico de analogia."),
    ("degree", "verbal-analogies", "Grau", "Reconhecer intensificação.", "intermediário", "original-lexicon", "Tipo clássico de analogia."),
    ("sequence", "verbal-analogies", "Sequência", "Reconhecer a etapa seguinte.", "intermediário", "original-lexicon", "Pearson cita relações de tempo."),
    ("single-word", "word-knowledge", "Sinônimo de uma palavra", "Escolher o equivalente mais próximo.", "intermediário", "original-lexicon", "Pearson diz que o subteste pede um sinônimo."),
    ("explicit-detail", "reading-comprehension", "Detalhe explícito", "Localizar um fato dito na passagem.", "básico", "pearson-vue-afoqt", "Pearson descreve leitura e compreensão, inclusive sentido implícito. Este lote cobre o detalhe explícito; inferência mais aberta ficou de fora por não ser verificável automaticamente."),
    ("most-effective", "situational-judgment", "Resposta mais efetiva", "Escolher a ação mais alinhada à rubrica de treino.", "avançado", "afdp-1-1,afdp-1", "Pearson diz que o subteste mede resposta a problemas interpessoais e liderança. A rubrica local não é o gabarito oficial."),
    ("likert", "self-description", "Familiarização", "Ver o formato de concordância, sem correção.", "básico", "pearson-vue-afoqt", "Pearson informa que o inventário não é graduado."),
]


def validate(item: Item) -> tuple[bool, str]:
    notes = []
    correct = [text for text, flag, _ in item.options if flag]
    if len(correct) != 1 and item.scored:
        return False, "não há exatamente uma alternativa correta"
    if len(item.options) != 5:
        return False, "o item não tem exatamente cinco alternativas"
    texts = [text for text, _, _ in item.options]
    if len(texts) != len(set(texts)):
        return False, "alternativa repetida"
    forbidden = {"none of these results", "not enough information", "an undefined value", "a reversed reading"}
    if forbidden.intersection(texts):
        return False, "distrator genérico proibido"
    if item.check_kind == "number":
        if correct[0].split()[0] != item.check_value and correct[0] != item.check_value:
            return False, f"número {correct[0]} diferente de {item.check_value}"
        again = recompute_number(item.stem)
        if again is None:
            return False, "conta sem segunda verificação"
        if again != item.check_value:
            return False, f"segunda conta deu {again}, não {item.check_value}"
        notes.append("número recalculado pelo enunciado")
    elif item.check_kind == "text":
        if correct[0] != item.check_value:
            return False, "texto correto não confere"
        notes.append("texto conferido")
    elif item.check_kind == "span":
        if item.check_value.lower() not in item.stem.lower():
            return False, "o fato não está na passagem"
        notes.append("trecho localizado")
    elif item.status == "training_rubric":
        notes.append("rubrica de treino, não gabarito oficial")
    elif item.status == "familiarization_unscored":
        notes.append("sem correção")
    else:
        return False, "tipo de verificação ausente"
    return True, "; ".join(notes)


def write_db(items: list[Item]) -> dict:
    if DB_PATH.exists():
        DB_PATH.unlink()
    EXPORT.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    for source in SOURCES:
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [source[key] for key in (
                "source_key", "institution", "title", "url", "published", "updated",
                "accessed", "doc_type", "license_notes", "relevant", "verification", "role",
            )],
        )
    for row in TOPICS:
        conn.execute("INSERT INTO topics VALUES (?,?,?,?,?,?,?)", row)
    source_urls = {source["source_key"]: source["url"] for source in SOURCES}
    counts: dict[str, int] = {}
    rejected = []
    kept = []
    for item in items:
        counts[item.subtest] = counts.get(item.subtest, 0) + 1
        number = counts[item.subtest]
        question_id = f"{item.subtest[:2]}-{number:04d}"
        passed, note = validate(item)
        if not passed:
            rejected.append((question_id, note, item.stem[:80]))
            continue
        conn.execute(
            "INSERT INTO questions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                question_id, item.subtest, item.topic, item.subtopic, item.difficulty,
                item.stem, item.explanation, item.why_correct, item.concept,
                item.source_key, source_urls[item.source_key], item.seconds,
                ",".join(item.tags), item.figure, item.status, item.check_kind,
                item.check_value, item.scored,
            ),
        )
        for position, (text, flag, why) in enumerate(item.options):
            conn.execute(
                "INSERT INTO options VALUES (?,?,?,?,?,?)",
                (question_id, position, "ABCDE"[position], text, int(flag), why),
            )
        for word, meaning in item.glossary:
            conn.execute("INSERT INTO glossary VALUES (?,?,?)", (question_id, word, meaning))
        conn.execute(
            "INSERT INTO validation_results VALUES (?,?,?)",
            (question_id, 1, note),
        )
        kept.append(item)
    blueprints = {
        "full": {
            "name": "Simulado completo no formato publicado em 2026",
            "description": "Doze seções na ordem da Pearson VUE, com os tempos publicados. O intervalo de 15 minutos pode ser pulado no treino.",
            "sections": [
                ["verbal-analogies", 25, 8], ["arithmetic-reasoning", 25, 29],
                ["word-knowledge", 25, 5], ["math-knowledge", 25, 22],
                ["reading-comprehension", 25, 24], ["situational-judgment", 16, 35],
                ["break", 0, 15], ["self-description", 16, 45],
                ["physical-science", 20, 10], ["table-reading", 40, 7],
                ["instrument-comprehension", 25, 5], ["block-counting", 30, 5],
                ["aviation-information", 20, 8],
            ],
        },
        "verbal": {"name": "Área verbal", "description": "Analogias, vocabulário e leitura.", "sections": [["verbal-analogies", 25, 8], ["word-knowledge", 25, 5], ["reading-comprehension", 25, 24]]},
        "quantitative": {"name": "Área quantitativa", "description": "Raciocínio aritmético e conhecimento de matemática. O destacamento AFROTC descreve o composto quantitativo com esses dois subtestes.", "sections": [["arithmetic-reasoning", 25, 29], ["math-knowledge", 25, 22]]},
        "aviation": {"name": "Aviação", "description": "Informação de aviação e leitura de instrumentos no modelo de treino.", "sections": [["aviation-information", 20, 8], ["instrument-comprehension", 25, 5]]},
        "science": {"name": "Ciência física", "description": "Somente Physical Science.", "sections": [["physical-science", 20, 10]]},
        "spatial": {"name": "Raciocínio espacial e tabela", "description": "Tabela, instrumentos e blocos.", "sections": [["table-reading", 40, 7], ["instrument-comprehension", 25, 5], ["block-counting", 30, 5]]},
        "judgment": {"name": "Julgamento situacional", "description": "Rubrica de treino. Não produz percentil nem gabarito oficial.", "sections": [["situational-judgment", 16, 35]]},
        "cyber-track": {
            "name": "Trilha de comissionamento com ênfase verbal e quantitativa",
            "description": "Não é uma prova de Cyber Knowledge. O DAFMAN trata esse teste à parte. A trilha treina os mínimos publicados de Verbal e Quantitative e aumenta a dificuldade se o acerto passar de 80%.",
            "sections": [["verbal-analogies", 25, 8], ["word-knowledge", 25, 5], ["reading-comprehension", 15, 15], ["arithmetic-reasoning", 25, 29], ["math-knowledge", 25, 22]],
        },
    }
    for key, blueprint in blueprints.items():
        conn.execute(
            "INSERT INTO exam_blueprints VALUES (?,?,?,?)",
            (key, blueprint["name"], blueprint["description"], json.dumps(blueprint["sections"])),
        )
    conn.commit()
    export_public(conn, blueprints)
    summary = {
        "kept": conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0],
        "scored": conn.execute("SELECT COUNT(*) FROM questions WHERE scored = 1").fetchone()[0],
        "by_subtest": conn.execute(
            "SELECT subtest, COUNT(*), SUM(scored) FROM questions GROUP BY subtest ORDER BY subtest"
        ).fetchall(),
        "by_status": conn.execute(
            "SELECT validation_status, COUNT(*) FROM questions GROUP BY validation_status"
        ).fetchall(),
        "rejected": rejected,
    }
    conn.close()
    return summary


def export_public(conn: sqlite3.Connection, blueprints: dict) -> None:
    rows = conn.execute(
        """
        SELECT q.question_id, q.subtest, q.topic, q.subtopic, q.difficulty, q.stem,
               q.explanation_pt, q.why_correct_pt, q.concept_ref, q.source_key, q.source_url,
               q.estimated_seconds, q.tags, q.figure_svg, q.validation_status, q.scored
        FROM questions q ORDER BY q.question_id
        """
    ).fetchall()
    payload = []
    csv_rows = []
    for row in rows:
        options = conn.execute(
            "SELECT label, text, is_correct, why_wrong_pt FROM options WHERE question_id = ? ORDER BY position",
            (row[0],),
        ).fetchall()
        glossary = conn.execute(
            "SELECT word, meaning_pt FROM glossary WHERE question_id = ?",
            (row[0],),
        ).fetchall()
        payload.append({
            "id": row[0],
            "subtest": row[1],
            "topic": row[2],
            "subtopic": row[3],
            "difficulty": row[4],
            "stem": row[5],
            "explanation": row[6],
            "whyCorrect": row[7],
            "concept": row[8],
            "source": row[9],
            "sourceUrl": row[10],
            "seconds": row[11],
            "tags": row[12].split(","),
            "figure": row[13] or "",
            "status": row[14],
            "scored": bool(row[15]),
            "options": [
                {"label": label, "text": text, "correct": bool(flag), "whyWrong": why}
                for label, text, flag, why in options
            ],
            "glossary": [{"word": word, "meaning": meaning} for word, meaning in glossary],
        })
        csv_rows.append({
            "id": row[0], "subtest": row[1], "topic": row[2], "difficulty": row[4],
            "stem": row[5], "correct": next(text for _, text, flag, _ in options if flag) if row[15] else "",
            "status": row[14], "source": row[9],
        })
    (EXPORT / "questions.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (EXPORT / "blueprints.json").write_text(json.dumps(blueprints, ensure_ascii=False, indent=2), encoding="utf-8")
    with (EXPORT / "questions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)
    manifest = {
        "generated": ACCESSED,
        "questionCount": len(payload),
        "scoredCount": sum(1 for item in payload if item["scored"]),
        "disclaimer": "Treino original. Não é endossado pela USAF e não produz percentil oficial.",
    }
    (EXPORT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def write_quality(summary: dict) -> None:
    lines = [
        "# Relatório 4 — Qualidade",
        "",
        f"Data da geração: {ACCESSED}.",
        "",
        f"Questões gravadas: {summary['kept']}.",
        f"Questões pontuáveis: {summary['scored']}.",
        f"Questões rejeitadas na validação: {len(summary['rejected'])}.",
        "",
        "## Por subteste",
        "",
        "| Subteste | Itens | Pontuáveis |",
        "|---|---:|---:|",
    ]
    for subtest, count, scored in summary["by_subtest"]:
        lines.append(f"| {subtest} | {count} | {scored} |")
    lines += ["", "## Status", ""]
    for status, count in summary["by_status"]:
        lines.append(f"- {status}: {count}")
    lines += [
        "",
        "## O que a validação fez",
        "",
        "- Impediu enunciado repetido.",
        "- Exigiu uma alternativa correta nos itens pontuáveis.",
        "- Exigiu exatamente cinco alternativas distintas em cada item.",
        "- Rejeitou preenchimentos genéricos como “none of these results” e “not enough information”.",
        "- Gerou os distratores numéricos que faltavam perto do resultado, preservando a unidade.",
        "- Variou os distratores verbais pela relação ou pelo campo lexical de cada enunciado.",
        "- Recalculou o número a partir do enunciado, por outra leitura da mesma fórmula, e rejeitou divergências.",
        "- Conferiu se o fato cobrado na leitura aparece na passagem.",
        "- Embaralhou a posição da alternativa correta com semente estável do enunciado.",
        "- Manteve julgamento situacional fora do status de gabarito oficial.",
        "- Manteve o inventário de autodescrição sem pontuação.",
        "",
        "## Lacunas",
        "",
        "- Word Knowledge e Situational Judgment ficaram abaixo da meta inicial de 700 e 300 porque não foram inflados com paráfrases quase iguais.",
        "- Reading Comprehension deste lote cobra detalhe explícito. Inferência aberta não entrou, porque a checagem automática não a comprovaria.",
        "- A fórmula exata de cada composto, subteste por subteste, não está no trecho utilizável do DAFMAN 36-2664. O simulado não converte acerto em percentil.",
        "- A página da NASA Glenn não pôde ser lida nesta sessão e não sustenta nenhum item.",
        "- Nenhuma questão foi marcada como oficial ou endossada pela USAF.",
        "- A primeira geração válida tinha 3.589 pontuáveis. O acréscimo até a meta veio de famílias numéricas e espaciais com segunda conta, não de paráfrases verbais.",
        "",
        "## Meta sugerida e lote entregue",
        "",
        "| Subteste | Meta sugerida | Pontuáveis neste lote |",
        "|---|---:|---:|",
    ]
    targets = {
        "verbal-analogies": 550,
        "arithmetic-reasoning": 600,
        "word-knowledge": 700,
        "math-knowledge": 600,
        "reading-comprehension": 550,
        "situational-judgment": 300,
        "physical-science": 400,
        "table-reading": 350,
        "instrument-comprehension": 350,
        "block-counting": 350,
        "aviation-information": 500,
    }
    scored_by = {subtest: scored for subtest, _count, scored in summary["by_subtest"]}
    for subtest, target in targets.items():
        lines.append(f"| {subtest} | {target} | {scored_by.get(subtest, 0)} |")
    lines.append("")
    if summary["rejected"]:
        lines.append("## Rejeitadas")
        lines.append("")
        for question_id, note, stem in summary["rejected"][:30]:
            lines.append(f"- {question_id}: {note} — {stem}")
    (REPORTS / "04-qualidade.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    seen_guard: list[Item] = []
    seen_guard.extend(arithmetic(1300))
    seen_guard.extend(math_knowledge(1050))
    seen_guard.extend(table_reading(750))
    seen_guard.extend(science(600))
    seen_guard.extend(instruments(400))
    seen_guard.extend(blocks(600))
    seen_guard.extend(aviation(520))
    seen_guard.extend(analogies(550))
    seen_guard.extend(word_knowledge(200))
    seen_guard.extend(reading(160))
    seen_guard.extend(situational(8))
    seen_guard.extend(self_description())
    summary = write_db(seen_guard)
    write_quality(summary)
    print(json.dumps({
        "kept": summary["kept"],
        "scored": summary["scored"],
        "rejected": len(summary["rejected"]),
        "by_subtest": summary["by_subtest"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
