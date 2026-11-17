"""
XADREZ - Jogador vs. Jogador (PvP)
Projeto de Programação Orientada a Objetos com Tkinter

Etapa 2 - regras do xadrez e painel lateral.
    - Movimentos legais (o Rei nunca fica em xeque), xeque, xeque-mate, afogamento
    - Roque curto/longo e en passant
    - Classe Lance (notação algébrica) e histórico de lances
    - Janela "Sobre" com tk.Toplevel e menu Arquivo/Ajuda

Falta fazer: escolha da peça na promoção (por enquanto vira Rainha), peças
capturadas, botão Desistir, empate por material insuficiente, coordenadas
nas bordas, atalhos de teclado, "Como jogar" e @property nas peças.

Coordenadas internas: (linha, coluna); linha 0 = 8ª fileira (topo da tela).
"""

import tkinter as tk
from tkinter import messagebox
from tkinter import font as tkfont

BRANCAS = "brancas"
PRETAS = "pretas"
LETRAS_COLUNAS = "abcdefgh"

COR_FUNDO = "#2B2926"
COR_PAINEL = "#3A3733"
COR_TEXTO = "#EDEDED"
COR_TEXTO_SUAVE = "#B5B0A8"


def oposta(cor):
    """Devolve a cor adversária."""
    return PRETAS if cor == BRANCAS else BRANCAS


def dentro_do_tabuleiro(linha, coluna):
    return 0 <= linha < 8 and 0 <= coluna < 8


def para_algebrica(linha, coluna):
    """Converte (linha, coluna) para a notação algébrica (ex.: 'e4')."""
    return f"{LETRAS_COLUNAS[coluna]}{8 - linha}"


def escolher_fonte(janela):
    """Escolhe uma fonte instalada que tenha os símbolos das peças."""
    instaladas = set(tkfont.families(janela))
    for nome in ("Segoe UI Symbol", "Apple Symbols", "DejaVu Sans",
                 "FreeSerif", "Symbola"):
        if nome in instaladas:
            return nome
    return "Arial"


class MovimentoInvalidoError(Exception):
    """Lançada quando o jogador tenta uma ação que as regras não permitem."""

    def __init__(self, mensagem="Movimento inválido!"):
        super().__init__(mensagem)
        self.mensagem = mensagem


# =============================================================================
# PEÇAS
# =============================================================================
class Peca:
    """Superclasse de todas as peças. Cada subclasse sobrescreve
    `movimentos_pseudo_legais` (polimorfismo): respeitam o jeito de andar da
    peça, mas ainda não consideram o xeque (tarefa do Tabuleiro)."""

    nome = "Peça"
    artigo = "a"
    letra = "?"
    simbolo = "?"

    def __init__(self, cor=BRANCAS, linha=0, coluna=0):
        self.cor = cor
        self.linha = linha
        self.coluna = coluna
        self.ja_moveu = False

    def movimentos_pseudo_legais(self, tabuleiro):
        raise NotImplementedError("Cada peça deve implementar seu movimento.")

    def casas_atacadas(self, tabuleiro):
        """Casas ameaçadas pela peça (Peão e Rei sobrescrevem)."""
        return self.movimentos_pseudo_legais(tabuleiro)

    def deslizar(self, tabuleiro, direcoes):
        """Anda em linha reta até esbarrar em algo (Torre, Bispo, Rainha)."""
        destinos = []
        for d_linha, d_coluna in direcoes:
            linha, coluna = self.linha + d_linha, self.coluna + d_coluna
            while dentro_do_tabuleiro(linha, coluna):
                alvo = tabuleiro.obter(linha, coluna)
                if alvo is None or alvo.cor != self.cor:
                    destinos.append((linha, coluna))
                if alvo is not None:
                    break
                linha, coluna = linha + d_linha, coluna + d_coluna
        return destinos

    def saltar(self, tabuleiro, deslocamentos):
        """Anda por deslocamentos fixos (Cavalo e Rei)."""
        destinos = []
        for d_linha, d_coluna in deslocamentos:
            linha, coluna = self.linha + d_linha, self.coluna + d_coluna
            if dentro_do_tabuleiro(linha, coluna):
                alvo = tabuleiro.obter(linha, coluna)
                if alvo is None or alvo.cor != self.cor:
                    destinos.append((linha, coluna))
        return destinos

    def __str__(self):
        return f"{self.nome} das {self.cor} em {para_algebrica(self.linha, self.coluna)}"


