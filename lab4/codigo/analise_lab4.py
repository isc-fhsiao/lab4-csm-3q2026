"""Lab 4 CSM (ESFI001, UFABC) - Grupo 3.

Lê o material do Drive em Lab4_CSM/G1..G4, mede os arquivos de áudio e imagem,
gera as versões JPEG do Lab4.3, os gráficos e o js/dados.js do site.

Uso: python3 analise_lab4.py   (na pasta que contém Lab4_CSM/)
Precisa de ffmpeg/ffprobe no PATH, numpy, scipy, matplotlib e Pillow.

As avaliações externas (formulário com áudio e imagem) ficam em
Lab4_CSM/avaliacoes_externas/, uma planilha por participante. Para incluir
novas planilhas, copie-as para lá e rode de novo.
"""
import base64
import csv
import io
import json
import re
import shutil
import subprocess
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import signal
from scipy.io import wavfile
from scipy.ndimage import gaussian_filter, sobel

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent
DRIVE = BASE / "Lab4_CSM"
SITE = BASE / "site-lab4"
GRAF = SITE / "img" / "graficos"
FS = 44100

AZUL, LARANJA, CINZA = "#1f5f8b", "#c0582b", "#6b7280"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": .3, "savefig.dpi": 130})

# As quatro pastas usam gravações do nosso Lab 3 (conferido pela duração e pelo
# número de amostras de cada WAV original, iguais aos de lab3/js/dados.js).
RODADAS = {
    # formato_lab3: formato do arquivo entregue no Lab 3 (lab3/js/dados.js)
    "G1": {"lab3": "E5", "conteudo": "canto", "formato_lab3": "MP3",
           "descricao": "E5: trio vocal captado pelo C214 a 1 m"},
    "G2": {"lab3": "E1", "conteudo": "fala", "formato_lab3": "MP3",
           "descricao": "E1: fala com o SM57 a 15 cm"},
    "G3": {"lab3": "E3", "conteudo": "fala", "formato_lab3": "WAV PCM 16 bits",
           "descricao": "E3: fala a 180 graus (canal L: SM57, canal R: PK81)"},
    "G4": {"lab3": "E2", "conteudo": "fala com ruído", "formato_lab3": "WAV PCM 16 bits",
           "descricao": "E2: fala suave com o PK81 e conversas ao fundo (só o canal L tem microfone)"},
}
CONDICOES = ["mp3_48k", "aac_48k", "vorbis_48k", "mp3_128k", "aac_128k", "vorbis_128k"]
NO_PACOTE = ["mp3_48k", "mp3_128k", "aac_48k", "vorbis_128k"]  # lista fixa do Lab4.4
EXT = {"mp3": ".mp3", "aac": ".m4a", "vorbis": ".ogg"}
NOME_COND = {"REF_OCULTA": "Referência oculta", "ANCORA": "Âncora (passa-baixas 3,5 kHz)",
             "mp3_48k": "MP3 48 kbit/s", "aac_48k": "AAC 48 kbit/s", "vorbis_48k": "Vorbis 48 kbit/s",
             "mp3_128k": "MP3 128 kbit/s", "aac_128k": "AAC 128 kbit/s", "vorbis_128k": "Vorbis 128 kbit/s"}


def ff(args):
    p = subprocess.run(args, capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors="replace")[-1500:])
    return p.stdout


def ler_audio(path):
    raw = ff(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(FS), "-"])
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def ler_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def db(x, piso=1e-12):
    return 10 * np.log10(np.maximum(x, piso))


def r(x, n=1):
    return None if x is None else round(float(x), n)


# ------------------------------------------------------------------ áudio
def atraso(ref, x, maxlag=4096):
    a, b = ref.mean(1), x.mean(1)
    n = min(len(a), len(b))
    c = signal.correlate(b[:n], a[:n], mode="full", method="fft")
    lags = signal.correlation_lags(n, n, mode="full")
    m = np.abs(lags) <= maxlag
    return int(lags[m][np.argmax(c[m])])


def alinhar(ref, x, lag):
    x = x[lag:] if lag >= 0 else np.vstack([np.zeros((-lag, 2)), x])
    n = min(len(ref), len(x))
    return ref[:n], x[:n]


# grade de 1/6 de oitava entre 100 Hz e 20 kHz para os espectros médios
FC = 1000 * 2 ** (np.arange(-20, 26) / 6)
FC = FC[(FC >= 100) & (FC <= 20000)]


def espectro_bandas(x):
    f, p = signal.welch(x, FS, nperseg=4096, axis=0)
    p = p.sum(1)
    out = []
    for fc in FC:
        m = (f >= fc * 2 ** (-1 / 12)) & (f < fc * 2 ** (1 / 12))
        out.append(p[m].mean())
    return np.array(out)


def corte(x, ref, limiar=-10, piso=-55):
    """Primeira frequência acima de 2 kHz em que a versão fica 10 dB abaixo da referência
    por pelo menos 500 Hz seguidos. Só vale onde a referência tem conteúdo (acima do piso)."""
    f, px = signal.welch(x, FS, nperseg=8192, axis=0)
    _, pr = signal.welch(ref, FS, nperseg=8192, axis=0)
    k = np.ones(9) / 9
    px, pr = np.convolve(px.sum(1), k, "same"), np.convolve(pr.sum(1), k, "same")
    rel, nivel = db(px) - db(pr), db(pr) - db(pr.max())
    passo = f[1]
    n = int(500 / passo)
    for i in np.where(f >= 2000)[0]:
        if nivel[i] < piso:
            break
        if np.all(rel[i:i + n] < limiar):
            return float(f[i])
    return None


