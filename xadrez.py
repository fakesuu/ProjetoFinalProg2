"""
XADREZ - Jogador vs. Jogador (PvP)

Projeto de POO com Tkinter. Etapa 1: peças (herança/polimorfismo), tabuleiro,
turnos, menu inicial e Canvas.
Falta: xeque/xeque-mate, roque, en passant, promoção, histórico, capturas,
janela "Sobre" (Toplevel). Coordenadas: (linha, coluna); linha 0 = topo.
"""

import sys
import tkinter as tk
from tkinter import messagebox

BRANCAS = "brancas"
PRETAS = "pretas"

COR_FUNDO = "#2B2926"
COR_TEXTO = "#EDEDED"


def oposta(cor):
    return PRETAS if cor == BRANCAS else BRANCAS


def dentro(linha, coluna):
    """True se (linha, coluna) é uma casa válida do tabuleiro."""
    return 0 <= linha < 8 and 0 <= coluna < 8


class MovimentoInvalidoError(Exception):
    """Lançada quando o jogador tenta algo que as regras não permitem."""


# =============================================================================
# PEÇAS
# =============================================================================
class Peca:
    """Superclasse: cada subclasse sobrescreve `movimentos` (polimorfismo)."""

    nome = "Peça"
    simbolo = "?"

    def __init__(self, cor=BRANCAS, linha=0, coluna=0):
        self.cor = cor
        self.linha = linha
        self.coluna = coluna

    def movimentos(self, tabuleiro):
        raise NotImplementedError("Cada peça implementa o seu movimento.")

    def deslizar(self, tabuleiro, direcoes):
        destinos = []
        for dl, dc in direcoes:
            l, c = self.linha + dl, self.coluna + dc
            while dentro(l, c):
                alvo = tabuleiro.obter(l, c)
                if alvo is None or alvo.cor != self.cor:
                    destinos.append((l, c))
                if alvo is not None:
                    break
                l, c = l + dl, c + dc
        return destinos

    def saltar(self, tabuleiro, deslocamentos):
        destinos = []
        for dl, dc in deslocamentos:
            l, c = self.linha + dl, self.coluna + dc
            if dentro(l, c):
                alvo = tabuleiro.obter(l, c)
                if alvo is None or alvo.cor != self.cor:
                    destinos.append((l, c))
        return destinos


class Torre(Peca):
    nome = "Torre"
    simbolo = "\u265C"

    def movimentos(self, tabuleiro):
        return self.deslizar(tabuleiro, [(-1, 0), (1, 0), (0, -1), (0, 1)])


class Bispo(Peca):
    nome = "Bispo"
    simbolo = "\u265D"

    def movimentos(self, tabuleiro):
        return self.deslizar(tabuleiro, [(-1, -1), (-1, 1), (1, -1), (1, 1)])


class Cavalo(Peca):
    nome = "Cavalo"
    simbolo = "\u265E"

    def movimentos(self, tabuleiro):
        return self.saltar(tabuleiro, [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                                       (1, -2), (1, 2), (2, -1), (2, 1)])


class Rainha(Peca):
    nome = "Rainha"
    simbolo = "\u265B"

    def movimentos(self, tabuleiro):
        return self.deslizar(tabuleiro, [(-1, 0), (1, 0), (0, -1), (0, 1),
                                         (-1, -1), (-1, 1), (1, -1), (1, 1)])


class Rei(Peca):
    nome = "Rei"
    simbolo = "\u265A"

    def movimentos(self, tabuleiro):
        return self.saltar(tabuleiro, [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                                       (0, 1), (1, -1), (1, 0), (1, 1)])


class Peao(Peca):
    nome = "Peão"
    simbolo = "\u265F"

    def __init__(self, cor=BRANCAS, linha=0, coluna=0):
        super().__init__(cor, linha, coluna)
        self.direcao = -1 if cor == BRANCAS else 1     # brancas sobem
        self.linha_inicial = 6 if cor == BRANCAS else 1

    def movimentos(self, tabuleiro):
        destinos = []
        frente = self.linha + self.direcao
        if dentro(frente, self.coluna) and tabuleiro.obter(frente, self.coluna) is None:
            destinos.append((frente, self.coluna))
            dupla = frente + self.direcao
            if self.linha == self.linha_inicial and \
                    tabuleiro.obter(dupla, self.coluna) is None:
                destinos.append((dupla, self.coluna))
        for dc in (-1, 1):                              # capturas na diagonal
            if dentro(frente, self.coluna + dc):
                alvo = tabuleiro.obter(frente, self.coluna + dc)
                if alvo is not None and alvo.cor != self.cor:
                    destinos.append((frente, self.coluna + dc))
        return destinos