class Torre(Peca):
    nome, letra, simbolo = "Torre", "T", "\u265C"

    def movimentos_pseudo_legais(self, tabuleiro):
        return self.deslizar(tabuleiro, [(-1, 0), (1, 0), (0, -1), (0, 1)])


class Bispo(Peca):
    nome, artigo, letra, simbolo = "Bispo", "o", "B", "\u265D"

    def movimentos_pseudo_legais(self, tabuleiro):
        return self.deslizar(tabuleiro, [(-1, -1), (-1, 1), (1, -1), (1, 1)])


class Cavalo(Peca):
    nome, artigo, letra, simbolo = "Cavalo", "o", "C", "\u265E"

    def movimentos_pseudo_legais(self, tabuleiro):
        return self.saltar(tabuleiro, [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                                       (1, -2), (1, 2), (2, -1), (2, 1)])


class Rainha(Peca):
    nome, letra, simbolo = "Rainha", "D", "\u265B"

    def movimentos_pseudo_legais(self, tabuleiro):
        return self.deslizar(tabuleiro, [(-1, 0), (1, 0), (0, -1), (0, 1),
                                         (-1, -1), (-1, 1), (1, -1), (1, 1)])


class Rei(Peca):
    nome, artigo, letra, simbolo = "Rei", "o", "R", "\u265A"

    def __init__(self, cor=BRANCAS, linha=0, coluna=0):
        super().__init__(cor, linha, coluna)

    def casas_atacadas(self, tabuleiro):
        """O Rei ameaça só as casas vizinhas (o roque nunca captura)."""
        return self.saltar(tabuleiro, [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                                       (0, 1), (1, -1), (1, 0), (1, 1)])

    def movimentos_pseudo_legais(self, tabuleiro):
        return self.casas_atacadas(tabuleiro) + self.roques_possiveis(tabuleiro)

    def roques_possiveis(self, tabuleiro):
        """Rei e Torre sem ter se movido, caminho livre e sem casas atacadas."""
        destinos = []
        adversaria = oposta(self.cor)
        if self.ja_moveu or self.coluna != 4 or \
                tabuleiro.casa_atacada(self.linha, self.coluna, adversaria):
            return destinos                  # não há roque se o Rei está em xeque
        # (coluna da torre, casas vazias, casas atravessadas, destino do rei)
        for col_torre, vazias, atravessadas, destino in (
                (7, (5, 6), (5, 6), 6),             # roque curto
                (0, (1, 2, 3), (3, 2), 2)):         # roque longo
            torre = tabuleiro.obter(self.linha, col_torre)
            if not isinstance(torre, Torre) or torre.cor != self.cor or torre.ja_moveu:
                continue
            if any(tabuleiro.obter(self.linha, c) is not None for c in vazias):
                continue
            if any(tabuleiro.casa_atacada(self.linha, c, adversaria) for c in atravessadas):
                continue
            destinos.append((self.linha, destino))
        return destinos