def degrau_hf(ref):
    """Maior queda entre faixas vizinhas de 500 Hz acima de 14,5 kHz (mediana do espectro do canal L).
    Um degrau grande seguido de piso plano é o passa-baixas de um MP3 anterior."""
    f, p = signal.welch(ref[:, 0], FS, nperseg=8192)
    d = 10 * np.log10(p + 1e-30)
    ini = np.arange(14500, 21500, 500)
    niv = np.array([np.median(d[(f > a) & (f < a + 500)]) for a in ini])
    quedas = niv[:-1] - niv[1:]
    i = int(np.argmax(quedas))
    return float(quedas[i]), float(ini[i + 1])


def bytes_payload(path):
    raw = ff(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "packet=size",
              "-of", "csv=p=0", str(path)]).decode()
    return sum(int(s) for s in raw.split() if s.strip())


def analisar_rodada(g):
    pasta = DRIVE / g
    ref_path = pasta / "audio" / "referencia.wav"
    ref = ler_audio(ref_path)
    dur = len(ref) / FS
    orig = next((pasta / "originais").glob("*.wav"))
    pcm = wavfile.read(ref_path)[1]
    info = {
        "grupo": g, **RODADAS[g],
        "original": orig.name,
        "duracao_original": r(float(ff(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                       "-of", "csv=p=0", str(orig)])), 2),
        "duracao": r(dur, 2),
        "bytes_ref": ref_path.stat().st_size,
        "pico_dbfs": r(db(np.max(np.abs(ref)) ** 2), 1),
        "rms_dbfs": [r(db(np.mean(ref[:, c] ** 2)), 1) for c in (0, 1)],
        "amostras_fundo_escala": int(np.sum((pcm >= 32767) | (pcm <= -32768))),
        "pct_fundo_escala": r(100 * np.mean(np.any((pcm >= 32767) | (pcm <= -32768), axis=1)), 2),
        "degrau_hf": [r(v, 1) for v in degrau_hf(ref)],
    }
    medidas = {f"{m['codec'].lower()}_{m['kbps_nominal']}k": m for m in ler_csv(pasta / "audio" / "medidas_audio.csv")}
    bref = espectro_bandas(ref)
    versoes = {}
    for cond in CONDICOES:
        codec, taxa = cond.split("_")
        arq = pasta / "audio" / "codificados" / f"{cond}{EXT[codec]}"
        x = ler_audio(arq)
        lag = atraso(ref, x)
        a, b = alinhar(ref, x, lag)
        snr = db(np.sum(a ** 2)) - db(np.sum((a - b) ** 2))
        bx = espectro_bandas(x)
        rel = db(bx) - db(bref)
        fcorte = corte(b, a)
        nbytes = arq.stat().st_size
        payload = bytes_payload(arq)
        versoes[cond] = {
            "arquivo": arq.name, "codec": codec.upper() if codec != "vorbis" else "Vorbis",
            "kbps_nominal": int(taxa[:-1]), "bytes": nbytes,
            "kbps_csv": float(medidas[cond]["kbps_efetivo"]),
            "kbps_arquivo": r(nbytes * 8 / dur / 1000, 1),
            "kbps_audio": r(payload * 8 / dur / 1000, 1),
            "sobrecarga_bytes": nbytes - payload,
            "reducao_pct": r(100 * (1 - nbytes / info["bytes_ref"]), 1),
            "razao": r(info["bytes_ref"] / nbytes, 1),
            "atraso_amostras": lag,
            "snr_db": r(snr, 1), "corte_hz": r(fcorte, -2),
            "espectro_rel": [r(v, 1) for v in rel],
        }
    # pacote anônimo: confere cada S0n contra o gabarito (referência por igualdade,
    # âncora refazendo o mesmo filtro do notebook, codificados por correlação)
    gab = ler_csv(pasta / "audio" / "gabarito_audio_PRIVADO.csv")
    anc_ref = ler_audio_filtro(ref_path)
    pacote = []
    decod = {c: ler_audio(pasta / "audio" / "codificados" / versoes[c]["arquivo"]) for c in NO_PACOTE}
    for linha in gab:
        s = ler_audio(pasta / "pacote_audio" / linha["codigo"])
        cand = {"REF_OCULTA": ref, "ANCORA": anc_ref, **decod}
        scores = {}
        for k, v in cand.items():
            lag = atraso(v, s)
            a, b = alinhar(v, s, lag)
            scores[k] = db(np.sum(a ** 2)) - db(np.sum((a - b) ** 2))
        melhor = max(scores, key=scores.get)
        pacote.append({"codigo": linha["codigo"], "condicao": linha["condicao"],
                       "conferido": melhor == linha["condicao"],
                       "bytes": (pasta / "pacote_audio" / linha["codigo"]).stat().st_size,
                       "amostras": len(s)})
    # âncora: atenuação medida contra a referência e contra o Butterworth de 2ª ordem
    ganc = espectro_bandas(anc_ref)
    rel_anc = db(ganc) - db(bref)
    teor = -10 * np.log10(1 + (FC / 3500) ** 4)
    ancora = {"rel": [r(v, 1) for v in rel_anc], "teorico": [r(v, 1) for v in teor],
              "a7k": r(np.interp(7000, FC, rel_anc), 1), "a10k": r(np.interp(10000, FC, rel_anc), 1),
              "snr_db": r(db(np.sum(ref ** 2)) - db(np.sum((ref - anc_ref[:len(ref)]) ** 2)), 1)}
    info.update(versoes=versoes, pacote=pacote, ancora=ancora,
                espectro_ref=[r(v, 1) for v in db(bref / bref.max())])
    return info, ref, anc_ref