# =============================================================================
# TABULEIRO E JOGO
# =============================================================================
class Tabuleiro:
    """Matriz 8x8 de peças."""
    def __init__(self):
        self.casas = [[None] * 8 for _ in range(8)]
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

    def mover(self, origem, destino):
        peca = self.obter(*origem)
        capturada = self.obter(*destino)
        self.casas[origem[0]][origem[1]] = None
        self.colocar(peca, *destino)
        if isinstance(peca, Peao) and destino[0] in (0, 7):
            self.colocar(Rainha(peca.cor), *destino)    # promoção automática
        return capturada


class Jogo:
    def __init__(self):
        self.tabuleiro = Tabuleiro()
        self.turno = BRANCAS
        self.em_andamento = True
        self.vencedor = None

    def movimentos_da_peca(self, linha, coluna):
        if not self.em_andamento:
            raise MovimentoInvalidoError("A partida já terminou.")
        peca = self.tabuleiro.obter(linha, coluna)
        if peca is None:
            raise MovimentoInvalidoError("Não há peça nessa casa.")
        if peca.cor != self.turno:
            raise MovimentoInvalidoError(f"É a vez das {self.turno}.")
        destinos = peca.movimentos(self.tabuleiro)
        if not destinos:
            raise MovimentoInvalidoError(f"{peca.nome} sem movimentos agora.")
        return destinos

    def mover(self, origem, destino):
        if destino not in self.movimentos_da_peca(*origem):
            peca = self.tabuleiro.obter(*origem)
            raise MovimentoInvalidoError(f"{peca.nome} não pode ir para essa casa.")
        capturada = self.tabuleiro.mover(origem, destino)
        if isinstance(capturada, Rei):      # provisório: ainda sem xeque-mate
            self.em_andamento = False
            self.vencedor = self.turno
        else:
            self.turno = oposta(self.turno)


# =============================================================================
# INTERFACE (Tkinter)
# =============================================================================
class TelaMenu(tk.Frame):
    def __init__(self, master, ao_jogar, ao_sair):
        super().__init__(master, bg=COR_FUNDO)
        centro = tk.Frame(self, bg=COR_FUNDO)
        centro.pack(expand=True)
        tk.Label(centro, text="XADREZ", font=("Helvetica", 44, "bold"),
                 bg=COR_FUNDO, fg=COR_TEXTO).pack(pady=(0, 30))
        tk.Button(centro, text="Jogar", width=20, command=ao_jogar).pack(pady=6)
        tk.Button(centro, text="Sair", width=20, command=ao_sair).pack(pady=6)