class Peao(Peca):
    nome, artigo, letra, simbolo = "Peão", "o", "", "\u265F"

    def __init__(self, cor=BRANCAS, linha=0, coluna=0):
        super().__init__(cor, linha, coluna)
        self.direcao = -1 if cor == BRANCAS else 1      # brancas sobem
        self.linha_inicial = 6 if cor == BRANCAS else 1

    def casas_atacadas(self, tabuleiro):
        """O peão ameaça as duas diagonais à frente (mesmo vazias)."""
        linha = self.linha + self.direcao
        return [(linha, self.coluna + d) for d in (-1, 1)
                if dentro_do_tabuleiro(linha, self.coluna + d)]

    def movimentos_pseudo_legais(self, tabuleiro):
        destinos = []
        frente = self.linha + self.direcao
        if dentro_do_tabuleiro(frente, self.coluna) and \
                tabuleiro.obter(frente, self.coluna) is None:
            destinos.append((frente, self.coluna))
            dupla = frente + self.direcao
            if self.linha == self.linha_inicial and \
                    tabuleiro.obter(dupla, self.coluna) is None:
                destinos.append((dupla, self.coluna))
        for linha, coluna in self.casas_atacadas(tabuleiro):
            alvo = tabuleiro.obter(linha, coluna)
            if alvo is not None and alvo.cor != self.cor:
                destinos.append((linha, coluna))                # captura
            elif alvo is None and tabuleiro.alvo_en_passant == (linha, coluna):
                destinos.append((linha, coluna))                # en passant
        return destinos


# =============================================================================
# LANCE, TABULEIRO E JOGO
# =============================================================================
class Lance:
    """Registro de um movimento, escrito em notação algébrica longa
    (ex.: 'Cb1-c3', 'e4xd5', 'O-O', 'e7-e8=D#')."""

    def __init__(self, peca=None, origem=(0, 0), destino=(0, 0)):
        self.peca = peca
        self.origem = origem
        self.destino = destino
        self.capturada = None
        self.roque = None               # None, "curto" ou "longo"
        self.promocao = None            # classe da peça promovida
        self.sufixo = ""                # "+" (xeque) ou "#" (xeque-mate)

    def __str__(self):
        if self.roque:
            texto = "O-O" if self.roque == "curto" else "O-O-O"
        else:
            separador = "x" if self.capturada is not None else "-"
            texto = (f"{self.peca.letra}{para_algebrica(*self.origem)}"
                     f"{separador}{para_algebrica(*self.destino)}")
            if self.promocao is not None:
                texto += f"={self.promocao.letra}"
        return texto + self.sufixo