def ler_audio_filtro(ref_path):
    raw = ff(["ffmpeg", "-v", "error", "-i", str(ref_path), "-af", "lowpass=f=3500",
              "-c:a", "pcm_s16le", "-f", "s16le", "-ac", "2", "-ar", str(FS), "-"])
    return np.frombuffer(raw, np.int16).reshape(-1, 2) / 32768.0


EXTERNAS = DRIVE / "avaliacoes_externas"
# condições de escuta informadas pelo grupo para as sessões em que o formulário ficou sem esse campo
ESCUTA_INFORMADA = {f"P0{i}": "Headset sem fio Logitech Zone Vibe 100" for i in range(1, 6)}
PACOTE_CONDS = ["REF_OCULTA", "ANCORA", "mp3_48k", "mp3_128k", "aac_48k", "vorbis_128k"]


def ler_csv_externo(p):
    """Lê uma planilha do formulário de avaliação. Aceita também o formato exportado com
    cada linha inteira entre aspas."""
    txt = p.read_text(encoding="utf-8-sig")
    reg = list(csv.reader(io.StringIO(txt)))
    if reg and len(reg[0]) >= 16:
        return [dict(zip(reg[0], x)) for x in reg[1:] if len(x) >= 16]
    linhas = []
    for ln in txt.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        m = re.match(r'^"(.*)"\s*;?.*$', ln)
        corpo = (m.group(1) if m else ln).replace('""', '"')
        linhas.append(next(csv.reader([corpo])))
    return [dict(zip(linhas[0], x)) for x in linhas[1:] if len(x) >= 16]


def data_local(iso):
    t = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=-3)))
    return t.strftime("%Y-%m-%d")


def avaliacoes_externas():
    """Junta as planilhas das avaliações externas, numera os participantes em sequência
    (P01, P02...) e liga cada estímulo de áudio ao gabarito do pacote."""
    gabs = {g: {l["codigo"]: l["condicao"] for l in ler_csv(DRIVE / g / "audio" / "gabarito_audio_PRIVADO.csv")}
            for g in RODADAS}
    blocos = [ler_csv_externo(p) for p in EXTERNAS.glob("*.csv")]
    blocos = [b for b in blocos if b]
    blocos.sort(key=lambda b: int(re.sub(r"\D", "", b[0]["participante"]) or 0))
    participantes, audio, imagem = [], [], []
    for i, rs in enumerate(blocos, 1):
        novo, g = f"P{i:02d}", rs[0]["grupo_produtor"].strip()
        escuta = next((" ".join(x["condicoes_escuta"].split()) for x in rs if x["condicoes_escuta"].strip()), "")
        escuta = escuta or ESCUTA_INFORMADA.get(rs[0]["participante"].strip(), "")
        for x in rs:
            obs = " ".join(x["observacao"].split())
            if x["modalidade"].strip() == "audio":
                nota = x["nota_0_100"].strip()
                audio.append({"participante": novo, "grupo_produtor": g, "ordem": x["codigo_exibido"].strip(),
                              "estimulo": x["arquivo_estimulo"].strip(), "condicao": gabs[g][x["arquivo_estimulo"].strip()],
                              "nota": int(float(nota)) if nota else None, "observacao": obs})
            elif x["modalidade"].strip() == "imagem":
                imagem.append({"participante": novo, "par": x["codigo_exibido"].strip(), "q": int(x["q_ffmpeg"]),
                               "diferenca": int(x["diferenca_0_3"]), "original_lado": x["original_lado"].strip(),
                               "observacao": obs})
        ref = next((a["nota"] for a in audio if a["participante"] == novo and a["condicao"] == "REF_OCULTA"), None)
        participantes.append({
            "participante": novo, "grupo_produtor": g,
            "data": data_local(rs[0]["data_inicio"]), "condicoes_escuta": escuta, "ref_oculta": ref,
            "triagem": ref is not None and ref >= 90,
            "sem_nota": [a["condicao"] for a in audio if a["participante"] == novo and a["nota"] is None],
        })
    return participantes, audio, imagem


def estat(v, casas=1):
    v = [x for x in v if x is not None]
    if not v:
        return {"n": 0, "media": None, "dp": None, "min": None, "max": None}
    return {"n": len(v), "media": r(np.mean(v), casas), "dp": r(np.std(v, ddof=1), casas) if len(v) > 1 else None,
            "min": min(v), "max": max(v)}


