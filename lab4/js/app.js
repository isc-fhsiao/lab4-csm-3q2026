/* Lab 4 CSM - Grupo 3. Preenche números, tabelas, textos alternativos, o gráfico de espectro,
   o teste cego e o comparador de imagem. Os valores vêm de js/dados.js (window.LAB4),
   gerado por analise_lab4.py. */
(function () {
  "use strict";
  var D = window.LAB4;
  if (!D) { return; }
  var NOMES = D.nomes;
  var RODADAS = Object.keys(D.rodadas);

  // ------------------------------------------------------------ utilidades
  function fmt(v, casas) {
    if (v === undefined || v === null || isNaN(v)) { return "?"; }
    if (casas === undefined) { casas = 1; }
    return Number(v).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
  }
  function get(caminho) {
    return caminho.split(".").reduce(function (o, k) { return o == null ? undefined : o[k]; }, D);
  }
  function el(tag, attrs, texto) {
    var e = document.createElement(tag);
    if (attrs) { Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); }); }
    if (texto !== undefined) { e.textContent = texto; }
    return e;
  }
  function media(lista, f) {
    return lista.reduce(function (a, x) { return a + f(x); }, 0) / lista.length;
  }
  function anunciar(id, texto) {
    var alvo = document.getElementById(id);
    if (!alvo) { return; }
    clearTimeout(alvo._t);
    alvo._t = setTimeout(function () { alvo.textContent = texto; }, 350);
  }
  function hz(v) { return v == null ? "sem corte mensurável" : fmt(v, 0) + " Hz"; }

  // linhas: [rótulo, valores...]; valor número => 1 casa, [número, casas], texto ou {t, cls}
  function tabela(id, cabecalho, linhas, classeLinha) {
    var t = document.getElementById(id);
    if (!t) { return; }
    Array.prototype.slice.call(t.querySelectorAll("thead, tbody")).forEach(function (n) { t.removeChild(n); });
    var thead = el("thead"), tr = el("tr");
    cabecalho.forEach(function (c) { tr.appendChild(el("th", { scope: "col" }, c)); });
    thead.appendChild(tr);
    t.appendChild(thead);
    var tb = el("tbody");
    linhas.forEach(function (l, i) {
      var r = el("tr");
      if (classeLinha && classeLinha(i)) { r.className = classeLinha(i); }
      r.appendChild(el("th", { scope: "row" }, l[0]));
      l.slice(1).forEach(function (v) {
        if (v && typeof v === "object" && !Array.isArray(v)) { r.appendChild(el("td", { "class": v.cls || "" }, v.t)); return; }
        if (typeof v === "string") { r.appendChild(el("td", null, v)); return; }
        var casas = 1, num = v;
        if (Array.isArray(v)) { num = v[0]; casas = v[1]; }
        r.appendChild(el("td", { "class": "num" }, fmt(num, casas)));
      });
      tb.appendChild(r);
    });
    t.appendChild(tb);
  }

  // ------------------------------------------------------- valores derivados
  var destaque = {};
  D.imagens.forEach(function (l) { if (l.imagem === D.imagem_destaque) { destaque[l.q] = l; } });
  D.img = { "806": destaque };
  D.media = {};
  [2, 20, 31].forEach(function (q) {
    var ls = D.imagens.filter(function (l) { return l.q === q; });
    var m = function (k) { return media(ls, function (l) { return l[k]; }); };
    D.media[q] = {
      reducao_pct: m("reducao_pct"), psnr: m("psnr"), ssim: m("ssim"), blocagem: m("blocagem"),
      bytes_jpeg: m("bytes_jpeg"), bpp: m("bpp"), razao_bruto: m("razao_bruto"),
      classes: {
        uniforme: media(ls, function (l) { return l.psnr_classes.uniforme; }),
        textura: media(ls, function (l) { return l.psnr_classes.textura; }),
        borda: media(ls, function (l) { return l.psnr_classes.borda; })
      }
    };
  });
  D.dif_psnr_806 = destaque[20].psnr - destaque[31].psnr;
  D.dif_red_media = D.media[31].reducao_pct - D.media[20].reducao_pct;
  D.dif_psnr_media = D.media[20].psnr - D.media[31].psnr;
  D.n_part = D.participantes.length;
  D.n_triados = D.participantes.filter(function (p) { return p.triagem; }).length;
  D.q31_2ou3 = D.res_img["31"].contagem[2] + D.res_img["31"].contagem[3];
  D.dif_red_2_20 = destaque[20].reducao_pct - destaque[2].reducao_pct;
  D.dif_red_20_31 = destaque[31].reducao_pct - destaque[20].reducao_pct;
  D.dif_nota_2_20 = D.res_img["20"].media - D.res_img["2"].media;
  D.dif_nota_20_31 = D.res_img["31"].media - D.res_img["20"].media;
  var ORDEM = ["REF_OCULTA", "vorbis_128k", "mp3_128k", "aac_48k", "mp3_48k", "ANCORA"];
  var NOME_CURTO = { REF_OCULTA: "Referência oculta", ANCORA: "Âncora", vorbis_128k: "Vorbis 128 kbit/s",
    mp3_128k: "MP3 128 kbit/s", aac_48k: "AAC 48 kbit/s", mp3_48k: "MP3 48 kbit/s" };

  // ---------------------------------------------------- números no texto
  document.querySelectorAll("[data-k]").forEach(function (e) {
    var v = get(e.getAttribute("data-k"));
    if (v === undefined) { return; }
    var casas = e.hasAttribute("data-d") ? parseInt(e.getAttribute("data-d"), 10) : 1;
    e.textContent = fmt(v, casas) + (e.getAttribute("data-u") || "");
  });

  // ---------------------------------------------------- tabela de gravações
  tabela("tab-gravacoes", ["Pasta", "Estação do Lab 3", "Conteúdo", "Formato no Lab 3", "Original (s)",
    "Referência (s)", "Pico (dBFS)", "RMS L e R (dBFS)", "Instantes saturados (%)", "Maior degrau acima de 14,5 kHz"],
    RODADAS.map(function (g) {
      var r = D.rodadas[g];
      return [g, r.descricao, r.conteudo, r.formato_lab3, [r.duracao_original, 2], [r.duracao, 2], [r.pico_dbfs, 1],
        { t: fmt(r.rms_dbfs[0]) + " e " + fmt(r.rms_dbfs[1]), cls: "num" }, [r.pct_fundo_escala, 2],
        { t: fmt(r.degrau_hf[0]) + " dB em " + fmt(r.degrau_hf[1], 0) + " Hz", cls: "nowrap" }];
    }));

  // ----------------------------------------------------- tabela de cortes
  tabela("tab-corte", ["Versão"].concat(RODADAS), D.condicoes.map(function (c) {
    return [NOMES[c]].concat(RODADAS.map(function (g) {
      var v = D.rodadas[g].versoes[c].corte_hz;
      return { t: v == null ? "não há" : fmt(v, 0) + " Hz", cls: "num" };
    }));
  }));

  // ------------------------------------------------- gráfico de espectro (SVG)
  var CURVAS = [
    { id: "mp3_48k", cor: "var(--azul)", traco: "" },
    { id: "aac_48k", cor: "var(--laranja)", traco: "" },
    { id: "vorbis_48k", cor: "var(--verde)", traco: "" },
    { id: "mp3_128k", cor: "var(--azul)", traco: "6 4" },
    { id: "aac_128k", cor: "var(--laranja)", traco: "6 4" },
    { id: "vorbis_128k", cor: "var(--verde)", traco: "6 4" },
    { id: "ANCORA", cor: "var(--cinza)", traco: "2 3" }
  ];
  var ativas = { mp3_48k: true, aac_48k: true, vorbis_48k: true, ANCORA: true };
  var ctl = document.getElementById("ctl-curvas");
  CURVAS.forEach(function (c) {
    var lab = el("label");
    var cb = el("input", { type: "checkbox", value: c.id });
    cb.checked = !!ativas[c.id];
    cb.addEventListener("change", function () {
      ativas[c.id] = cb.checked;
      desenharEspectro();
      anunciar("aviso-curvas", (cb.checked ? "Curva mostrada: " : "Curva ocultada: ") + rotuloCurva(c.id));
    });
    lab.appendChild(cb);
    var sw = el("span", { "aria-hidden": "true", style: "display:inline-block;width:22px;height:0;border-top:3px " +
      (c.traco === "" ? "solid" : c.traco === "2 3" ? "dotted" : "dashed") + " " + c.cor + ";vertical-align:middle" });
    lab.appendChild(sw);
    lab.appendChild(document.createTextNode(rotuloCurva(c.id)));
    ctl.appendChild(lab);
  });
  function rotuloCurva(id) { return id === "ANCORA" ? "Âncora" : NOMES[id]; }

  var rodadaAtual = "G1";
  var svgNS = "http://www.w3.org/2000/svg";
  function sv(tag, attrs, texto) {
    var e = document.createElementNS(svgNS, tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (texto !== undefined) { e.textContent = texto; }
    return e;
  }
  function desenharEspectro() {
    var svg = document.getElementById("svg-espectro");
    Array.prototype.slice.call(svg.querySelectorAll("g")).forEach(function (n) { svg.removeChild(n); });
    var W = 720, H = 340, ml = 54, mr = 14, mt = 14, mb = 42;
    var lx0 = Math.log10(100), lx1 = Math.log10(20000), y0 = 6, y1 = -60;
    var X = function (f) { return ml + (Math.log10(f) - lx0) / (lx1 - lx0) * (W - ml - mr); };
    var Y = function (v) { return mt + (y0 - Math.max(y1, Math.min(y0, v))) / (y0 - y1) * (H - mt - mb); };
    var g = sv("g");
    [100, 200, 500, 1000, 2000, 5000, 10000, 20000].forEach(function (f) {
      g.appendChild(sv("line", { x1: X(f), x2: X(f), y1: mt, y2: H - mb, "class": "grade-l" }));
      g.appendChild(sv("text", { x: X(f), y: H - mb + 16, "text-anchor": "middle", "class": "suave" },
        f >= 1000 ? fmt(f / 1000, 0) + " k" : String(f)));
    });
    [0, -10, -20, -30, -40, -50, -60].forEach(function (v) {
      g.appendChild(sv("line", { x1: ml, x2: W - mr, y1: Y(v), y2: Y(v), "class": v === 0 ? "eixo" : "grade-l" }));
      g.appendChild(sv("text", { x: ml - 6, y: Y(v) + 4, "text-anchor": "end", "class": "suave" }, fmt(v, 0)));
    });
    g.appendChild(sv("text", { x: (ml + W - mr) / 2, y: H - 6, "text-anchor": "middle" }, "frequência (Hz)"));
    g.appendChild(sv("text", { x: 14, y: (mt + H - mb) / 2, "text-anchor": "middle",
      transform: "rotate(-90 14 " + (mt + H - mb) / 2 + ")" }, "nível relativo à referência (dB)"));
    var r = D.rodadas[rodadaAtual];
    CURVAS.forEach(function (c) {
      if (!ativas[c.id]) { return; }
      var vals = c.id === "ANCORA" ? r.ancora.rel : r.versoes[c.id].espectro_rel;
      var d = vals.map(function (v, i) { return (i ? "L" : "M") + X(D.fc[i]).toFixed(1) + " " + Y(v).toFixed(1); }).join(" ");
      g.appendChild(sv("path", { d: d, fill: "none", stroke: c.cor, "stroke-width": 2.2, "stroke-dasharray": c.traco }));
    });
    svg.appendChild(g);
    var partes = D.condicoes.map(function (c) { return NOMES[c] + ": " + hz(r.versoes[c].corte_hz); });
    document.getElementById("svg-espectro-desc").textContent = "Pasta " + rodadaAtual +
      ". Frequência a partir da qual cada versão fica 10 dB abaixo da referência. " + partes.join("; ") +
      ". A âncora cai de forma gradual: " + fmt(r.ancora.a7k) + " dB em 7 kHz e " + fmt(r.ancora.a10k) + " dB em 10 kHz.";
  }

  // ------------------------------------------------ tabelas por rodada
  function tabelasRodada() {
    var g = rodadaAtual, r = D.rodadas[g];
    var linhas = [["Referência WAV", [r.bytes_ref, 0], "não se aplica", { t: fmt(1411.2), cls: "num" }, "não se aplica", "não se aplica",
      [0, 1], [1, 1], "não se aplica", "não há"]];
    D.condicoes.forEach(function (c) {
      var v = r.versoes[c];
      linhas.push([NOMES[c], [v.bytes, 0], [v.kbps_csv, 1], [v.kbps_arquivo, 1], [v.kbps_audio, 1], [v.sobrecarga_bytes, 0],
        [v.reducao_pct, 1], [v.razao, 1], [v.snr_db, 1], { t: v.corte_hz == null ? "não há" : fmt(v.corte_hz, 0), cls: "num" }]);
    });
    tabela("tab-codif", ["Versão", "Bytes", "Taxa no CSV (kbit/s)", "Taxa do arquivo (kbit/s)", "Taxa só do áudio (kbit/s)",
      "Cabeçalhos (bytes)", "Redução (%)", "Razão de compressão", "SNR (dB)", "Corte de 10 dB (Hz)"], linhas);
    document.querySelector("#tab-codif caption").textContent = "Versões codificadas da pasta " + g + ", referência de " +
      fmt(r.duracao, 2) + " s. " + r.descricao + ".";
    tabela("tab-pacote", ["Estímulo", "Condição pelo gabarito", "Conferência", "Amostras", "Bytes"], r.pacote.map(function (p) {
      return [p.codigo, NOMES[p.condicao], { t: p.conferido ? "confere" : "não confere", cls: p.conferido ? "ok" : "ruim" },
        [p.amostras, 0], [p.bytes, 0]];
    }));
    document.querySelector("#tab-pacote caption").textContent = "Pacote anônimo da pasta " + g + " e conferência com o gabarito";
    var img = document.getElementById("img-espectro");
    img.src = D.graficos["espectro_" + g];
    img.alt = "Espectro relativo das versões da pasta " + g + " em dois painéis, 48 e 128 kbit/s. " +
      document.getElementById("svg-espectro-desc").textContent;
    document.getElementById("cap-espectro").textContent = "Mesmo gráfico gerado pelo script para a pasta " + g + ".";
    listaVersoes();
  }

  function listaVersoes() {
    var g = rodadaAtual, r = D.rodadas[g], box = document.getElementById("lista-versoes");
    box.innerHTML = "";
    var itens = [["REF", "Referência WAV", "PCM 16 bits, " + fmt(1411.2) + " kbit/s"],
      ["ANCORA", "Âncora", "passa-baixas de 2ª ordem em 3,5 kHz"]];
    D.condicoes.forEach(function (c) {
      var v = r.versoes[c];
      itens.push([c, NOMES[c], fmt(v.kbps_arquivo) + " kbit/s, redução de " + fmt(v.reducao_pct) + " %"]);
    });
    itens.forEach(function (it) {
      var f = el("figure"), cap = el("figcaption", null, it[1]);
      cap.appendChild(el("span", { "class": "det" }, it[2]));
      f.appendChild(cap);
      f.appendChild(el("audio", { controls: "", preload: "none", src: r.audio[it[0]], "aria-label": it[1] + ", pasta " + g }));
      box.appendChild(f);
    });
  }

  var sel = document.getElementById("sel-rodada");
  sel.addEventListener("change", function () {
    rodadaAtual = sel.value;
    desenharEspectro();
    tabelasRodada();
    anunciar("aviso-rodada", "Pasta " + rodadaAtual + " selecionada. Tabelas, gráfico e áudios atualizados.");
  });
  desenharEspectro();
  tabelasRodada();

  // ------------------------------------------------------- avaliação externa
  var nomesSemNota = [];
  tabela("tab-participantes", ["Participante", "Pacote de áudio", "Data", "Condições de escuta declaradas",
    "Nota da referência oculta", "Referência oculta com 90 ou mais"], D.participantes.map(function (p) {
    p.sem_nota.forEach(function (c) { nomesSemNota.push(p.participante + " no " + NOME_CURTO[c]); });
    return [p.participante, p.grupo_produtor + " (" + D.rodadas[p.grupo_produtor].conteudo + ")",
      { t: p.data.split("-").reverse().join("/"), cls: "nowrap" }, p.condicoes_escuta || "não informadas",
      p.ref_oculta == null ? "sem nota" : [p.ref_oculta, 0],
      { t: p.triagem ? "sim" : "não", cls: "nowrap" }];
  }));
  if (nomesSemNota.length) {
    document.getElementById("lista-sem-nota").textContent = nomesSemNota.slice(0, -1).join(", ") +
      (nomesSemNota.length > 1 ? " e " : "") + nomesSemNota[nomesSemNota.length - 1];
  }

  // ------------------------------------------------------- notas de áudio
  function celulaNota(e) {
    return e.n ? { t: fmt(e.media) + " (" + e.n + ")", cls: "num" } : { t: "sem dados", cls: "num" };
  }
  function resumoAudio() {
    var modo = document.getElementById("sel-triagem").value;
    tabela("tab-resumo-audio", ["Condição"].concat(RODADAS.map(function (g) { return g + " (" + D.rodadas[g].conteudo + ")"; }),
      modo === "todos" ? ["Todos os pacotes"] : []), ORDEM.map(function (c) {
      var l = [NOME_CURTO[c]].concat(RODADAS.map(function (g) { return celulaNota(D.res_audio[g].cond[c][modo]); }));
      if (modo === "todos") { l.push(celulaNota(D.res_audio_geral[c])); }
      return l;
    }), function (i) { return ORDEM[i] === "REF_OCULTA" ? "destaque" : ""; });
    document.querySelector("#tab-resumo-audio caption").textContent = "Nota média por condição e pacote (" +
      (modo === "todos" ? "todos os participantes" : "só os aprovados na triagem") + "; número de notas entre parênteses)";
  }
  document.getElementById("sel-triagem").addEventListener("change", function () {
    resumoAudio();
    anunciar("aviso-triagem", "Tabela atualizada: " + (this.value === "todos" ? "todos os participantes." :
      "só os aprovados na triagem, " + D.n_triados + " participantes."));
  });
  resumoAudio();

  function obsAudio() {
    var g = document.getElementById("sel-obs-audio").value;
    var ls = D.aval_audio.filter(function (a) { return a.grupo_produtor === g; }).sort(function (a, b) {
      return ORDEM.indexOf(a.condicao) - ORDEM.indexOf(b.condicao) || a.participante.localeCompare(b.participante);
    });
    tabela("tab-obs-audio", ["Condição", "Participante", "Estímulo", "Nota", "Comentário"], ls.map(function (a) {
      return [NOME_CURTO[a.condicao], a.participante, a.estimulo, a.nota == null ? "sem nota" : [a.nota, 0],
        a.observacao || "sem comentário"];
    }));
    document.querySelector("#tab-obs-audio caption").textContent = "Notas e comentários do pacote " + g +
      ", agrupados por condição";
  }
  document.getElementById("sel-obs-audio").addEventListener("change", obsAudio);
  obsAudio();

  // ------------------------------------------------------- imagens
  var nomesImg = {};
  var outras = 0;
  D.imagens.forEach(function (l) {
    if (nomesImg[l.imagem]) { return; }
    nomesImg[l.imagem] = l.imagem === D.imagem_destaque ? "Composição coletiva" : "Retrato " + (++outras);
  });
  tabela("tab-jpeg", ["Imagem", "q", "PNG (bytes)", "JPEG (bytes)", "Redução sobre o PNG (%)", "Razão sobre o bruto",
    "Bits por pixel", "PSNR (dB)", "SSIM", "Blocagem"], D.imagens.map(function (l) {
    return [nomesImg[l.imagem], [l.q, 0], [l.bytes_original, 0], [l.bytes_jpeg, 0], [l.reducao_pct, 2], [l.razao_bruto, 1],
      [l.bpp, 2], [l.psnr, 1], [l.ssim, 3], [l.blocagem, 2]];
  }), function (i) { return D.imagens[i].imagem === D.imagem_destaque ? "destaque" : ""; });

  tabela("tab-notas-img", ["Versão", "Respostas", "Média (0 a 3)", "Desvio padrão", "Nota 0", "Nota 1", "Nota 2", "Nota 3"],
    [2, 20, 31].map(function (q) {
      var r = D.res_img[q];
      return ["q=" + q, [r.n, 0], [r.media, 2], [r.dp, 2], [r.contagem[0], 0], [r.contagem[1], 0], [r.contagem[2], 0], [r.contagem[3], 0]];
    }));
  function obsImg() {
    var q = +document.getElementById("sel-obs-img").value;
    var ls = D.aval_img.filter(function (x) { return x.q === q; });
    tabela("tab-obs-img", ["Participante", "Par", "Lado do original", "Diferença (0 a 3)", "Comentário"], ls.map(function (x) {
      return [x.participante, x.par, x.original_lado, [x.diferenca, 0], x.observacao || "sem comentário"];
    }));
    document.querySelector("#tab-obs-img caption").textContent = "Respostas dos participantes para o par com q=" + q;
  }
  document.getElementById("sel-obs-img").addEventListener("change", obsImg);
  obsImg();

  // ---------------------------------------------------- quadro comparativo
  var linhasQA = [["Referência oculta", { t: fmt(1411.2), cls: "num" }, [0, 1], "não há", "idêntica"],
    ["Âncora", { t: fmt(1411.2), cls: "num" }, [0, 1], "gradual a partir de 3,5 kHz",
      [media(RODADAS, function (g) { return D.rodadas[g].ancora.snr_db; }), 1]]];
  D.condicoes.forEach(function (c) {
    var cortes = RODADAS.map(function (g) { return D.rodadas[g].versoes[c].corte_hz; }).filter(function (v) { return v != null; });
    var faixa = !cortes.length ? "não há" : (Math.min.apply(null, cortes) === Math.max.apply(null, cortes) ?
      fmt(cortes[0], 0) + " Hz" : fmt(Math.min.apply(null, cortes), 0) + " a " + fmt(Math.max.apply(null, cortes), 0) + " Hz") +
      " (" + cortes.length + " de 4 pastas)";
    linhasQA.push([NOMES[c], [media(RODADAS, function (g) { return D.rodadas[g].versoes[c].kbps_arquivo; }), 1],
      [media(RODADAS, function (g) { return D.rodadas[g].versoes[c].reducao_pct; }), 1], faixa,
      [media(RODADAS, function (g) { return D.rodadas[g].versoes[c].snr_db; }), 1]]);
  });
  var condQA = ["REF_OCULTA", "ANCORA"].concat(D.condicoes);
  linhasQA.forEach(function (l, i) {
    var c = condQA[i];
    if (D.res_audio_geral[c]) {
      RODADAS.forEach(function (g) { l.push(celulaNota(D.res_audio[g].cond[c].todos)); });
      l.push(celulaNota(D.res_audio_geral[c]));
    } else {
      RODADAS.concat(["x"]).forEach(function () { l.push("fora do teste"); });
    }
  });
  tabela("tab-quadro-audio", ["Condição", "Taxa média (kbit/s)", "Redução média (%)", "Corte de 10 dB", "SNR média (dB)"]
    .concat(RODADAS.map(function (g) { return "Nota " + g; }), ["Nota geral"]), linhasQA);
  tabela("tab-quadro-img", ["Versão", "JPEG médio (bytes)", "Redução média sobre o PNG (%)", "Razão média sobre o bruto",
    "PSNR média (dB)", "SSIM média", "Blocagem média", "Diferença percebida (0 a 3)"], [2, 20, 31].map(function (q) {
    var m = D.media[q];
    var r = D.res_img[q];
    return ["q=" + q, [m.bytes_jpeg, 0], [m.reducao_pct, 1], [m.razao_bruto, 1], [m.psnr, 1], [m.ssim, 3], [m.blocagem, 2],
      { t: fmt(r.media, 2) + " (" + r.n + ")", cls: "num" }];
  }));

  // ------------------------------------------------- textos alternativos
  function altTaxas() {
    return "Gráfico de barras da taxa efetiva por versão e pasta. " + D.condicoes.map(function (c) {
      return NOMES[c] + ": " + RODADAS.map(function (g) { return g + " " + fmt(D.rodadas[g].versoes[c].kbps_arquivo); }).join(", ");
    }).join(". ") + ".";
  }
  document.getElementById("img-taxas").alt = altTaxas();
  document.getElementById("img-notas").alt = "Quatro gráficos de barras, um por pacote, com a nota média de cada condição e as notas individuais. " +
    RODADAS.map(function (g) {
      return "Pacote " + g + ": " + ORDEM.map(function (c) { return NOME_CURTO[c] + " " + fmt(D.res_audio[g].cond[c].todos.media, 0); }).join(", ");
    }).join(". ") + ".";
  document.getElementById("img-notas-img").alt = "Barras empilhadas com o número de participantes por nota de diferença. " +
    [2, 20, 31].map(function (q) {
      var c = D.res_img[q].contagem;
      return "q=" + q + ": " + c[0] + " deram 0, " + c[1] + " deram 1, " + c[2] + " deram 2 e " + c[3] + " deram 3, média " + fmt(D.res_img[q].media, 2);
    }).join(". ") + ".";
  document.getElementById("img-reducao").alt = "Dois gráficos de dispersão. Áudio: as versões a 128 kbit/s, com redução perto de 91 %, ficam perto da referência nos pacotes G2 e G3, e as de 48 kbit/s, perto de 96,5 %, caem para notas entre " +
    fmt(Math.min(D.res_audio.G3.cond.mp3_48k.todos.media, D.res_audio.G2.cond.aac_48k.todos.media), 0) + " e " + fmt(D.res_audio.G3.cond.aac_48k.todos.media, 0) +
    ". Imagem: diferença percebida de " + [2, 20, 31].map(function (q) {
      return fmt(D.res_img[q].media, 2) + " com redução de " + fmt(destaque[q].reducao_pct) + " % (q=" + q + ")";
    }).join(", ") + ".";
  document.getElementById("img-ancora").alt = "Curvas da âncora menos a referência nas quatro pastas, praticamente sobrepostas até 10 kHz. " +
    "Atenuação medida na G1: " + fmt(D.rodadas.G1.ancora.a7k) + " dB em 7 kHz e " + fmt(D.rodadas.G1.ancora.a10k) +
    " dB em 10 kHz. A curva teórica do Butterworth de 2ª ordem passa perto dessas medidas; o passa-baixas ideal cairia na vertical em 3,5 kHz.";
  var d806 = destaque;
  document.getElementById("img-tamanho").alt = "Dois gráficos. Tamanho do JPEG: composição coletiva com " +
    [2, 20, 31].map(function (q) { return fmt(d806[q].bytes_jpeg, 0) + " bytes em q=" + q; }).join(", ") +
    "; as outras fotos ficam um pouco abaixo. PSNR contra bits por pixel na composição coletiva: " +
    [2, 20, 31].map(function (q) { return fmt(d806[q].psnr) + " dB com " + fmt(d806[q].bpp, 2) + " bit por pixel"; }).join(", ") + ".";
  document.getElementById("img-classes").alt = "Barras de PSNR da luminância por classe de bloco. " + [2, 20, 31].map(function (q) {
    var c = D.media[q].classes;
    return "q=" + q + ": uniforme " + fmt(c.uniforme) + " dB, textura " + fmt(c.textura) + " dB, borda " + fmt(c.borda) + " dB";
  }).join(". ") + ".";
  document.getElementById("img-recortes").alt = "Grade de recortes ampliados em 4 colunas (original PNG, q=2, q=20 e q=31) e 3 linhas. " +
    "Parede: lisa no original e em q=2, com blocos de 8 pixels visíveis como degraus de cor em q=20 e q=31. " +
    "Cabelo: fios visíveis no original e em q=2, manchas lisas em q=31. " +
    "Olho da pelúcia: contorno nítido no original, com halos e brilho borrado em q=20 e q=31.";
  document.getElementById("img-mapa").alt = "Foto coletiva ao lado do mapa de classes dos blocos 8 por 8. A parede e o fundo claro aparecem como uniformes, " +
    "cabelos, pelúcias e roupas como textura e os contornos dos rostos, olhos e monitores como borda. Contagem na foto: " +
    d806[2].blocos.uniforme + " blocos uniformes, " + d806[2].blocos.textura + " de textura e " + d806[2].blocos.borda + " de borda.";

  // ------------------------------------------------------------ teste cego
  var TC_CONDS = ["REF_OCULTA", "ANCORA", "mp3_48k", "mp3_128k", "aac_48k", "vorbis_128k"];
  var tc = { rodada: "G1", ordem: [], notas: [], revelado: false };
  function embaralhar(a) {
    a = a.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1)), t = a[i];
      a[i] = a[j]; a[j] = t;
    }
    return a;
  }
  function srcCond(g, c) {
    var au = D.rodadas[g].audio;
    return c === "REF_OCULTA" ? au.REF : c === "ANCORA" ? au.ANCORA : au[c];
  }
  function novoSorteio() {
    tc.rodada = document.getElementById("tc-rodada").value;
    tc.ordem = embaralhar(TC_CONDS);
    tc.notas = tc.ordem.map(function () { return 50; });
    tc.revelado = false;
    document.getElementById("tc-ref").src = D.rodadas[tc.rodada].audio.REF;
    var box = document.getElementById("tc-lista");
    box.innerHTML = "";
    tc.ordem.forEach(function (c, i) {
      var cod = "S0" + (i + 1);
      var linha = el("div", { "class": "estimulo" });
      linha.appendChild(el("span", { "class": "rot", id: "tc-rot-" + i }, "Estímulo " + cod));
      var dir = el("div", { "class": "linha" });
      dir.appendChild(el("audio", { controls: "", preload: "none", src: srcCond(tc.rodada, c), "aria-labelledby": "tc-rot-" + i }));
      var rg = el("input", { type: "range", min: "0", max: "100", step: "1", value: "50", id: "tc-n-" + i,
        "aria-label": "Nota do estímulo " + cod + ", de 0 a 100" });
      var out = el("output", { "for": "tc-n-" + i }, "50");
      rg.addEventListener("input", function () { tc.notas[i] = +rg.value; out.textContent = rg.value; });
      dir.appendChild(rg);
      dir.appendChild(out);
      linha.appendChild(dir);
      box.appendChild(linha);
    });
    document.getElementById("tc-resultado").hidden = true;
    document.getElementById("tc-csv").disabled = true;
    anunciar("tc-aviso", "Novo sorteio da pasta " + tc.rodada + ". Seis estímulos, S01 a S06.");
  }
  function revelar() {
    tc.revelado = true;
    var t = document.getElementById("tc-resultado");
    t.hidden = false;
    tabela("tc-resultado", ["Estímulo", "Condição", "Sua nota"], tc.ordem.map(function (c, i) {
      return ["S0" + (i + 1), NOMES[c], [tc.notas[i], 0]];
    }));
    document.getElementById("tc-csv").disabled = false;
    var ref = tc.notas[tc.ordem.indexOf("REF_OCULTA")];
    anunciar("tc-aviso", "Condições reveladas. Você deu " + ref + " à referência oculta" + (ref < 90 ?
      ", abaixo de 90, o valor que a BS.1534 usa na triagem dos avaliadores." : "."));
  }
  function baixarCsv() {
    var av = document.getElementById("tc-avaliador").value;
    var linhas = ["grupo_avaliador,grupo_produtor,avaliador,estimulo,nota_0_100,condicao"];
    tc.ordem.forEach(function (c, i) {
      linhas.push(["navegador", tc.rodada, av, "S0" + (i + 1) + ".wav", tc.notas[i], c].join(","));
    });
    var blob = new Blob([linhas.join("\n") + "\n"], { type: "text/csv" });
    var a = el("a", { href: URL.createObjectURL(blob), download: tc.rodada + "_" + av + "_navegador.csv" });
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }
  document.getElementById("tc-novo").addEventListener("click", novoSorteio);
  document.getElementById("tc-rodada").addEventListener("change", novoSorteio);
  document.getElementById("tc-revelar").addEventListener("click", revelar);
  document.getElementById("tc-csv").addEventListener("click", baixarCsv);
  novoSorteio();
  document.getElementById("tc-aviso").textContent = "";

  // um áudio por vez
  document.addEventListener("play", function (ev) {
    Array.prototype.forEach.call(document.querySelectorAll("audio"), function (a) {
      if (a !== ev.target) { a.pause(); }
    });
  }, true);

  // ------------------------------------------------------------ comparador
  var cmp = { img: {}, px: {}, pronto: false, x: 520, y: 24 };
  var W = 640, H = 480, ZW = 64, ZH = 48;
  function carregarImagens(cb) {
    var s = document.createElement("script");
    s.src = "js/imagens.js";
    s.onload = function () {
      var fontes = window.LAB4_IMG, chaves = Object.keys(fontes), faltam = chaves.length;
      chaves.forEach(function (k) {
        var im = new Image();
        im.onload = function () { cmp.img[k] = im; if (--faltam === 0) { cb(); } };
        im.src = fontes[k];
      });
    };
    document.body.appendChild(s);
  }
  function pixels(k) {
    if (!cmp.px[k]) {
      var c = document.createElement("canvas");
      c.width = W; c.height = H;
      var x = c.getContext("2d");
      x.drawImage(cmp.img[k], 0, 0);
      cmp.px[k] = x.getImageData(0, 0, W, H).data;
    }
    return cmp.px[k];
  }
  function desenharCmp() {
    if (!cmp.pronto) { return; }
    var q = document.getElementById("cmp-q").value, modo = document.getElementById("cmp-modo").value;
    var cv = document.getElementById("cmp-foto"), ctx = cv.getContext("2d");
    var po = pixels("original"), pj = pixels("q" + q);
    if (modo === "dif") {
      var out = ctx.createImageData(W, H);
      for (var i = 0; i < po.length; i += 4) {
        out.data[i] = Math.min(255, Math.abs(po[i] - pj[i]) * 8);
        out.data[i + 1] = Math.min(255, Math.abs(po[i + 1] - pj[i + 1]) * 8);
        out.data[i + 2] = Math.min(255, Math.abs(po[i + 2] - pj[i + 2]) * 8);
        out.data[i + 3] = 255;
      }
      ctx.putImageData(out, 0, 0);
    } else {
      ctx.drawImage(cmp.img[modo === "original" ? "original" : "q" + q], 0, 0);
    }
    ctx.strokeStyle = "#c0582b";
    ctx.lineWidth = 3;
    ctx.strokeRect(cmp.x - 1.5, cmp.y - 1.5, ZW + 3, ZH + 3);
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1;
    ctx.strokeRect(cmp.x - 3.5, cmp.y - 3.5, ZW + 7, ZH + 7);
    document.getElementById("cmp-z1").getContext("2d").drawImage(cmp.img.original, cmp.x, cmp.y, ZW, ZH, 0, 0, ZW, ZH);
    document.getElementById("cmp-z2").getContext("2d").drawImage(cmp.img["q" + q], cmp.x, cmp.y, ZW, ZH, 0, 0, ZW, ZH);
    document.getElementById("cmp-z2-cap").textContent = "JPEG q=" + q;
    // erro da luminância no trecho
    var se = 0, mx = 0, n = 0;
    for (var yy = cmp.y; yy < cmp.y + ZH; yy++) {
      for (var xx = cmp.x; xx < cmp.x + ZW; xx++) {
        var k = (yy * W + xx) * 4;
        var yo = 0.299 * po[k] + 0.587 * po[k + 1] + 0.114 * po[k + 2];
        var yj = 0.299 * pj[k] + 0.587 * pj[k + 1] + 0.114 * pj[k + 2];
        var e = yo - yj;
        se += e * e; mx = Math.max(mx, Math.abs(e)); n++;
      }
    }
    var psnrT = se === 0 ? Infinity : 10 * Math.log10(255 * 255 / (se / n));
    var l = destaque[q];
    var ficha = document.getElementById("cmp-ficha");
    ficha.innerHTML = "";
    [["Arquivo JPEG", fmt(l.bytes_jpeg, 0) + " bytes"], ["Redução sobre o PNG", fmt(l.reducao_pct, 2) + " %"],
      ["PSNR da foto inteira", fmt(l.psnr) + " dB"], ["PSNR da luminância no trecho", isFinite(psnrT) ? fmt(psnrT) + " dB" : "sem erro"],
      ["Maior erro no trecho", fmt(mx, 0) + " níveis de cinza"], ["Trecho", "x " + cmp.x + " a " + (cmp.x + ZW - 1) + ", y " + cmp.y + " a " + (cmp.y + ZH - 1)]
    ].forEach(function (p) { ficha.appendChild(el("dt", null, p[0])); ficha.appendChild(el("dd", null, p[1])); });
    cv.setAttribute("aria-label", "Composição coletiva, " + (modo === "dif" ? "diferença ampliada entre o original e o JPEG q=" + q :
      modo === "original" ? "original PNG" : "JPEG q=" + q) + ", com o trecho de x " + cmp.x + " e y " + cmp.y + " marcado.");
    document.getElementById("cmp-z2").setAttribute("aria-label", "Trecho ampliado do JPEG q=" + q + ". PSNR da luminância no trecho " +
      (isFinite(psnrT) ? fmt(psnrT) + " dB" : "infinita") + ", maior erro " + fmt(mx, 0) + " níveis.");
    anunciar("cmp-aviso", "q=" + q + ", trecho em x " + cmp.x + " e y " + cmp.y + ": PSNR do trecho " +
      (isFinite(psnrT) ? fmt(psnrT) + " dB" : "sem erro") + ", maior erro " + fmt(mx, 0) + " níveis de cinza.");
  }
  function mover(x, y) {
    cmp.x = Math.max(0, Math.min(W - ZW, Math.round(x / 8) * 8));
    cmp.y = Math.max(0, Math.min(H - ZH, Math.round(y / 8) * 8));
    document.getElementById("cmp-x").value = cmp.x;
    document.getElementById("cmp-y").value = cmp.y;
    desenharCmp();
  }
  document.getElementById("cmp-foto").addEventListener("click", function (ev) {
    var r = ev.currentTarget.getBoundingClientRect();
    mover((ev.clientX - r.left) / r.width * W - ZW / 2, (ev.clientY - r.top) / r.height * H - ZH / 2);
  });
  ["cmp-x", "cmp-y"].forEach(function (id) {
    document.getElementById(id).addEventListener("change", function () {
      mover(+document.getElementById("cmp-x").value || 0, +document.getElementById("cmp-y").value || 0);
    });
  });
  ["cmp-q", "cmp-modo"].forEach(function (id) { document.getElementById(id).addEventListener("change", desenharCmp); });
  Array.prototype.forEach.call(document.querySelectorAll("[data-reg]"), function (b) {
    b.addEventListener("click", function () {
      var reg = D.regioes[b.getAttribute("data-reg")];
      mover(reg[0], reg[1]);
    });
  });
  carregarImagens(function () {
    cmp.pronto = true;
    try {
      desenharCmp();
    } catch (e) {
      cmp.pronto = false;
      document.getElementById("cmp-cap").textContent = "O navegador bloqueou a leitura dos pixels. Abra a página pelo site publicado.";
    }
  });

  // ------------------------------------------------------------- tema
  var bt = document.getElementById("bt-tema");
  function atual() {
    var t = document.documentElement.getAttribute("data-theme");
    if (t) { return t; }
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function rotulo() {
    var escuro = atual() === "dark";
    bt.textContent = escuro ? "Tema claro" : "Tema escuro";
    bt.setAttribute("aria-pressed", escuro ? "true" : "false");
  }
  rotulo();
  bt.addEventListener("click", function () {
    var novo = atual() === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", novo);
    try { localStorage.setItem("tema-csm", novo); } catch (e) {}
    rotulo();
  });
})();