class Tabuleiro:
    """Matriz 8x8 de peças + regras que dependem do conjunto do tabuleiro."""

    def __init__(self):
        self.casas = [[None] * 8 for _ in range(8)]
        self.alvo_en_passant = None    # casa "pulada" por um peão no último lance
        self.posicionar_pecas_iniciais()

    def posicionar_pecas_iniciais(self):
        self.casas = [[None] * 8 for _ in range(8)]
        self.alvo_en_passant = None
        ordem = [Torre, Cavalo, Bispo, Rainha, Rei, Bispo, Cavalo, Torre]
        for coluna, classe in enumerate(ordem):
            self.colocar(classe(PRETAS), 0, coluna)
            self.colocar(classe(BRANCAS), 7, coluna)
        for coluna in range(8):
            self.colocar(Peao(PRETAS), 1, coluna)
            self.colocar(Peao(BRANCAS), 6, coluna)

    def colocar(self, peca, linha, coluna):
        self.casas[linha][coluna] = peca
        if peca is not None:
            peca.linha, peca.coluna = linha, coluna

    def obter(self, linha, coluna):
        return self.casas[linha][coluna]

    def pecas_da_cor(self, cor):
        return [p for fileira in self.casas for p in fileira
                if p is not None and p.cor == cor]

    def casa_atacada(self, linha, coluna, cor_atacante):
        """True se alguma peça de `cor_atacante` ameaça a casa indicada."""
        return any((linha, coluna) in p.casas_atacadas(self)
                   for p in self.pecas_da_cor(cor_atacante))

    def localizar_rei(self, cor):
        return next(p for p in self.pecas_da_cor(cor) if isinstance(p, Rei))

    def em_xeque(self, cor):
        rei = self.localizar_rei(cor)
        return self.casa_atacada(rei.linha, rei.coluna, oposta(cor))

    def deixa_rei_em_xeque(self, peca, destino):
        """Simula o movimento, vê se o Rei próprio fica em xeque e desfaz."""
        l_ori, c_ori = peca.linha, peca.coluna
        l_des, c_des = destino
        capturada = self.casas[l_des][c_des]
        en_passant = None
        if isinstance(peca, Peao) and c_ori != c_des and capturada is None:
            en_passant = self.casas[l_ori][c_des]       # peão ao lado da origem
            self.casas[l_ori][c_des] = None
        self.casas[l_ori][c_ori] = None
        self.colocar(peca, l_des, c_des)
        try:
            return self.em_xeque(peca.cor)
        finally:                    # desfaz a simulação, aconteça o que acontecer
            self.casas[l_des][c_des] = capturada
            self.colocar(peca, l_ori, c_ori)
            if en_passant is not None:
                self.casas[l_ori][c_des] = en_passant

    def movimentos_legais(self, peca):
        """Pseudo-legais que não deixam o próprio Rei em xeque."""
        return [d for d in peca.movimentos_pseudo_legais(self)
                if not self.deixa_rei_em_xeque(peca, d)]

    def possui_movimento_legal(self, cor):
        return any(self.movimentos_legais(p) for p in self.pecas_da_cor(cor))

    def executar_movimento(self, origem, destino):
        """Executa o lance (já validado) e devolve um objeto Lance."""
        l_ori, c_ori = origem
        l_des, c_des = destino
        peca = self.casas[l_ori][c_ori]
        lance = Lance(peca, origem, destino)
        lance.capturada = self.casas[l_des][c_des]

        if isinstance(peca, Peao) and c_ori != c_des and lance.capturada is None:
            lance.capturada = self.casas[l_ori][c_des]       # en passant
            self.casas[l_ori][c_des] = None

        if isinstance(peca, Rei) and abs(c_des - c_ori) == 2:    # roque
            curto = c_des > c_ori
            col_torre = 7 if curto else 0
            torre = self.casas[l_ori][col_torre]
            self.casas[l_ori][col_torre] = None
            self.colocar(torre, l_ori, 5 if curto else 3)
            torre.ja_moveu = True
            lance.roque = "curto" if curto else "longo"

        self.casas[l_ori][c_ori] = None
        self.colocar(peca, l_des, c_des)
        peca.ja_moveu = True

        if isinstance(peca, Peao) and l_des in (0, 7):            # promoção
            self.colocar(Rainha(peca.cor), l_des, c_des)
            lance.promocao = Rainha

        if isinstance(peca, Peao) and abs(l_des - l_ori) == 2:
            self.alvo_en_passant = ((l_ori + l_des) // 2, c_ori)
        else:
            self.alvo_en_passant = None
        return lance


class Jogo:
    """Controla turnos, histórico e situação da partida (sem Tkinter)."""

    def __init__(self):
        self.tabuleiro = Tabuleiro()
        self.reiniciar()

    def reiniciar(self):
        self.tabuleiro.posicionar_pecas_iniciais()
        self.turno = BRANCAS
        self.historico = []
        self.estado = "em_andamento"    # ou xeque, xeque_mate, afogamento
        self.vencedor = None
        self.ultimo_lance = None

    @property
    def em_andamento(self):
        return self.estado not in ("xeque_mate", "afogamento")

    def movimentos_da_peca(self, linha, coluna):
        """Movimentos legais da peça para o jogador da vez (ou lança erro)."""
        if not self.em_andamento:
            raise MovimentoInvalidoError("A partida já terminou.\nInicie uma nova partida.")
        peca = self.tabuleiro.obter(linha, coluna)
        if peca is None:
            raise MovimentoInvalidoError("Não há nenhuma peça nessa casa.")
        if peca.cor != self.turno:
            raise MovimentoInvalidoError(
                f"Essa peça pertence às {peca.cor}, mas é a vez das {self.turno}.")
        destinos = self.tabuleiro.movimentos_legais(peca)
        if not destinos:
            dica = "\nSeu Rei está em xeque!" if self.estado == "xeque" else ""
            raise MovimentoInvalidoError(
                f"Essa peça ({peca.nome}) não tem movimento legal agora.{dica}")
        return destinos

    def mover(self, origem, destino):
        """Valida e executa o movimento, troca o turno e reavalia a partida."""
        if destino not in self.movimentos_da_peca(*origem):
            peca = self.tabuleiro.obter(*origem)
            if destino in peca.movimentos_pseudo_legais(self.tabuleiro):
                raise MovimentoInvalidoError(
                    "Esse movimento deixaria seu Rei em xeque, o que é proibido.")
            raise MovimentoInvalidoError(
                f"{peca.artigo.capitalize()} {peca.nome} não pode ir para "
                f"{para_algebrica(*destino)}.")
        lance = self.tabuleiro.executar_movimento(origem, destino)
        self.turno = oposta(self.turno)
        self.avaliar_situacao(lance)
        self.historico.append(lance)
        self.ultimo_lance = lance

    def avaliar_situacao(self, lance):
        """Define se há xeque, xeque-mate ou afogamento após o lance."""
        em_xeque = self.tabuleiro.em_xeque(self.turno)
        if not self.tabuleiro.possui_movimento_legal(self.turno):
            if em_xeque:
                self.estado, lance.sufixo = "xeque_mate", "#"
                self.vencedor = oposta(self.turno)
            else:
                self.estado = "afogamento"
        elif em_xeque:
            self.estado, lance.sufixo = "xeque", "+"
        else:
            self.estado = "em_andamento"

    def texto_status(self):
        if self.estado == "xeque":
            return f"XEQUE!\nO Rei das {self.turno} está sob ataque."
        if self.estado == "xeque_mate":
            return f"XEQUE-MATE!\nAs {self.vencedor} venceram a partida."
        if self.estado == "afogamento":
            return "EMPATE por afogamento:\nsem lances legais e sem xeque."
        return f"Turno das {self.turno}.\nEscolha uma peça e depois o destino."


# =============================================================================
# INTERFACE (Tkinter)
# =============================================================================
class JanelaSobre(tk.Toplevel):
    """Janela secundária 'Ajuda -> Sobre'."""

    def __init__(self, master=None, familia_fonte="Arial"):
        super().__init__(master, bg=COR_FUNDO)
        self.title("Sobre o Xadrez")
        self.resizable(False, False)
        self.transient(master)
        tk.Label(self, text="\u265E", font=(familia_fonte, 44), bg=COR_FUNDO,
                 fg=COR_TEXTO).pack(pady=(16, 0))
        tk.Label(self, text="Xadrez \u2022 Python + Tkinter", bg=COR_FUNDO,
                 fg=COR_TEXTO, font=("Helvetica", 15, "bold")).pack()
        tk.Label(self, text="Versão 0.5", bg=COR_FUNDO, fg=COR_TEXTO_SUAVE).pack()
        tk.Label(self, justify="center", bg=COR_FUNDO, fg=COR_TEXTO,
                 text="Xadrez para dois jogadores no mesmo computador,\n"
                      "feito para demonstrar POO: classes, herança,\n"
                      "polimorfismo, super() e Tkinter.").pack(padx=28, pady=10)
        tk.Button(self, text="Fechar", width=12, command=self.destroy).pack(pady=(0, 16))
        self.bind("<Escape>", lambda evento: self.destroy())
        self.focus_set()


class TelaMenu(tk.Frame):
    """Menu principal. Todos os widgets usam pack() dentro deste Frame."""

    def __init__(self, master, ao_jogar, ao_sair, familia_fonte="Arial"):
        super().__init__(master, bg=COR_FUNDO)
        centro = tk.Frame(self, bg=COR_FUNDO)
        centro.pack(expand=True)
        tk.Label(centro, text="\u265A \u265B \u265C", font=(familia_fonte, 46),
                 bg=COR_FUNDO, fg="#D9B26F").pack()
        tk.Label(centro, text="XADREZ", font=("Helvetica", 44, "bold"),
                 bg=COR_FUNDO, fg=COR_TEXTO).pack()
        tk.Label(centro, text="Jogador  vs  Jogador", font=("Helvetica", 14),
                 bg=COR_FUNDO, fg=COR_TEXTO_SUAVE).pack(pady=(0, 30))
        tk.Button(centro, text="Jogar", width=22, command=ao_jogar).pack(pady=6)
        tk.Button(centro, text="Sair", width=22, command=ao_sair).pack(pady=6)


class TelaJogo(tk.Frame):
    """Tela da partida. Geometria: self usa grid ([tabuleiro | painel]);
    o frame do tabuleiro e o painel lateral usam pack internamente."""

    CASA = 64
    MARGEM = 12
    COR_CLARA, COR_ESCURA = "#F0D9B5", "#B58863"
    COR_ULT_CLARA, COR_ULT_ESCURA = "#CED26B", "#AAA23A"
    COR_SELECAO, COR_XEQUE, COR_DICA = "#F5E663", "#E8584F", "#5E8C31"

    def __init__(self, master, ao_voltar, familia_fonte="Arial"):
        super().__init__(master, bg=COR_FUNDO)
        self.jogo = Jogo()
        self.ao_voltar = ao_voltar
        self.fonte_pecas = (familia_fonte, -int(self.CASA * 0.74))
        self.selecionada = None      # (linha, coluna) da peça selecionada
        self.destinos = []           # destinos legais dessa peça
        self.criar_widgets()
        self.desenhar()
        self.atualizar_painel()

    def criar_widgets(self):
        lado = 8 * self.CASA + 2 * self.MARGEM
        frame_tabuleiro = tk.Frame(self, bg=COR_FUNDO)
        frame_tabuleiro.grid(row=0, column=0, padx=(14, 6), pady=12, sticky="n")
        self.canvas = tk.Canvas(frame_tabuleiro, width=lado, height=lado,
                                bg=COR_FUNDO, highlightthickness=0, cursor="hand2")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.ao_clicar)

        painel = tk.Frame(self, bg=COR_PAINEL, padx=12, pady=12)
        painel.grid(row=0, column=1, padx=(6, 14), pady=12, sticky="nsew")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.lbl_turno = tk.Label(painel, width=22, pady=8, font=("Helvetica", 14, "bold"))
        self.lbl_turno.pack(fill="x", pady=(0, 6))
        self.var_mensagem = tk.StringVar()
        tk.Label(painel, textvariable=self.var_mensagem, height=3, wraplength=250,
                 justify="left", anchor="nw", bg=COR_PAINEL, fg=COR_TEXTO).pack(fill="x")

        frame_hist = tk.LabelFrame(painel, text=" Histórico de lances ",
                                   bg=COR_PAINEL, fg=COR_TEXTO_SUAVE, padx=6, pady=6)
        frame_hist.pack(fill="both", expand=True, pady=8)
        barra = tk.Scrollbar(frame_hist, orient="vertical")
        self.lista_historico = tk.Listbox(
            frame_hist, width=30, height=4, bg="#262421", fg=COR_TEXTO,
            font=("Courier", 10), bd=0, highlightthickness=0,
            yscrollcommand=barra.set)
        barra.config(command=self.lista_historico.yview)
        barra.pack(side="right", fill="y")
        self.lista_historico.pack(side="left", fill="both", expand=True)

        tk.Button(painel, text="Nova partida",
                  command=self.nova_partida).pack(fill="x", pady=2)
        tk.Button(painel, text="Voltar ao menu",
                  command=lambda: self.ao_voltar()).pack(fill="x", pady=2)

    def desenhar(self):
        """Redesenha o Canvas: casas, destaques, dicas e peças."""
        self.canvas.delete("all")
        tam, margem = self.CASA, self.MARGEM
        tabuleiro, ultimo = self.jogo.tabuleiro, self.jogo.ultimo_lance
        casa_xeque = None
        if self.jogo.estado in ("xeque", "xeque_mate"):
            rei = tabuleiro.localizar_rei(self.jogo.turno)
            casa_xeque = (rei.linha, rei.coluna)

        for linha in range(8):
            for coluna in range(8):
                clara = (linha + coluna) % 2 == 0
                cor = self.COR_CLARA if clara else self.COR_ESCURA
                if ultimo is not None and (linha, coluna) in (ultimo.origem, ultimo.destino):
                    cor = self.COR_ULT_CLARA if clara else self.COR_ULT_ESCURA
                if casa_xeque == (linha, coluna):
                    cor = self.COR_XEQUE
                if self.selecionada == (linha, coluna):
                    cor = self.COR_SELECAO
                x, y = margem + coluna * tam, margem + linha * tam
                self.canvas.create_rectangle(x, y, x + tam, y + tam, fill=cor, outline=cor)
                if (linha, coluna) in self.destinos:
                    if tabuleiro.obter(linha, coluna) is not None:    # captura: anel
                        self.canvas.create_oval(x + 4, y + 4, x + tam - 4, y + tam - 4,
                                                outline=self.COR_DICA, width=5)
                    else:                                             # vazia: ponto
                        self.canvas.create_oval(x + 24, y + 24, x + 40, y + 40,
                                                fill=self.COR_DICA, outline="")
                peca = tabuleiro.obter(linha, coluna)
                if peca is not None:
                    self.desenhar_peca(peca, x + tam / 2, y + tam / 2)

    def desenhar_peca(self, peca, cx, cy):
        if peca.cor == BRANCAS:         # contorno preto para as brancas
            for d_x, d_y in ((-1.5, 0), (1.5, 0), (0, -1.5), (0, 1.5)):
                self.canvas.create_text(cx + d_x, cy + d_y, text=peca.simbolo,
                                        font=self.fonte_pecas, fill="#000000")
        self.canvas.create_text(cx, cy, text=peca.simbolo, font=self.fonte_pecas,
                                fill="#FFFFFF" if peca.cor == BRANCAS else "#111111")

    def atualizar_painel(self):
        jogo = self.jogo
        if not jogo.em_andamento:
            self.lbl_turno.config(text="FIM DE JOGO", bg="#A8423A", fg="#FFFFFF")
        elif jogo.turno == BRANCAS:
            self.lbl_turno.config(text="Vez das BRANCAS", bg="#F5F5F5", fg="#111111")
        else:
            self.lbl_turno.config(text="Vez das PRETAS", bg="#111111", fg="#F5F5F5")
        self.var_mensagem.set(jogo.texto_status())

        self.lista_historico.delete(0, tk.END)          # histórico em pares
        lances = jogo.historico
        for i in range(0, len(lances), 2):
            preto = str(lances[i + 1]) if i + 1 < len(lances) else ""
            self.lista_historico.insert(tk.END, f"{i // 2 + 1:>3}. {lances[i]!s:<10} {preto}")
        self.lista_historico.see(tk.END)

    def ao_clicar(self, evento):
        coluna = (evento.x - self.MARGEM) // self.CASA
        linha = (evento.y - self.MARGEM) // self.CASA
        if not dentro_do_tabuleiro(linha, coluna):
            return
        try:
            self.tratar_clique(linha, coluna)
        except MovimentoInvalidoError as erro:
            messagebox.showwarning("Movimento inválido", erro.mensagem, parent=self)
        except Exception as erro:                  # rede de segurança
            messagebox.showerror("Erro inesperado", f"Ocorreu um erro:\n{erro}",
                                 parent=self)

    def tratar_clique(self, linha, coluna):
        clicada = (linha, coluna)
        peca = self.jogo.tabuleiro.obter(linha, coluna)
        if clicada == self.selecionada:                      # cancelar seleção
            self.limpar_selecao()
        elif self.selecionada is None or (peca and peca.cor == self.jogo.turno):
            self.destinos = self.jogo.movimentos_da_peca(linha, coluna)   # valida
            self.selecionada = clicada
        else:                                                # tentar mover
            self.jogo.mover(self.selecionada, clicada)
            self.limpar_selecao()
            self.atualizar_painel()
            if not self.jogo.em_andamento:
                messagebox.showinfo("Fim de jogo", self.jogo.texto_status(), parent=self)
        self.desenhar()

    def limpar_selecao(self):
        self.selecionada = None
        self.destinos = []

    def partida_em_curso(self):
        return len(self.jogo.historico) > 0 and self.jogo.em_andamento

    def nova_partida(self):
        if self.partida_em_curso() and not messagebox.askyesno(
                "Nova partida", "A partida atual será descartada.\nContinuar?",
                parent=self):
            return
        self.jogo.reiniciar()
        self.limpar_selecao()
        self.desenhar()
        self.atualizar_painel()