def resumir(participantes, audio, imagem):
    res_a = {}
    for g in RODADAS:
        ps = [p for p in participantes if p["grupo_produtor"] == g]
        ok = {p["participante"] for p in ps if p["triagem"]}
        res_a[g] = {"participantes": [p["participante"] for p in ps], "triados": sorted(ok), "cond": {}}
        for c in PACOTE_CONDS:
            v = [a["nota"] for a in audio if a["grupo_produtor"] == g and a["condicao"] == c]
            vt = [a["nota"] for a in audio if a["grupo_produtor"] == g and a["condicao"] == c and a["participante"] in ok]
            res_a[g]["cond"][c] = {"todos": estat(v), "triados": estat(vt)}
    geral = {c: estat([a["nota"] for a in audio if a["condicao"] == c]) for c in PACOTE_CONDS}
    res_i = {}
    for q in (2, 20, 31):
        v = [x["diferenca"] for x in imagem if x["q"] == q]
        res_i[q] = {**estat(v, 2), "contagem": [v.count(k) for k in range(4)]}
    return res_a, geral, res_i


def salvar_consolidado(participantes, audio, imagem):
    d = SITE / "dados"
    d.mkdir(exist_ok=True)
    info = {p["participante"]: p for p in participantes}
    with open(d / "avaliacoes_externas.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["participante", "data", "pacote_audio", "modalidade", "item", "condicao_ou_q",
                     "nota_0_100", "diferenca_0_3", "observacao", "condicoes_escuta"])
        for a in audio:
            p = info[a["participante"]]
            wr.writerow([a["participante"], p["data"], a["grupo_produtor"], "audio", a["estimulo"],
                         a["condicao"], "" if a["nota"] is None else a["nota"], "", a["observacao"], p["condicoes_escuta"]])
        for x in imagem:
            p = info[x["participante"]]
            wr.writerow([x["participante"], p["data"], p["grupo_produtor"], "imagem", x["par"],
                         f"q={x['q']}", "", x["diferenca"], x["observacao"], p["condicoes_escuta"]])
    return "dados/avaliacoes_externas.csv"


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


# ------------------------------------------------------------------ imagem
def luma(rgb):
    rgb = rgb.astype(np.float64)
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def psnr(a, b):
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    return 10 * np.log10(255 ** 2 / mse)


def ssim(x, y):
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    mx, my = gaussian_filter(x, 1.5), gaussian_filter(y, 1.5)
    sxx = gaussian_filter(x * x, 1.5) - mx * mx
    syy = gaussian_filter(y * y, 1.5) - my * my
    sxy = gaussian_filter(x * y, 1.5) - mx * my
    m = ((2 * mx * my + c1) * (2 * sxy + c2)) / ((mx ** 2 + my ** 2 + c1) * (sxx + syy + c2))
    return float(m[5:-5, 5:-5].mean())


