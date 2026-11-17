"""
XADREZ - Jogador vs. Jogador (PvP)

Já funciona: peças com herança/polimorfismo, tabuleiro desenhado no Canvas,
mover clicando e alternância de turnos.
Falta: menu inicial, classe Jogo, menu superior, promoção do peão, xeque,
xeque-mate, roque, en passant e histórico de lances.
"""

import sys
import tkinter as tk
from tkinter import messagebox

BRANCAS = "brancas"
PRETAS = "pretas"


def dentro(linha, coluna):
    return 0 <= linha < 8 and 0 <= coluna < 8


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
        self.direcao = -1 if cor == BRANCAS else 1      # brancas sobem
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
# TABULEIRO
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
        """Move a peça e devolve a peça capturada (ou None)."""
        capturada = self.obter(*destino)
        peca = self.obter(*origem)
        self.casas[origem[0]][origem[1]] = None
        self.colocar(peca, *destino)
        return capturada


# =============================================================================
# INTERFACE
# =============================================================================
class ChessApp(tk.Tk):
    CASA = 64
    COR_CLARA = "#F0D9B5"
    COR_ESCURA = "#B58863"
    COR_SELECAO = "#F5E663"

    def __init__(self):
        super().__init__()
        self.title("Xadrez \u2014 Python & Tkinter")
        self.resizable(False, False)
        self.fonte = ("Segoe UI Symbol" if sys.platform == "win32" else "DejaVu Sans",
                      -int(self.CASA * 0.74))

        self.tabuleiro = Tabuleiro()
        self.turno = BRANCAS
        self.selecionada = None      # (linha, coluna) da peça selecionada
        self.destinos = []           # destinos possíveis dessa peça

        self.lbl_turno = tk.Label(self, font=("Helvetica", 14, "bold"))
        self.lbl_turno.pack(pady=6)
        self.canvas = tk.Canvas(self, width=8 * self.CASA, height=8 * self.CASA)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.ao_clicar)
        self.desenhar()

    def desenhar(self):
        self.canvas.delete("all")
        t = self.CASA
        for linha in range(8):
            for coluna in range(8):
                cor = self.COR_CLARA if (linha + coluna) % 2 == 0 else self.COR_ESCURA
                if self.selecionada == (linha, coluna):
                    cor = self.COR_SELECAO
                x, y = coluna * t, linha * t
                self.canvas.create_rectangle(x, y, x + t, y + t, fill=cor, outline=cor)
                if (linha, coluna) in self.destinos:
                    self.canvas.create_oval(x + 24, y + 24, x + 40, y + 40,
                                            fill="#5E8C31", outline="")
                peca = self.tabuleiro.obter(linha, coluna)
                if peca is not None:
                    self.canvas.create_text(
                        x + t / 2, y + t / 2, text=peca.simbolo, font=self.fonte,
                        fill="white" if peca.cor == BRANCAS else "black")
        self.lbl_turno.config(text=f"Vez das {self.turno}")

    def ao_clicar(self, evento):
        linha, coluna = evento.y // self.CASA, evento.x // self.CASA
        if not dentro(linha, coluna):
            return
        peca = self.tabuleiro.obter(linha, coluna)

        if peca is not None and peca.cor == self.turno:      # (re)seleciona
            self.selecionada = (linha, coluna)
            self.destinos = peca.movimentos(self.tabuleiro)
        elif self.selecionada is None:
            messagebox.showwarning("Movimento inválido",
                                   f"Selecione uma peça das {self.turno}.")
        elif (linha, coluna) not in self.destinos:
            messagebox.showwarning("Movimento inválido",
                                   "Essa peça não pode ir para essa casa.")
        else:                                                # move
            capturada = self.tabuleiro.mover(self.selecionada, (linha, coluna))
            self.selecionada, self.destinos = None, []
            if isinstance(capturada, Rei):                   # provisório
                self.desenhar()
                messagebox.showinfo("Fim de jogo", f"As {self.turno} venceram!")
                self.tabuleiro = Tabuleiro()
                self.turno = PRETAS                          # volta p/ brancas abaixo
            self.turno = PRETAS if self.turno == BRANCAS else BRANCAS
        self.desenhar()


if __name__ == "__main__":
    ChessApp().mainloop()