class ChessApp(tk.Tk):
    """Janela principal: barra de menus + contêiner que alterna as telas."""

    def __init__(self):
        super().__init__()
        self.title("Xadrez \u2014 Python & Tkinter")
        self.configure(bg=COR_FUNDO)
        self.geometry("940x660")
        self.minsize(940, 660)
        self.fonte_pecas = escolher_fonte(self)
        self.criar_menu()

        self.container = tk.Frame(self, bg=COR_FUNDO)
        self.container.pack(fill="both", expand=True)
        self.tela_menu = TelaMenu(self.container, self.iniciar_partida,
                                  self.confirmar_saida, self.fonte_pecas)
        self.tela_jogo = None
        self.tela_atual = None
        self.mostrar_tela(self.tela_menu)
        self.protocol("WM_DELETE_WINDOW", self.confirmar_saida)

    def criar_menu(self):
        barra = tk.Menu(self)
        arquivo = tk.Menu(barra, tearoff=0)
        arquivo.add_command(label="Nova partida", command=self.iniciar_partida)
        arquivo.add_command(label="Voltar ao menu principal", command=self.voltar_ao_menu)
        arquivo.add_separator()
        arquivo.add_command(label="Sair", command=self.confirmar_saida)
        barra.add_cascade(label="Arquivo", menu=arquivo)
        ajuda = tk.Menu(barra, tearoff=0)
        ajuda.add_command(label="Sobre", command=lambda: JanelaSobre(self, self.fonte_pecas))
        barra.add_cascade(label="Ajuda", menu=ajuda)
        self.config(menu=barra)

    def mostrar_tela(self, tela):
        if self.tela_atual is not None and self.tela_atual is not tela:
            self.tela_atual.pack_forget()
        tela.pack(fill="both", expand=True)
        self.tela_atual = tela

    def iniciar_partida(self):
        """Botão 'Jogar' / menu 'Nova partida'."""
        if self.tela_jogo is not None:
            self.tela_jogo.nova_partida()
        else:
            self.tela_jogo = TelaJogo(self.container, self.voltar_ao_menu,
                                      self.fonte_pecas)
        self.mostrar_tela(self.tela_jogo)

    def voltar_ao_menu(self):
        if self.tela_jogo is not None:
            if self.tela_jogo.partida_em_curso() and not messagebox.askyesno(
                    "Voltar ao menu", "A partida atual será encerrada.\nContinuar?",
                    parent=self):
                return
            self.tela_jogo.destroy()
            self.tela_jogo = None
            self.tela_atual = None
        self.mostrar_tela(self.tela_menu)

    def confirmar_saida(self):
        """Botão Sair, menu Arquivo e protocolo WM_DELETE_WINDOW."""
        if messagebox.askyesno("Sair", "Deseja realmente sair do jogo?", parent=self):
            self.destroy()


def main():
    ChessApp().mainloop()


if __name__ == "__main__":
    main()