def classes_blocos(Y):
    """Classifica blocos 8x8 em uniforme (0), textura (1) ou borda (2)."""
    h, w = (Y.shape[0] // 8) * 8, (Y.shape[1] // 8) * 8
    Y = Y[:h, :w]
    gx, gy = sobel(Y, 1), sobel(Y, 0)
    blk = lambda a: a.reshape(h // 8, 8, w // 8, 8).sum((1, 3))
    std = Y.reshape(h // 8, 8, w // 8, 8).std((1, 3))
    j11, j22, j12 = blk(gx * gx), blk(gy * gy), blk(gx * gy)
    coer = np.sqrt((j11 - j22) ** 2 + 4 * j12 ** 2) / (j11 + j22 + 1e-9)
    cl = np.where(std < np.percentile(std, 33), 0, np.where(coer >= 0.5, 2, 1))
    return cl


def blocagem(Y):
    """Salto médio de luminância nas fronteiras de bloco menos o salto dentro dos blocos."""
    dx = np.abs(np.diff(Y, axis=1))
    col = np.arange(dx.shape[1])
    fronteira = dx[:, (col % 8) == 7].mean()
    dentro = dx[:, (col % 8) != 7].mean()
    return float(fronteira - dentro)


def analisar_imagens():
    zips = sorted(DRIVE.glob("imagens-*.zip"))
    destino_orig = SITE / "img" / "lab4" / "originais"
    destino_jpg = SITE / "img" / "lab4" / "jpeg"
    trabalho = DRIVE / "G2" / "imagens"
    (trabalho / "originais").mkdir(parents=True, exist_ok=True)
    (trabalho / "jpeg").mkdir(parents=True, exist_ok=True)
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            for n in zf.namelist():
                if n.lower().endswith(".png"):
                    alvo = trabalho / "originais" / Path(n).name
                    if not alvo.exists():
                        alvo.write_bytes(zf.read(n))
    # fotos soltas em Lab4_CSM/imagens/originais (zip já extraído)
    for p in sorted((DRIVE / "imagens" / "originais").glob("*.png")) if (DRIVE / "imagens" / "originais").exists() else []:
        alvo = trabalho / "originais" / p.name
        if not alvo.exists():
            shutil.copy2(p, alvo)
    originais = sorted((trabalho / "originais").glob("*.png"))
    linhas = []
    for o in originais:
        rgb0 = np.asarray(Image.open(o).convert("RGB"))
        Y0 = luma(rgb0)
        cl = classes_blocos(Y0)
        for q in (2, 20, 31):
            jpg = trabalho / "jpeg" / f"{o.stem}_q{q}.jpg"
            ff(["ffmpeg", "-y", "-loglevel", "error", "-i", str(o), "-frames:v", "1", "-q:v", str(q), str(jpg)])
            rgb = np.asarray(Image.open(jpg).convert("RGB"))
            Y = luma(rgb)
            h, w = cl.shape[0] * 8, cl.shape[1] * 8
            erro = ((Y[:h, :w] - Y0[:h, :w]) ** 2).reshape(cl.shape[0], 8, cl.shape[1], 8).mean((1, 3))
            por_classe = {}
            for k, nome in enumerate(("uniforme", "textura", "borda")):
                mse = erro[cl == k].mean()
                por_classe[nome] = r(10 * np.log10(255 ** 2 / mse), 1)
            linhas.append({
                "imagem": o.name, "q": q, "bytes_original": o.stat().st_size, "bytes_jpeg": jpg.stat().st_size,
                "reducao_pct": r(100 * (1 - jpg.stat().st_size / o.stat().st_size), 2),
                "razao_bruto": r(rgb0.size / jpg.stat().st_size, 1),
                "bpp": r(jpg.stat().st_size * 8 / (rgb0.shape[0] * rgb0.shape[1]), 2),
                "psnr": r(psnr(rgb0, rgb), 1), "ssim": r(ssim(Y0, Y), 3),
                "psnr_classes": por_classe,
                "blocagem": r(blocagem(Y) - blocagem(Y0), 2),
                "arquivo_jpeg": jpg.name,
            })
        linhas_cl = {"uniforme": int((cl == 0).sum()), "textura": int((cl == 1).sum()), "borda": int((cl == 2).sum())}
        for l in linhas[-3:]:
            l["blocos"] = linhas_cl
    # mesmo CSV do Lab4.3
    with open(trabalho / "medidas_imagem.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["grupo", "imagem", "q_ffmpeg", "bytes_original", "bytes_jpeg", "reducao_pct", "arquivo_jpeg"])
        for l in linhas:
            wr.writerow(["G2", l["imagem"], l["q"], l["bytes_original"], l["bytes_jpeg"], l["reducao_pct"], l["arquivo_jpeg"]])
    return originais, linhas


# ------------------------------------------------------------------ gráficos
def salvar(fig, nome):
    fig.tight_layout()
    fig.savefig(GRAF / nome)
    plt.close(fig)
    return f"img/graficos/{nome}"


def graf_taxas(rodadas):
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    gs = list(rodadas)
    larg = 0.8 / len(gs)
    cores = [AZUL, LARANJA, "#4c9f70", CINZA]
    for i, g in enumerate(gs):
        vals = [rodadas[g]["versoes"][c]["kbps_arquivo"] for c in CONDICOES]
        ax.bar(np.arange(6) + (i - 1.5) * larg, vals, larg, label=f"{g} ({rodadas[g]['conteudo']})", color=cores[i])
    for y in (48, 128):
        ax.axhline(y, color="k", lw=.8, ls="--")
    ax.set_xticks(range(6), [NOME_COND[c] for c in CONDICOES], rotation=15)
    ax.set_ylabel("taxa do arquivo (kbit/s)")
    ax.set_ylim(0, 175)
    ax.legend(ncol=4, fontsize=8, loc="upper left", frameon=False)
    return salvar(fig, "audio_taxas.png")


def graf_espectros(g, info):
    fig, axs = plt.subplots(1, 2, figsize=(9.6, 3.6), sharey=True)
    for ax, taxa in zip(axs, ("48k", "128k")):
        ax.axhline(0, color="k", lw=1, label="referência")
        for c, cor in zip(("mp3", "aac", "vorbis"), (AZUL, LARANJA, "#4c9f70")):
            ax.semilogx(FC, info["versoes"][f"{c}_{taxa}"]["espectro_rel"], color=cor, lw=1.6,
                        label=NOME_COND[f"{c}_{taxa}"])
        if taxa == "48k":
            ax.semilogx(FC, info["ancora"]["rel"], color=CINZA, ls="--", lw=1.4, label="âncora")
        ax.set_ylim(-60, 6)
        ax.set_xlim(100, 20000)
        ax.set_xlabel("frequência (Hz)")
        ax.set_title(f"{g}: versões a {taxa[:-1]} kbit/s", fontsize=10)
        ax.legend(fontsize=8, loc="lower left")
    axs[0].set_ylabel("nível relativo à referência (dB)")
    return salvar(fig, f"audio_espectro_{g}.png")


def graf_ancora(rodadas):
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    for g, cor in zip(rodadas, (AZUL, LARANJA, "#4c9f70", CINZA)):
        ax.semilogx(FC, rodadas[g]["ancora"]["rel"], color=cor, lw=1.4, label=f"medido, {g}")
    ax.semilogx(FC, rodadas["G1"]["ancora"]["teorico"], color="k", lw=2, ls="--",
                label="Butterworth 2ª ordem, 3,5 kHz")
    ax.plot([100, 3500, 3500, 20000], [0, 0, -60, -60], color=LARANJA, lw=1, ls=":", label="passa-baixas ideal")
    ax.set_ylim(-60, 5)
    ax.set_xlim(100, 20000)
    ax.set_xlabel("frequência (Hz)")
    ax.set_ylabel("âncora menos referência (dB)")
    ax.legend(fontsize=8, loc="lower left")
    return salvar(fig, "audio_ancora.png")


def graf_notas(audio, res_a):
    ordem = ["REF_OCULTA", "vorbis_128k", "mp3_128k", "aac_48k", "mp3_48k", "ANCORA"]
    rot = {"REF_OCULTA": "Ref. oculta", "ANCORA": "Âncora", "vorbis_128k": "Vorbis 128",
           "mp3_128k": "MP3 128", "aac_48k": "AAC 48", "mp3_48k": "MP3 48"}
    fig, axs = plt.subplots(2, 2, figsize=(9.6, 6.6), sharey=True)
    rng = np.random.default_rng(4)
    for ax, g in zip(axs.flat, RODADAS):
        vals = [res_a[g]["cond"][c]["todos"]["media"] for c in ordem]
        cores = [LARANJA if c in ("REF_OCULTA", "ANCORA") else AZUL for c in ordem]
        ax.bar(range(6), vals, color=cores, alpha=.85)
        for i, c in enumerate(ordem):
            pts = [a["nota"] for a in audio if a["grupo_produtor"] == g and a["condicao"] == c and a["nota"] is not None]
            ax.scatter(i + rng.uniform(-.18, .18, len(pts)), pts, s=14, color="k", zorder=3)
            ax.text(i, 103, f"{vals[i]:.0f}", ha="center", fontsize=9)
        ax.set_xticks(range(6), [rot[c] for c in ordem], rotation=20, fontsize=8)
        ax.set_ylim(0, 110)
        n = len(res_a[g]["participantes"])
        ax.set_title(f"Pacote {g} ({RODADAS[g]['conteudo']}): {n} participantes", fontsize=10)
    for ax in axs[:, 0]:
        ax.set_ylabel("nota (0 a 100)")
    return salvar(fig, "audio_notas.png")


def graf_notas_img(res_i):
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    cores = ["#d5dbe3", "#8fb3cf", AZUL, LARANJA]
    base = np.zeros(3)
    qs = (2, 20, 31)
    for k in range(4):
        v = np.array([res_i[q]["contagem"][k] for q in qs])
        ax.barh(range(3), v, left=base, color=cores[k], label=f"{k}", edgecolor="white")
        for i, x in enumerate(v):
            if x:
                ax.text(base[i] + x / 2, i, str(x), ha="center", va="center", fontsize=9,
                        color="white" if k >= 2 else "k")
        base += v
    ax.set_yticks(range(3), [f"q={q}\nmédia {res_i[q]['media']:.2f}".replace(".", ",") for q in qs])
    ax.set_xlabel("número de participantes")
    ax.legend(title="diferença (0 a 3)", ncol=4, fontsize=8, loc="upper center", bbox_to_anchor=(.5, 1.32), frameon=False)
    ax.grid(False)
    return salvar(fig, "img_notas.png")


def graf_reducao(rodadas, res_a, linhas_img, res_i):
    fig, axs = plt.subplots(1, 2, figsize=(9.6, 3.8))
    cores = dict(zip(RODADAS, (AZUL, LARANJA, "#4c9f70", CINZA)))
    marc = {"mp3_48k": "o", "aac_48k": "s", "mp3_128k": "o", "vorbis_128k": "^", "REF_OCULTA": "*"}
    for g in RODADAS:
        xs, ys = [], []
        for c in ["mp3_48k", "aac_48k", "mp3_128k", "vorbis_128k", "REF_OCULTA"]:
            x = 0 if c == "REF_OCULTA" else rodadas[g]["versoes"][c]["reducao_pct"]
            y = res_a[g]["cond"][c]["todos"]["media"]
            axs[0].scatter(x, y, color=cores[g], marker=marc[c], s=60 if c == "REF_OCULTA" else 30, zorder=3)
            xs.append(x); ys.append(y)
        axs[0].plot([], [], color=cores[g], marker="o", ls="", label=f"{g} ({RODADAS[g]['conteudo']})")
    axs[0].set_xlabel("redução de dados sobre o WAV (%)")
    axs[0].set_ylabel("nota média (0 a 100)")
    axs[0].set_xlim(-5, 100)
    axs[0].set_ylim(0, 105)
    axs[0].annotate("referência", (0, 100), fontsize=8, xytext=(4, 0), textcoords="offset points")
    axs[0].annotate("128 kbit/s", (91, 102), fontsize=8, ha="center")
    axs[0].annotate("48 kbit/s", (96.5, 2), fontsize=8, ha="center")
    axs[0].legend(fontsize=7, loc="lower left")
    for q in (2, 20, 31):
        red = np.mean([l["reducao_pct"] for l in linhas_img if l["q"] == q and l["imagem"].endswith("806.png")])
        axs[1].errorbar(red, res_i[q]["media"], yerr=res_i[q]["dp"], fmt="o", color=AZUL, capsize=4)
        axs[1].annotate(f"q={q}", (red, res_i[q]["media"]), xytext=(-30, 6), textcoords="offset points", fontsize=9)
    axs[1].set_xlabel("redução sobre o PNG (%), composição coletiva")
    axs[1].set_ylabel("diferença percebida média (0 a 3)")
    axs[1].set_ylim(0, 3.2)
    axs[1].set_xlim(75, 100)
    return salvar(fig, "reducao_percepcao.png")


def graf_imagens(linhas):
    fig, axs = plt.subplots(1, 2, figsize=(9.6, 3.6))
    imgs = sorted({l["imagem"] for l in linhas})
    for k, im in enumerate(imgs):
        ls = [l for l in linhas if l["imagem"] == im]
        destaque = im.endswith("806.png")
        cor = LARANJA if destaque else CINZA
        axs[0].plot([l["q"] for l in ls], [l["bytes_jpeg"] / 1024 for l in ls], "o-", color=cor,
                    lw=2 if destaque else 1, label="composição coletiva" if destaque else ("demais fotos" if k == 0 else None))
        axs[1].plot([l["bpp"] for l in ls], [l["psnr"] for l in ls], "o-", color=cor, lw=2 if destaque else 1)
        for l in ls:
            if destaque:
                axs[1].annotate(f"q={l['q']}", (l["bpp"], l["psnr"]), textcoords="offset points", xytext=(5, -10), fontsize=8)
    axs[0].set_yscale("log")
    axs[0].set_xticks([2, 20, 31])
    axs[0].set_xlabel("parâmetro -q:v do FFmpeg")
    axs[0].set_ylabel("tamanho do JPEG (KiB)")
    axs[0].legend(fontsize=8)
    axs[1].set_xlabel("bits por pixel")
    axs[1].set_ylabel("PSNR RGB (dB)")
    return salvar(fig, "img_tamanho_psnr.png")


def graf_classes(linhas):
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    nomes = ("uniforme", "textura", "borda")
    for j, q in enumerate((2, 20, 31)):
        ls = [l for l in linhas if l["q"] == q]
        vals = [np.mean([l["psnr_classes"][n] for l in ls]) for n in nomes]
        ax.bar(np.arange(3) + (j - 1) * 0.27, vals, 0.27, label=f"q={q}", color=(AZUL, LARANJA, CINZA)[j])
    ax.set_xticks(range(3), ["áreas uniformes", "texturas", "bordas"])
    ax.set_ylabel("PSNR da luminância (dB)")
    ax.set_ylim(20, None)
    ax.legend(fontsize=8)
    return salvar(fig, "img_psnr_regioes.png")


def graf_recortes(orig, regioes):
    qs = (2, 20, 31)
    jpgs = {q: np.asarray(Image.open(DRIVE / "G2" / "imagens" / "jpeg" / f"{orig.stem}_q{q}.jpg").convert("RGB")) for q in qs}
    o = np.asarray(Image.open(orig).convert("RGB"))
    fig, axs = plt.subplots(len(regioes), 4, figsize=(8.4, 2.25 * len(regioes)))
    for i, (nome, (x, y, w, h)) in enumerate(regioes.items()):
        for j, (rot, im) in enumerate([("original PNG", o)] + [(f"q={q}", jpgs[q]) for q in qs]):
            ax = axs[i, j]
            ax.imshow(im[y:y + h, x:x + w], interpolation="nearest")
            ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
            if i == 0:
                ax.set_title(rot, fontsize=10)
            if j == 0:
                ax.set_ylabel(nome, fontsize=10)
    return salvar(fig, "img_recortes.png")


def graf_mapa(orig):
    rgb = np.asarray(Image.open(orig).convert("RGB"))
    cl = classes_blocos(luma(rgb))
    cores = np.array([[31, 95, 139], [76, 159, 112], [192, 88, 43]], np.uint8)
    mapa = np.kron(cores[cl], np.ones((8, 8, 1), np.uint8))
    fig, axs = plt.subplots(1, 2, figsize=(9.6, 3.7))
    axs[0].imshow(rgb); axs[0].set_title("original", fontsize=10)
    axs[1].imshow(rgb); axs[1].imshow(mapa, alpha=.55); axs[1].set_title("classes dos blocos 8x8", fontsize=10)
    for ax in axs:
        ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    from matplotlib.patches import Patch
    axs[1].legend(handles=[Patch(color=c / 255, label=n) for c, n in zip(cores, ("uniforme", "textura", "borda"))],
                  fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(GRAF / "img_mapa_regioes.jpg", pil_kwargs={"quality": 88})
    plt.close(fig)
    return "img/graficos/img_mapa_regioes.jpg"


# ------------------------------------------------------------------ site
def copiar_audio_site(g, ref_path, anc):
    d = SITE / "audio" / g
    d.mkdir(parents=True, exist_ok=True)
    arqs = {}
    ff(["ffmpeg", "-y", "-v", "error", "-i", str(ref_path), "-c:a", "flac", str(d / "referencia.flac")])
    arqs["REF"] = f"audio/{g}/referencia.flac"
    ancora_s = next(l["codigo"] for l in ler_csv(DRIVE / g / "audio" / "gabarito_audio_PRIVADO.csv") if l["condicao"] == "ANCORA")
    ff(["ffmpeg", "-y", "-v", "error", "-i", str(DRIVE / g / "pacote_audio" / ancora_s), "-c:a", "flac", str(d / "ancora.flac")])
    arqs["ANCORA"] = f"audio/{g}/ancora.flac"
    # versões codificadas decodificadas para FLAC (sem perdas): tocam em qualquer navegador
    # e não revelam o codec pela extensão no teste cego
    for c in CONDICOES:
        codec = c.split("_")[0]
        src = DRIVE / g / "audio" / "codificados" / f"{c}{EXT[codec]}"
        ff(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-ar", str(FS), "-ac", "2", "-c:a", "flac",
            "-sample_fmt", "s16", str(d / f"{c}.flac")])
        arqs[c] = f"audio/{g}/{c}.flac"
    return arqs


def main():
    GRAF.mkdir(parents=True, exist_ok=True)
    (SITE / "js").mkdir(parents=True, exist_ok=True)
    rodadas, graficos = {}, {}
    for g in RODADAS:
        info, ref, anc = analisar_rodada(g)
        info["audio"] = copiar_audio_site(g, DRIVE / g / "audio" / "referencia.wav", anc)
        rodadas[g] = info
        graficos[f"espectro_{g}"] = graf_espectros(g, info)
        print(g, "ok", {c: (v["kbps_arquivo"], v["snr_db"], v["corte_hz"]) for c, v in info["versoes"].items()})
    graficos["taxas"] = graf_taxas(rodadas)
    graficos["ancora"] = graf_ancora(rodadas)

    participantes, aval_audio, aval_img = avaliacoes_externas()
    res_a, res_geral, res_i = resumir(participantes, aval_audio, aval_img)
    graficos["notas"] = graf_notas(aval_audio, res_a)
    graficos["notas_img"] = graf_notas_img(res_i)
    consolidado = salvar_consolidado(participantes, aval_audio, aval_img)

    originais, linhas_img = analisar_imagens()
    destaque = next(o for o in originais if o.stem.endswith("806"))
    regioes = {"parede (uniforme)": (520, 30, 64, 48), "cabelo (textura)": (165, 330, 64, 48),
               "olho da pelúcia (bordas)": (380, 215, 64, 48)}
    graficos["img_tamanho"] = graf_imagens(linhas_img)
    graficos["img_classes"] = graf_classes(linhas_img)
    graficos["img_recortes"] = graf_recortes(destaque, regioes)
    graficos["img_mapa"] = graf_mapa(destaque)
    graficos["reducao"] = graf_reducao(rodadas, res_a, linhas_img, res_i)

    # só a composição coletiva vai para o site: as demais fotos têm colegas de outras
    # turmas ao fundo, sem autorização para publicação
    d_img = SITE / "img" / "lab4"
    d_img.mkdir(parents=True, exist_ok=True)
    shutil.copy2(destaque, d_img / "coletiva.png")
    for q in (2, 20, 31):
        shutil.copy2(DRIVE / "G2" / "imagens" / "jpeg" / f"{destaque.stem}_q{q}.jpg", d_img / f"coletiva_q{q}.jpg")
    # o comparador lê pixels com canvas; com data URI funciona também abrindo via file://
    uris = {"original": "data:image/png;base64," + base64.b64encode((d_img / "coletiva.png").read_bytes()).decode()}
    for q in (2, 20, 31):
        uris[f"q{q}"] = "data:image/jpeg;base64," + base64.b64encode((d_img / f"coletiva_q{q}.jpg").read_bytes()).decode()
    (SITE / "js" / "imagens.js").write_text("window.LAB4_IMG = " + json.dumps(uris) + ";\n", encoding="utf-8")

    dados = {
        "rodadas": rodadas, "condicoes": CONDICOES, "nomes": NOME_COND,
        "fc": [r(f, 0) for f in FC],
        "participantes": participantes, "aval_audio": aval_audio, "aval_img": aval_img,
        "res_audio": res_a, "res_audio_geral": res_geral, "res_img": res_i, "consolidado": consolidado,
        "extensao_url": "https://drive.google.com/drive/folders/1Uq_4UB5OdG4508TN57uqHbkFDcuyTru-?usp=drive_link",
        "imagens": linhas_img, "imagem_destaque": destaque.name,
        "imagem_site": {"original": "img/lab4/coletiva.png",
                        "jpeg": {q: f"img/lab4/coletiva_q{q}.jpg" for q in (2, 20, 31)},
                        "largura": 640, "altura": 480},
        "regioes": regioes,
        "graficos": graficos,
    }
    js = "window.LAB4 = " + json.dumps(dados, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (SITE / "js" / "dados.js").write_text(js, encoding="utf-8")
    (SITE / "codigo").mkdir(exist_ok=True)
    shutil.copy2(Path(__file__), SITE / "codigo" / "analise_lab4.py")
    print("participantes:", [(p["participante"], p["grupo_produtor"], p["ref_oculta"], p["condicoes_escuta"][:20]) for p in participantes])
    print("audio:", {g: {c: v["todos"]["media"] for c, v in res_a[g]["cond"].items()} for g in res_a})
    print("imagem:", {q: (v["n"], v["media"], v["contagem"]) for q, v in res_i.items()})
    print("dados.js:", len(js), "bytes")


if __name__ == "__main__":
    main()