class TelaJogo(tk.Frame):
    CASA = 64
    MARGEM = 20
    COR_CLARA = "#F0D9B5"
    COR_ESCURA = "#B58863"
    COR_SELECAO = "#F5E663"

    def __init__(self, master, ao_voltar, fonte):
        super().__init__(master, bg=COR_FUNDO)
        self.jogo = Jogo()
        self.ao_voltar = ao_voltar
        self.fonte = (fonte, -int(self.CASA * 0.74))
        self.selecionada = None
        self.destinos = []

        self.var_status = tk.StringVar()
        tk.Label(self, textvariable=self.var_status, bg=COR_FUNDO, fg=COR_TEXTO,
                 font=("Helvetica", 14, "bold")).pack(pady=(10, 0))
        lado = 8 * self.CASA + 2 * self.MARGEM
        self.canvas = tk.Canvas(self, width=lado, height=lado, bg=COR_FUNDO,
                                highlightthickness=0)
        self.canvas.pack(pady=6)
        self.canvas.bind("<Button-1>", self.ao_clicar)
        tk.Button(self, text="Voltar ao menu", command=self.ao_voltar).pack()
        self.desenhar()

    def desenhar(self):
        self.canvas.delete("all")
        t, m = self.CASA, self.MARGEM
        for linha in range(8):
            for coluna in range(8):
                cor = self.COR_CLARA if (linha + coluna) % 2 == 0 else self.COR_ESCURA
                if self.selecionada == (linha, coluna):
                    cor = self.COR_SELECAO
                x, y = m + coluna * t, m + linha * t
                self.canvas.create_rectangle(x, y, x + t, y + t, fill=cor, outline=cor)
                if (linha, coluna) in self.destinos:        # bolinha de destino
                    self.canvas.create_oval(x + 24, y + 24, x + 40, y + 40,
                                            fill="#5E8C31", outline="")
                peca = self.jogo.tabuleiro.obter(linha, coluna)
                if peca is not None:
                    self.desenhar_peca(peca, x + t / 2, y + t / 2)
        if self.jogo.em_andamento:
            self.var_status.set(f"Vez das {self.jogo.turno}")
        else:
            self.var_status.set(f"Fim de jogo! As {self.jogo.vencedor} venceram")

    def desenhar_peca(self, peca, cx, cy):
        if peca.cor == BRANCAS:
            for dx, dy in ((-1.5, 0), (1.5, 0), (0, -1.5), (0, 1.5)):
                self.canvas.create_text(cx + dx, cy + dy, text=peca.simbolo,
                                        font=self.fonte, fill="black")
        self.canvas.create_text(cx, cy, text=peca.simbolo, font=self.fonte,
                                fill="white" if peca.cor == BRANCAS else "#111111")

    def ao_clicar(self, evento):
        coluna = (evento.x - self.MARGEM) // self.CASA
        linha = (evento.y - self.MARGEM) // self.CASA
        if not dentro(linha, coluna):
            return
        try:
            self.tratar_clique(linha, coluna)
        except MovimentoInvalidoError as erro:
            messagebox.showwarning("Movimento inválido", erro, parent=self)

    def tratar_clique(self, linha, coluna):
        clicada = (linha, coluna)
        peca = self.jogo.tabuleiro.obter(linha, coluna)
        if self.selecionada is None or (peca and peca.cor == self.jogo.turno):
            self.destinos = self.jogo.movimentos_da_peca(linha, coluna)  # valida
            self.selecionada = clicada
        else:
            self.jogo.mover(self.selecionada, clicada)
            self.selecionada, self.destinos = None, []
        self.desenhar()
        if not self.jogo.em_andamento:
            messagebox.showinfo("Fim de jogo", self.var_status.get(), parent=self)


class ChessApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Xadrez \u2014 Python & Tkinter")
        self.configure(bg=COR_FUNDO)
        self.geometry("620x700")

        self.fonte = "Segoe UI Symbol" if sys.platform == "win32" else "DejaVu Sans"

        barra = tk.Menu(self)
        arquivo = tk.Menu(barra, tearoff=0)
        arquivo.add_command(label="Sair", command=self.confirmar_saida)
        barra.add_cascade(label="Arquivo", menu=arquivo)
        ajuda = tk.Menu(barra, tearoff=0)
        ajuda.add_command(label="Sobre", command=self.mostrar_sobre)
        barra.add_cascade(label="Ajuda", menu=ajuda)
        self.config(menu=barra)

        self.container = tk.Frame(self, bg=COR_FUNDO)
        self.container.pack(fill="both", expand=True)
        self.tela_menu = TelaMenu(self.container, self.iniciar_partida,
                                  self.confirmar_saida)
        self.tela_jogo = None
        self.tela_atual = None
        self.mostrar(self.tela_menu)
        self.protocol("WM_DELETE_WINDOW", self.confirmar_saida)

    def mostrar(self, tela):
        if self.tela_atual is not None:
            self.tela_atual.pack_forget()
        tela.pack(fill="both", expand=True)
        self.tela_atual = tela

    def iniciar_partida(self):
        if self.tela_jogo is not None:
            self.tela_jogo.destroy()
        self.tela_jogo = TelaJogo(self.container,
                                  lambda: self.mostrar(self.tela_menu), self.fonte)
        self.mostrar(self.tela_jogo)

    def confirmar_saida(self):
        if messagebox.askyesno("Sair", "Deseja realmente sair do jogo?", parent=self):
            self.destroy()

    def mostrar_sobre(self):
        # TODO: trocar por uma janela tk.Toplevel
        messagebox.showinfo("Sobre", "Xadrez PvP - Python + Tkinter\nVersão 0.1",
                            parent=self)


if __name__ == "__main__":
    ChessApp().mainloop()
