"""
==============================================================================
 XADREZ  -  Jogador vs. Jogador (PvP)
 Projeto de Programação Orientada a Objetos com Tkinter
==============================================================================


Regras implementadas: movimento de todas as peças, captura, xeque,
xeque-mate, afogamento (empate), roque curto e longo, en passant,
promoção do peão e empate por material insuficiente.

Convenção de coordenadas internas: (linha, coluna) com linha 0 = 8ª fileira
(lado das pretas, topo da tela) e linha 7 = 1ª fileira (lado das brancas).
"""

import tkinter as tk
from tkinter import messagebox
from tkinter import font as tkfont

# =============================================================================
# CONSTANTES E FUNÇÕES AUXILIARES
# =============================================================================
BRANCAS = "brancas"
PRETAS = "pretas"
LETRAS_COLUNAS = "abcdefgh"

# Paleta de cores da interface
COR_FUNDO = "#2B2926"
COR_PAINEL = "#3A3733"
COR_TEXTO = "#EDEDED"
COR_TEXTO_SUAVE = "#B5B0A8"
COR_BOTAO = "#5E8C31"
COR_BOTAO_ATIVO = "#76A84A"
COR_BOTAO_PERIGO = "#A8423A"
COR_BOTAO_PERIGO_ATIVO = "#C2584F"
COR_BOTAO_NEUTRO = "#55524D"
COR_BOTAO_NEUTRO_ATIVO = "#6B6862"


def oposta(cor):
    """Devolve a cor adversária."""
    return PRETAS if cor == BRANCAS else BRANCAS


def dentro_do_tabuleiro(linha, coluna):
    """Verifica se (linha, coluna) é uma casa válida do tabuleiro 8x8."""
    return 0 <= linha < 8 and 0 <= coluna < 8


def para_algebrica(linha, coluna):
    """Converte (linha, coluna) internos para a notação algébrica (ex.: 'e4')."""
    return f"{LETRAS_COLUNAS[coluna]}{8 - linha}"


def centralizar(janela, largura=None, altura=None):
    """Centraliza uma janela na tela. Sem tamanho informado, usa o tamanho
    requisitado pelos próprios widgets (útil para janelas de diálogo)."""
    janela.update_idletasks()
    if largura is None:
        largura = janela.winfo_reqwidth()
    if altura is None:
        altura = janela.winfo_reqheight()
    x = (janela.winfo_screenwidth() - largura) // 2
    y = (janela.winfo_screenheight() - altura) // 3
    janela.geometry(f"{largura}x{altura}+{x}+{max(y, 0)}")


def criar_botao(master, texto, comando, cor=COR_BOTAO, cor_ativa=COR_BOTAO_ATIVO,
                largura=None, fonte=("Helvetica", 11, "bold")):
    """Fábrica de botões com aparência padronizada."""
    opcoes = dict(text=texto, command=comando, bg=cor, fg="#FFFFFF",
                  activebackground=cor_ativa, activeforeground="#FFFFFF",
                  relief="flat", bd=0, font=fonte, cursor="hand2",
                  padx=12, pady=6)
    if largura is not None:
        opcoes["width"] = largura
    return tk.Button(master, **opcoes)


# =============================================================================
# EXCEÇÃO PERSONALIZADA
# =============================================================================
class MovimentoInvalidoError(Exception):
    """Lançada quando o jogador tenta uma ação que as regras não permitem."""

    def __init__(self, mensagem="Movimento inválido!"):
        super().__init__(mensagem)
        self.mensagem = mensagem


# =============================================================================
# PEÇAS  (superclasse + 6 subclasses)
# =============================================================================
class Peca:
    """Superclasse de todas as peças do xadrez.

    Guarda o que é comum a qualquer peça (cor, posição, se já se moveu) e
    oferece utilitários de movimento (deslizar e saltar). Cada subclasse
    sobrescreve `movimentos_pseudo_legais` -> POLIMORFISMO: o tabuleiro
    chama o mesmo método em qualquer peça e cada uma responde à sua maneira.

    "Pseudo-legais" = respeitam o jeito de andar da peça, mas ainda NÃO
    consideram se o próprio Rei ficaria em xeque (isso é tarefa do Tabuleiro).
    """

    nome = "Peça"
    artigo = "a"           # artigo do nome ("a Torre", "o Bispo") p/ mensagens
    letra = "?"            # letra usada na notação dos lances (PT-BR)
    simbolo_cheio = "?"    # glifo Unicode preenchido
    simbolo_vazado = "?"   # glifo Unicode vazado
    valor = 0              # valor material (usado para ordenar as capturas)

    def __init__(self, cor=BRANCAS, linha=0, coluna=0):
        # Atributos "protegidos" (prefixo _): acesso externo via properties.
        self._cor = cor
        self._linha = linha
        self._coluna = coluna
        self._ja_moveu = False

    # ---- Encapsulamento: leitura controlada dos atributos -----------------
    @property
    def cor(self):
        return self._cor

    @property
    def linha(self):
        return self._linha

    @property
    def coluna(self):
        return self._coluna

    @property
    def ja_moveu(self):
        return self._ja_moveu

    @property
    def simbolo(self):
        """Glifo para exibição em textos (vazado p/ brancas, cheio p/ pretas)."""
        return self.simbolo_vazado if self._cor == BRANCAS else self.simbolo_cheio

    # ---- Modificadores controlados ---------------------------------------
    def posicionar(self, linha, coluna):
        """Atualiza a posição da peça (chamado pelo Tabuleiro)."""
        self._linha = linha
        self._coluna = coluna

    def marcar_como_movida(self):
        """Registra que a peça já se moveu (importante para o roque)."""
        self._ja_moveu = True

    # ---- Comportamento polimórfico ----------------------------------------
    def movimentos_pseudo_legais(self, tabuleiro):
        """Lista de destinos (linha, coluna) possíveis. Cada subclasse implementa."""
        raise NotImplementedError("Cada peça deve implementar seu movimento.")

    def casas_atacadas(self, tabuleiro):
        """Casas que a peça ameaça. Por padrão, são as mesmas casas de movimento.
        (Peão e Rei sobrescrevem este método, pois diferem nesse ponto.)"""
        return self.movimentos_pseudo_legais(tabuleiro)

    # ---- Utilitários reutilizados pelas subclasses -------------------------
    def _deslizar(self, tabuleiro, direcoes):
        """Movimento em linha reta até encontrar obstáculo (Torre/Bispo/Rainha)."""
        destinos = []
        for d_linha, d_coluna in direcoes:
            linha = self._linha + d_linha
            coluna = self._coluna + d_coluna
            while dentro_do_tabuleiro(linha, coluna):
                alvo = tabuleiro.obter(linha, coluna)
                if alvo is None:
                    destinos.append((linha, coluna))
                else:
                    if alvo.cor != self._cor:      # pode capturar peça adversária
                        destinos.append((linha, coluna))
                    break                           # obstáculo: para de deslizar
                linha += d_linha
                coluna += d_coluna
        return destinos

    def _saltar(self, tabuleiro, deslocamentos):
        """Movimento por deslocamentos fixos (Cavalo e Rei)."""
        destinos = []
        for d_linha, d_coluna in deslocamentos:
            linha = self._linha + d_linha
            coluna = self._coluna + d_coluna
            if dentro_do_tabuleiro(linha, coluna):
                alvo = tabuleiro.obter(linha, coluna)
                if alvo is None or alvo.cor != self._cor:
                    destinos.append((linha, coluna))
        return destinos

    # ---- Representações textuais -------------------------------------------
    def __str__(self):
        return (f"{self.nome} das {self._cor} em "
                f"{para_algebrica(self._linha, self._coluna)}")

    def __repr__(self):
        return (f"<{self.__class__.__name__} {self._cor} "
                f"{para_algebrica(self._linha, self._coluna)}>")


class Torre(Peca):
    """Move-se quantas casas quiser na horizontal ou vertical."""
    nome = "Torre"
    letra = "T"
    simbolo_cheio = "\u265C"
    simbolo_vazado = "\u2656"
    valor = 5

    def __init__(self, cor=BRANCAS, linha=0, coluna=0):
        super().__init__(cor, linha, coluna)

    def movimentos_pseudo_legais(self, tabuleiro):
        return self._deslizar(tabuleiro, [(-1, 0), (1, 0), (0, -1), (0, 1)])


class Bispo(Peca):
    """Move-se quantas casas quiser nas diagonais."""
    nome = "Bispo"
    artigo = "o"
    letra = "B"
    simbolo_cheio = "\u265D"
    simbolo_vazado = "\u2657"
    valor = 3

    def __init__(self, cor=BRANCAS, linha=0, coluna=0):
        super().__init__(cor, linha, coluna)

    def movimentos_pseudo_legais(self, tabuleiro):
        return self._deslizar(tabuleiro, [(-1, -1), (-1, 1), (1, -1), (1, 1)])


class Cavalo(Peca):
    """Move-se em 'L' e é a única peça que salta sobre as outras."""
    nome = "Cavalo"
    artigo = "o"
    letra = "C"
    simbolo_cheio = "\u265E"
    simbolo_vazado = "\u2658"
    valor = 3

    DESLOCAMENTOS = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                     (1, -2), (1, 2), (2, -1), (2, 1)]

    def __init__(self, cor=BRANCAS, linha=0, coluna=0):
        super().__init__(cor, linha, coluna)

    def movimentos_pseudo_legais(self, tabuleiro):
        return self._saltar(tabuleiro, self.DESLOCAMENTOS)


class Rainha(Peca):
    """Combina os movimentos da Torre e do Bispo."""
    nome = "Rainha"
    letra = "D"   # "Dama" na notação brasileira
    simbolo_cheio = "\u265B"
    simbolo_vazado = "\u2655"
    valor = 9

    DIRECOES = [(-1, 0), (1, 0), (0, -1), (0, 1),
                (-1, -1), (-1, 1), (1, -1), (1, 1)]

    def __init__(self, cor=BRANCAS, linha=0, coluna=0):
        super().__init__(cor, linha, coluna)

    def movimentos_pseudo_legais(self, tabuleiro):
        return self._deslizar(tabuleiro, self.DIRECOES)


class Rei(Peca):
    """Move-se uma casa em qualquer direção e pode fazer o roque."""
    nome = "Rei"
    artigo = "o"
    letra = "R"
    simbolo_cheio = "\u265A"
    simbolo_vazado = "\u2654"
    valor = 0

    DESLOCAMENTOS = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                     (0, 1), (1, -1), (1, 0), (1, 1)]

    def __init__(self, cor=BRANCAS, linha=0, coluna=0):
        super().__init__(cor, linha, coluna)

    def casas_atacadas(self, tabuleiro):
        """O Rei ameaça apenas as casas vizinhas (o roque nunca captura)."""
        return self._saltar(tabuleiro, self.DESLOCAMENTOS)

    def movimentos_pseudo_legais(self, tabuleiro):
        destinos = self.casas_atacadas(tabuleiro)
        destinos.extend(self._roques_possiveis(tabuleiro))
        return destinos

    def _roques_possiveis(self, tabuleiro):
        """Casas de destino do Rei caso o roque seja permitido.

        Condições: Rei e Torre nunca se moveram; casas entre eles vazias;
        Rei fora de xeque e sem passar/chegar a casas atacadas.
        """
        destinos = []
        if self.ja_moveu or self.coluna != 4:
            return destinos
        linha = self.linha
        adversaria = oposta(self.cor)
        if tabuleiro.casa_atacada(linha, self.coluna, adversaria):
            return destinos  # não é permitido fazer roque em xeque

        # (coluna da torre, casas que devem estar vazias,
        #  casas que o rei atravessa, coluna de destino do rei)
        configuracoes = (
            (7, (5, 6), (5, 6), 6),        # roque curto (lado do rei)
            (0, (1, 2, 3), (3, 2), 2),     # roque longo (lado da dama)
        )
        for col_torre, vazias, atravessadas, destino in configuracoes:
            torre = tabuleiro.obter(linha, col_torre)
            if not isinstance(torre, Torre) or torre.cor != self.cor or torre.ja_moveu:
                continue
            if any(tabuleiro.obter(linha, c) is not None for c in vazias):
                continue
            if any(tabuleiro.casa_atacada(linha, c, adversaria) for c in atravessadas):
                continue
            destinos.append((linha, destino))
        return destinos


class Peao(Peca):
    """Avança uma casa (duas no primeiro lance) e captura na diagonal."""
    nome = "Peão"
    artigo = "o"
    letra = ""    # na notação, o peão não leva letra
    simbolo_cheio = "\u265F"
    simbolo_vazado = "\u2659"
    valor = 1

    def __init__(self, cor=BRANCAS, linha=0, coluna=0):
        super().__init__(cor, linha, coluna)
        # Brancas sobem (linha diminui); pretas descem (linha aumenta).
        self._direcao = -1 if cor == BRANCAS else 1
        self._linha_inicial = 6 if cor == BRANCAS else 1

    def casas_atacadas(self, tabuleiro):
        """O peão ameaça as duas diagonais à frente (mesmo que estejam vazias)."""
        destinos = []
        linha = self._linha + self._direcao
        for d_coluna in (-1, 1):
            coluna = self._coluna + d_coluna
            if dentro_do_tabuleiro(linha, coluna):
                destinos.append((linha, coluna))
        return destinos

    def movimentos_pseudo_legais(self, tabuleiro):
        destinos = []
        # 1) Avanço simples e duplo (só para casas vazias)
        frente = self._linha + self._direcao
        if dentro_do_tabuleiro(frente, self._coluna) and \
                tabuleiro.obter(frente, self._coluna) is None:
            destinos.append((frente, self._coluna))
            dupla = frente + self._direcao
            if self._linha == self._linha_inicial and \
                    tabuleiro.obter(dupla, self._coluna) is None:
                destinos.append((dupla, self._coluna))
        # 2) Capturas na diagonal (inclui en passant)
        for linha, coluna in self.casas_atacadas(tabuleiro):
            alvo = tabuleiro.obter(linha, coluna)
            if alvo is not None and alvo.cor != self._cor:
                destinos.append((linha, coluna))
            elif alvo is None and tabuleiro.alvo_en_passant == (linha, coluna):
                destinos.append((linha, coluna))
        return destinos


# =============================================================================
# LANCE (registro de um movimento)
# =============================================================================
class Lance:
    """Guarda tudo o que aconteceu em um movimento e sabe se escrever
    em notação algébrica longa (ex.: 'Cb1-c3', 'e4xd5', 'O-O', 'e7-e8=D#')."""

    def __init__(self, peca=None, origem=(0, 0), destino=(0, 0), capturada=None,
                 roque=None, en_passant=False, promocao=None):
        self.peca = peca
        self.origem = origem
        self.destino = destino
        self.capturada = capturada
        self.roque = roque              # None, "curto" ou "longo"
        self.en_passant = en_passant
        self.promocao = promocao        # classe da peça promovida (ou None)
        self.sufixo = ""                # "+" (xeque) ou "#" (xeque-mate)

    def __str__(self):
        if self.roque == "curto":
            texto = "O-O"
        elif self.roque == "longo":
            texto = "O-O-O"
        else:
            separador = "x" if self.capturada is not None else "-"
            texto = (f"{self.peca.letra}{para_algebrica(*self.origem)}"
                     f"{separador}{para_algebrica(*self.destino)}")
            if self.promocao is not None:
                texto += f"={self.promocao.letra}"
        return texto + self.sufixo


# =============================================================================
# TABULEIRO
# =============================================================================
class Tabuleiro:
    """Matriz 8x8 de peças + todas as regras que dependem do conjunto do
    tabuleiro (xeque, movimentos legais, execução de lances especiais)."""

    def __init__(self, preencher=True):
        self._casas = [[None for _ in range(8)] for _ in range(8)]
        self.alvo_en_passant = None   # casa "pulada" por um peão no último lance
        if preencher:
            self.posicionar_pecas_iniciais()

    # ---- Montagem -----------------------------------------------------------
    def posicionar_pecas_iniciais(self):
        """Limpa o tabuleiro e coloca as 32 peças na posição inicial."""
        self._casas = [[None for _ in range(8)] for _ in range(8)]
        self.alvo_en_passant = None
        ordem = [Torre, Cavalo, Bispo, Rainha, Rei, Bispo, Cavalo, Torre]
        for coluna, classe in enumerate(ordem):
            # Polimorfismo: 'classe' pode ser qualquer subclasse de Peca.
            self.colocar(classe(PRETAS, 0, coluna), 0, coluna)
            self.colocar(classe(BRANCAS, 7, coluna), 7, coluna)
        for coluna in range(8):
            self.colocar(Peao(PRETAS, 1, coluna), 1, coluna)
            self.colocar(Peao(BRANCAS, 6, coluna), 6, coluna)

    def colocar(self, peca, linha, coluna):
        """Coloca uma peça (ou None) numa casa e atualiza a posição da peça."""
        self._casas[linha][coluna] = peca
        if peca is not None:
            peca.posicionar(linha, coluna)

    def obter(self, linha, coluna):
        """Devolve a peça da casa (ou None se estiver vazia)."""
        return self._casas[linha][coluna]

    # ---- Consultas ------------------------------------------------------------
    def todas_as_pecas(self):
        return [p for fileira in self._casas for p in fileira if p is not None]

    def pecas_da_cor(self, cor):
        return [p for p in self.todas_as_pecas() if p.cor == cor]

    def localizar_rei(self, cor):
        for peca in self.pecas_da_cor(cor):
            if isinstance(peca, Rei):
                return peca
        return None

    def casa_atacada(self, linha, coluna, cor_atacante):
        """True se alguma peça de `cor_atacante` ameaça a casa indicada."""
        alvo = (linha, coluna)
        for peca in self.pecas_da_cor(cor_atacante):
            if alvo in peca.casas_atacadas(self):
                return True
        return False

    def em_xeque(self, cor):
        """True se o Rei da cor informada está sob ataque."""
        rei = self.localizar_rei(cor)
        return rei is not None and self.casa_atacada(rei.linha, rei.coluna, oposta(cor))

    # ---- Movimentos legais ----------------------------------------------------
    def _deixa_rei_em_xeque(self, peca, destino):
        """Simula o movimento, verifica se o Rei próprio fica em xeque e desfaz."""
        l_origem, c_origem = peca.linha, peca.coluna
        l_destino, c_destino = destino
        capturada = self._casas[l_destino][c_destino]
        capturada_en_passant = None

        # En passant: o peão capturado está ao lado da origem, não no destino.
        if isinstance(peca, Peao) and c_origem != c_destino and capturada is None:
            capturada_en_passant = self._casas[l_origem][c_destino]
            self._casas[l_origem][c_destino] = None

        self._casas[l_origem][c_origem] = None
        self._casas[l_destino][c_destino] = peca
        peca.posicionar(l_destino, c_destino)
        try:
            return self.em_xeque(peca.cor)
        finally:  # desfaz a simulação, aconteça o que acontecer
            peca.posicionar(l_origem, c_origem)
            self._casas[l_origem][c_origem] = peca
            self._casas[l_destino][c_destino] = capturada
            if capturada_en_passant is not None:
                self._casas[l_origem][c_destino] = capturada_en_passant

    def movimentos_legais(self, peca):
        """Destinos válidos da peça: pseudo-legais que não expõem o próprio Rei."""
        return [destino for destino in peca.movimentos_pseudo_legais(self)
                if not self._deixa_rei_em_xeque(peca, destino)]

    def possui_movimento_legal(self, cor):
        """True se a cor ainda tem ao menos um movimento legal."""
        for peca in self.pecas_da_cor(cor):
            if self.movimentos_legais(peca):
                return True
        return False

    @staticmethod
    def eh_promocao(peca, destino):
        """True se o movimento leva um peão até a última fileira."""
        return isinstance(peca, Peao) and destino[0] in (0, 7)

    def material_insuficiente(self):
        """Detecta posições onde é impossível dar xeque-mate."""
        restantes = [p for p in self.todas_as_pecas() if not isinstance(p, Rei)]
        if not restantes:                                   # Rei x Rei
            return True
        if len(restantes) == 1 and isinstance(restantes[0], (Bispo, Cavalo)):
            return True                                     # Rei + peça menor x Rei
        if all(isinstance(p, Bispo) for p in restantes):    # bispos na mesma cor
            return len({(p.linha + p.coluna) % 2 for p in restantes}) == 1
        return False

    # ---- Execução de um lance ------------------------------------------------
    def executar_movimento(self, origem, destino, classe_promocao=Rainha):
        """Executa o lance (já validado) e devolve um objeto Lance."""
        l_origem, c_origem = origem
        l_destino, c_destino = destino
        peca = self._casas[l_origem][c_origem]
        capturada = self._casas[l_destino][c_destino]
        lance = Lance(peca, origem, destino)

        # En passant: remove o peão que foi "ultrapassado".
        if isinstance(peca, Peao) and c_origem != c_destino and capturada is None:
            capturada = self._casas[l_origem][c_destino]
            self._casas[l_origem][c_destino] = None
            lance.en_passant = True
        lance.capturada = capturada

        # Roque: o Rei anda duas casas e a Torre pula para o outro lado dele.
        if isinstance(peca, Rei) and abs(c_destino - c_origem) == 2:
            if c_destino > c_origem:
                col_torre_origem, col_torre_destino, lance.roque = 7, 5, "curto"
            else:
                col_torre_origem, col_torre_destino, lance.roque = 0, 3, "longo"
            torre = self._casas[l_origem][col_torre_origem]
            self._casas[l_origem][col_torre_origem] = None
            self.colocar(torre, l_origem, col_torre_destino)
            torre.marcar_como_movida()

        # Movimento principal
        self._casas[l_origem][c_origem] = None
        self.colocar(peca, l_destino, c_destino)
        peca.marcar_como_movida()

        # Promoção do peão
        if self.eh_promocao(peca, destino):
            nova = classe_promocao(peca.cor, l_destino, c_destino)
            nova.marcar_como_movida()
            self.colocar(nova, l_destino, c_destino)
            lance.promocao = classe_promocao

        # Atualiza a casa de en passant (só vale para o lance seguinte)
        if isinstance(peca, Peao) and abs(l_destino - l_origem) == 2:
            self.alvo_en_passant = ((l_origem + l_destino) // 2, c_origem)
        else:
            self.alvo_en_passant = None
        return lance

    # ---- Representação textual -------------------------------------------------
    def __str__(self):
        linhas = []
        for linha in range(8):
            simbolos = [p.simbolo if p is not None else "\u00b7"
                        for p in self._casas[linha]]
            linhas.append(f"{8 - linha}  " + " ".join(simbolos))
        linhas.append("   " + " ".join(LETRAS_COLUNAS))
        return "\n".join(linhas)


# =============================================================================
# JOGO (controle de partida)
# =============================================================================
class Jogo:
    """Controla turnos, histórico, capturas e a situação da partida.
    Não conhece o Tkinter: toda a lógica pode ser testada sem interface."""

    ESTADOS_ENCERRADOS = ("xeque_mate", "afogamento",
                          "material_insuficiente", "desistencia")

    def __init__(self):
        self.tabuleiro = Tabuleiro()
        self.reiniciar()

    def reiniciar(self):
        """Volta tudo ao estado inicial (nova partida)."""
        self.tabuleiro.posicionar_pecas_iniciais()
        self.turno = BRANCAS
        self.historico = []                      # lista de objetos Lance
        self.capturadas = {BRANCAS: [], PRETAS: []}   # peças PERDIDAS por cada cor
        self.estado = "em_andamento"
        self.vencedor = None
        self.ultimo_lance = None

    @property
    def em_andamento(self):
        return self.estado not in self.ESTADOS_ENCERRADOS

    # ---- Validações -------------------------------------------------------------
    def movimentos_da_peca(self, linha, coluna):
        """Movimentos legais da peça em (linha, coluna) para o jogador da vez.
        Lança MovimentoInvalidoError se a seleção não for permitida."""
        if not self.em_andamento:
            raise MovimentoInvalidoError(
                "A partida já terminou.\nInicie uma nova partida para jogar novamente.")
        peca = self.tabuleiro.obter(linha, coluna)
        if peca is None:
            raise MovimentoInvalidoError(
                "Não há nenhuma peça nessa casa.\nSelecione uma peça sua.")
        if peca.cor != self.turno:
            raise MovimentoInvalidoError(
                f"Essa peça pertence às {peca.cor}, mas é a vez das {self.turno}.")
        destinos = self.tabuleiro.movimentos_legais(peca)
        if not destinos:
            dica = ("\nSeu Rei está em xeque: defenda-o primeiro."
                    if self.estado == "xeque" else "")
            raise MovimentoInvalidoError(
                f"Essa peça ({peca.nome}) não tem nenhum movimento legal agora.{dica}")
        return destinos

    # ---- Execução de um movimento ---------------------------------------------
    def mover(self, origem, destino, classe_promocao=Rainha):
        """Valida e executa o movimento. Troca o turno e reavalia a partida."""
        legais = self.movimentos_da_peca(*origem)
        if destino not in legais:
            peca = self.tabuleiro.obter(*origem)
            nome_casa = para_algebrica(*destino)
            if destino in peca.movimentos_pseudo_legais(self.tabuleiro):
                if self.tabuleiro.em_xeque(self.turno):
                    raise MovimentoInvalidoError(
                        "Seu Rei está em xeque!\nVocê precisa tirá-lo do ataque: "
                        "mover o Rei, capturar o atacante ou bloquear a linha.")
                raise MovimentoInvalidoError(
                    "Esse movimento deixaria seu próprio Rei em xeque, "
                    "o que é proibido.")
            raise MovimentoInvalidoError(
                f"{peca.artigo.capitalize()} {peca.nome} não pode ir para "
                f"{nome_casa}.\nEsse movimento não segue a regra dessa peça.")

        lance = self.tabuleiro.executar_movimento(origem, destino, classe_promocao)
        if lance.capturada is not None:
            self.capturadas[lance.capturada.cor].append(lance.capturada)
        self.turno = oposta(self.turno)
        self._avaliar_situacao(lance)
        self.historico.append(lance)
        self.ultimo_lance = lance
        return lance

    def _avaliar_situacao(self, lance):
        """Define se há xeque, xeque-mate ou empate após o lance."""
        cor = self.turno   # quem vai jogar agora
        em_xeque = self.tabuleiro.em_xeque(cor)
        if not self.tabuleiro.possui_movimento_legal(cor):
            if em_xeque:
                self.estado = "xeque_mate"
                self.vencedor = oposta(cor)
                lance.sufixo = "#"
            else:
                self.estado = "afogamento"
        elif self.tabuleiro.material_insuficiente():
            self.estado = "material_insuficiente"
        elif em_xeque:
            self.estado = "xeque"
            lance.sufixo = "+"
        else:
            self.estado = "em_andamento"

    def desistir(self):
        """O jogador da vez desiste; o adversário vence."""
        self.estado = "desistencia"
        self.vencedor = oposta(self.turno)

    # ---- Texto de status ---------------------------------------------------------
    def texto_status(self):
        if self.estado == "em_andamento":
            return f"Turno das {self.turno}.\nEscolha uma peça e depois o destino."
        if self.estado == "xeque":
            return f"XEQUE!\nO Rei das {self.turno} está sob ataque."
        if self.estado == "xeque_mate":
            return f"XEQUE-MATE!\nAs {self.vencedor} venceram a partida."
        if self.estado == "afogamento":
            return "EMPATE por afogamento:\nsem lances legais e sem xeque."
        if self.estado == "material_insuficiente":
            return "EMPATE por material insuficiente:\nninguém consegue dar xeque-mate."
        if self.estado == "desistencia":
            return f"As {self.turno} desistiram.\nAs {self.vencedor} venceram a partida."
        return ""

    def __str__(self):
        return (f"Jogo(turno={self.turno}, lances={len(self.historico)}, "
                f"estado={self.estado})")


# =============================================================================
# JANELAS SECUNDÁRIAS (tk.Toplevel)
# =============================================================================
class DialogoPromocao(tk.Toplevel):
    """Janela modal para escolher a peça em que o peão será promovido."""

    OPCOES = (Rainha, Torre, Bispo, Cavalo)

    def __init__(self, master=None, cor=BRANCAS, familia_fonte="Arial"):
        super().__init__(master, bg=COR_FUNDO)
        self.title("Promoção do peão")
        self.resizable(False, False)
        self.escolha = Rainha                    # padrão caso feche a janela
        if master is not None:
            self.transient(master.winfo_toplevel())

        tk.Label(self, text="Escolha a peça para a promoção:",
                 bg=COR_FUNDO, fg=COR_TEXTO,
                 font=("Helvetica", 11, "bold")).pack(padx=24, pady=(16, 6))

        frame = tk.Frame(self, bg=COR_FUNDO)
        frame.pack(padx=14, pady=(4, 16))
        for classe in self.OPCOES:
            exemplo = classe(cor)                # só para ler o símbolo
            # Cada opção é um mini-Frame: botão com o símbolo + nome embaixo.
            celula = tk.Frame(frame, bg=COR_FUNDO)
            celula.pack(side="left", padx=6)
            tk.Button(celula, text=exemplo.simbolo, font=(familia_fonte, 30),
                      width=2, bg="#F0D9B5", fg="#222222",
                      activebackground="#FFE9B8", relief="raised", cursor="hand2",
                      command=lambda k=classe: self._escolher(k)).pack()
            tk.Label(celula, text=classe.nome, bg=COR_FUNDO, fg=COR_TEXTO,
                     font=("Helvetica", 10)).pack(pady=(3, 0))

        self.protocol("WM_DELETE_WINDOW", lambda: self._escolher(Rainha))
        centralizar(self)
        try:
            self.wait_visibility()
            self.grab_set()                      # torna a janela modal
        except tk.TclError:
            pass
        self.focus_set()

    def _escolher(self, classe):
        self.escolha = classe
        self.destroy()


class JanelaSobre(tk.Toplevel):
    """Janela 'Ajuda -> Sobre'."""

    def __init__(self, master=None, familia_fonte="Arial"):
        super().__init__(master, bg=COR_FUNDO)
        self.title("Sobre o Xadrez")
        self.resizable(False, False)
        if master is not None:
            self.transient(master)

        tk.Label(self, text="\u265E", font=(familia_fonte, 44),
                 bg=COR_FUNDO, fg=COR_TEXTO).pack(pady=(16, 0))
        tk.Label(self, text="Xadrez  \u2022  Python + Tkinter",
                 font=("Helvetica", 15, "bold"),
                 bg=COR_FUNDO, fg=COR_TEXTO).pack()
        tk.Label(self, text="Versão 1.0", font=("Helvetica", 10),
                 bg=COR_FUNDO, fg=COR_TEXTO_SUAVE).pack(pady=(0, 10))

        descricao = (
            "Jogo de xadrez para dois jogadores no mesmo computador,\n"
            "desenvolvido para demonstrar Programação Orientada a Objetos:\n"
            "classes, herança, polimorfismo, super(), encapsulamento\n"
            "e interface gráfica com Tkinter.\n\n"
            "Regras: roque, en passant, promoção, xeque, xeque-mate,\n"
            "afogamento e empate por material insuficiente."
        )
        tk.Label(self, text=descricao, justify="center", bg=COR_FUNDO,
                 fg=COR_TEXTO, font=("Helvetica", 10)).pack(padx=28)

        criar_botao(self, "Fechar", self.destroy, largura=12).pack(pady=16)

        self.bind("<Escape>", lambda evento: self.destroy())
        centralizar(self)
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        self.focus_set()


# =============================================================================
# TELAS (tk.Frame)
# =============================================================================
class TelaMenu(tk.Frame):
    """Menu principal. Todos os widgets usam pack() dentro deste Frame."""

    def __init__(self, master=None, ao_jogar=None, ao_sair=None,
                 familia_fonte="Arial"):
        super().__init__(master, bg=COR_FUNDO)

        # Frame interno com expand=True centraliza o conteúdo verticalmente.
        centro = tk.Frame(self, bg=COR_FUNDO)
        centro.pack(expand=True)

        tk.Label(centro, text="\u265A \u265B \u265C", font=(familia_fonte, 46),
                 bg=COR_FUNDO, fg="#D9B26F").pack()
        tk.Label(centro, text="XADREZ", font=("Helvetica", 44, "bold"),
                 bg=COR_FUNDO, fg=COR_TEXTO).pack(pady=(4, 0))
        tk.Label(centro, text="Jogador  vs  Jogador", font=("Helvetica", 14),
                 bg=COR_FUNDO, fg=COR_TEXTO_SUAVE).pack(pady=(0, 36))

        criar_botao(centro, "\u25B6  Jogar", ao_jogar, largura=22,
                    fonte=("Helvetica", 14, "bold")).pack(pady=8)
        criar_botao(centro, "Sair", ao_sair, cor=COR_BOTAO_PERIGO,
                    cor_ativa=COR_BOTAO_PERIGO_ATIVO, largura=22,
                    fonte=("Helvetica", 14, "bold")).pack(pady=8)

        tk.Label(self, text="Projeto de Programação Orientada a Objetos com Tkinter",
                 font=("Helvetica", 9), bg=COR_FUNDO,
                 fg=COR_TEXTO_SUAVE).pack(side="bottom", pady=12)


class TelaJogo(tk.Frame):
    """Tela da partida.

    Organização dos gerenciadores de geometria (sem misturar no mesmo contêiner):
      - TelaJogo (self)        -> grid : [tabuleiro | painel lateral]
      - frame_tabuleiro        -> pack : apenas o Canvas
      - painel lateral         -> pack : seções empilhadas
      - frame de capturas      -> grid : rótulos em linhas
      - frame do histórico     -> pack : Listbox + Scrollbar
      - frame dos botões       -> grid : botões em coluna
    """

    TAMANHO_CASA = 64
    MARGEM = 22

    COR_CLARA = "#F0D9B5"
    COR_ESCURA = "#B58863"
    COR_ULT_CLARA = "#CED26B"      # destaque do último lance (casa clara)
    COR_ULT_ESCURA = "#AAA23A"     # destaque do último lance (casa escura)
    COR_SELECAO = "#F5E663"
    COR_XEQUE = "#E8584F"
    COR_DICA = "#5E8C31"

    def __init__(self, master=None, ao_voltar=None, familia_fonte="Arial"):
        super().__init__(master, bg=COR_FUNDO)
        self.jogo = Jogo()
        self.ao_voltar = ao_voltar
        self.familia_fonte = familia_fonte
        # Tamanho negativo no Tk = tamanho em pixels.
        self.fonte_pecas = (familia_fonte, -int(self.TAMANHO_CASA * 0.74))
        self.selecionada = None      # (linha, coluna) da peça selecionada
        self.destinos = []           # destinos legais da peça selecionada

        self._criar_widgets()
        self.desenhar()
        self.atualizar_painel()

    # ---- Construção da interface -----------------------------------------------
    def _criar_widgets(self):
        lado = 8 * self.TAMANHO_CASA + 2 * self.MARGEM

        # ===== Seção 1: tabuleiro (coluna 0 do grid) =====
        self.frame_tabuleiro = tk.Frame(self, bg=COR_FUNDO)
        self.frame_tabuleiro.grid(row=0, column=0, padx=(14, 6), pady=12, sticky="n")

        self.canvas = tk.Canvas(self.frame_tabuleiro, width=lado, height=lado,
                                bg=COR_FUNDO, highlightthickness=0, cursor="hand2")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.ao_clicar)

        # ===== Seção 2: painel lateral (coluna 1 do grid) =====
        self.painel = tk.Frame(self, bg=COR_PAINEL, padx=12, pady=12)
        self.painel.grid(row=0, column=1, padx=(6, 14), pady=12, sticky="nsew")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        tk.Label(self.painel, text="PARTIDA", font=("Helvetica", 10, "bold"),
                 bg=COR_PAINEL, fg=COR_TEXTO_SUAVE).pack(anchor="w")

        self.lbl_turno = tk.Label(self.painel, text="", width=22, pady=8,
                                  font=("Helvetica", 14, "bold"))
        self.lbl_turno.pack(fill="x", pady=(2, 6))

        self.var_mensagem = tk.StringVar()
        tk.Label(self.painel, textvariable=self.var_mensagem, height=3,
                 wraplength=250, justify="left", anchor="nw",
                 bg=COR_PAINEL, fg=COR_TEXTO,
                 font=("Helvetica", 10)).pack(fill="x", pady=(0, 6))

        # --- Peças capturadas (grid dentro de um LabelFrame) ---
        frame_cap = tk.LabelFrame(self.painel, text=" Peças capturadas ",
                                  bg=COR_PAINEL, fg=COR_TEXTO_SUAVE,
                                  padx=8, pady=4)
        frame_cap.pack(fill="x", pady=(0, 8))
        frame_cap.columnconfigure(0, weight=1)

        self.var_cap_brancas = tk.StringVar(value="\u2014")
        self.var_cap_pretas = tk.StringVar(value="\u2014")
        estilo_titulo = dict(bg=COR_PAINEL, fg=COR_TEXTO_SUAVE, font=("Helvetica", 9))
        estilo_pecas = dict(bg=COR_PAINEL, fg=COR_TEXTO, height=2, wraplength=250,
                            justify="left", anchor="nw",
                            font=(self.familia_fonte, 14))

        tk.Label(frame_cap, text="Capturadas pelas brancas:",
                 **estilo_titulo).grid(row=0, column=0, sticky="w")
        tk.Label(frame_cap, textvariable=self.var_cap_brancas,
                 **estilo_pecas).grid(row=1, column=0, sticky="w")
        tk.Label(frame_cap, text="Capturadas pelas pretas:",
                 **estilo_titulo).grid(row=2, column=0, sticky="w")
        tk.Label(frame_cap, textvariable=self.var_cap_pretas,
                 **estilo_pecas).grid(row=3, column=0, sticky="w")

        # --- Histórico de lances (pack: Listbox + Scrollbar) ---
        frame_hist = tk.LabelFrame(self.painel, text=" Histórico de lances ",
                                   bg=COR_PAINEL, fg=COR_TEXTO_SUAVE,
                                   padx=6, pady=6)
        frame_hist.pack(fill="both", expand=True)

        barra = tk.Scrollbar(frame_hist, orient="vertical")
        self.lista_historico = tk.Listbox(
            frame_hist, width=30, height=4, bg="#262421", fg=COR_TEXTO,
            font=("Courier", 10), bd=0, highlightthickness=0,
            selectbackground="#262421", activestyle="none",
            yscrollcommand=barra.set)
        barra.config(command=self.lista_historico.yview)
        barra.pack(side="right", fill="y")
        self.lista_historico.pack(side="left", fill="both", expand=True)

        # --- Botões (grid) ---
        frame_botoes = tk.Frame(self.painel, bg=COR_PAINEL)
        frame_botoes.pack(fill="x", pady=(8, 0))
        frame_botoes.columnconfigure(0, weight=1)
        criar_botao(frame_botoes, "Nova partida", self.nova_partida).grid(
            row=0, column=0, sticky="ew", pady=2)
        criar_botao(frame_botoes, "Desistir", self.desistir,
                    cor=COR_BOTAO_PERIGO, cor_ativa=COR_BOTAO_PERIGO_ATIVO).grid(
            row=1, column=0, sticky="ew", pady=2)
        criar_botao(frame_botoes, "Voltar ao menu",
                    lambda: self.ao_voltar() if self.ao_voltar else None,
                    cor=COR_BOTAO_NEUTRO, cor_ativa=COR_BOTAO_NEUTRO_ATIVO).grid(
            row=2, column=0, sticky="ew", pady=2)

    # ---- Desenho do tabuleiro -----------------------------------------------------
    def desenhar(self):
        """Redesenha o Canvas inteiro: casas, destaques, dicas e peças."""
        self.canvas.delete("all")
        tam, margem = self.TAMANHO_CASA, self.MARGEM
        tabuleiro = self.jogo.tabuleiro
        ultimo = self.jogo.ultimo_lance

        # Casa do Rei em xeque (para destacar em vermelho)
        casa_xeque = None
        if self.jogo.estado in ("xeque", "xeque_mate"):
            rei = tabuleiro.localizar_rei(self.jogo.turno)
            if rei is not None:
                casa_xeque = (rei.linha, rei.coluna)

        # 1) Casas
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
                x0, y0 = margem + coluna * tam, margem + linha * tam
                self.canvas.create_rectangle(x0, y0, x0 + tam, y0 + tam,
                                             fill=cor, outline=cor)

        # 2) Dicas dos movimentos possíveis
        for linha, coluna in self.destinos:
            x0, y0 = margem + coluna * tam, margem + linha * tam
            if tabuleiro.obter(linha, coluna) is not None:   # captura -> anel
                self.canvas.create_oval(x0 + 4, y0 + 4, x0 + tam - 4, y0 + tam - 4,
                                        outline=self.COR_DICA, width=5)
            else:                                            # casa vazia -> ponto
                raio = tam * 0.16
                cx, cy = x0 + tam / 2, y0 + tam / 2
                self.canvas.create_oval(cx - raio, cy - raio, cx + raio, cy + raio,
                                        fill=self.COR_DICA, outline=self.COR_DICA)

        # 3) Peças
        for linha in range(8):
            for coluna in range(8):
                peca = tabuleiro.obter(linha, coluna)
                if peca is not None:
                    cx = margem + coluna * tam + tam / 2
                    cy = margem + linha * tam + tam / 2
                    self._desenhar_peca(peca, cx, cy)

        # 4) Coordenadas (a-h e 1-8) nas bordas
        for i in range(8):
            x = margem + i * tam + tam / 2
            y = margem + i * tam + tam / 2
            estilo = dict(fill=COR_TEXTO_SUAVE, font=("Helvetica", 10, "bold"))
            self.canvas.create_text(x, margem / 2, text=LETRAS_COLUNAS[i], **estilo)
            self.canvas.create_text(x, margem + 8 * tam + margem / 2,
                                    text=LETRAS_COLUNAS[i], **estilo)
            self.canvas.create_text(margem / 2, y, text=str(8 - i), **estilo)
            self.canvas.create_text(margem + 8 * tam + margem / 2, y,
                                    text=str(8 - i), **estilo)

    def _desenhar_peca(self, peca, cx, cy):
        """Desenha o glifo da peça. As brancas recebem um contorno preto
        (texto preto deslocado em 8 direções, com o branco por cima)."""
        glifo = peca.simbolo_cheio
        if peca.cor == BRANCAS:
            for d_x, d_y in ((-1.5, 0), (1.5, 0), (0, -1.5), (0, 1.5),
                             (-1.2, -1.2), (1.2, -1.2), (-1.2, 1.2), (1.2, 1.2)):
                self.canvas.create_text(cx + d_x, cy + d_y, text=glifo,
                                        font=self.fonte_pecas, fill="#000000")
            self.canvas.create_text(cx, cy, text=glifo, font=self.fonte_pecas,
                                    fill="#FFFFFF")
        else:
            self.canvas.create_text(cx, cy, text=glifo, font=self.fonte_pecas,
                                    fill="#111111")

    # ---- Atualização do painel lateral ------------------------------------------
    def atualizar_painel(self):
        jogo = self.jogo
        if jogo.em_andamento:
            if jogo.turno == BRANCAS:
                self.lbl_turno.config(text="Vez das BRANCAS", bg="#F5F5F5", fg="#111111")
            else:
                self.lbl_turno.config(text="Vez das PRETAS", bg="#111111", fg="#F5F5F5")
        else:
            self.lbl_turno.config(text="FIM DE JOGO", bg=COR_BOTAO_PERIGO, fg="#FFFFFF")
        self.var_mensagem.set(jogo.texto_status())

        def formatar(pecas):
            ordenadas = sorted(pecas, key=lambda p: -p.valor)
            return " ".join(p.simbolo for p in ordenadas) or "\u2014"

        # capturadas[cor] = peças PERDIDAS por essa cor
        self.var_cap_brancas.set(formatar(jogo.capturadas[PRETAS]))
        self.var_cap_pretas.set(formatar(jogo.capturadas[BRANCAS]))

        # Histórico em pares: "  1. e2-e4      e7-e5"
        self.lista_historico.delete(0, tk.END)
        lances = jogo.historico
        for i in range(0, len(lances), 2):
            branco = str(lances[i])
            preto = str(lances[i + 1]) if i + 1 < len(lances) else ""
            self.lista_historico.insert(tk.END, f"{i // 2 + 1:>3}. {branco:<10} {preto}")
        self.lista_historico.see(tk.END)

    # ---- Interação com o mouse -----------------------------------------------------
    def ao_clicar(self, evento):
        """Converte o clique em (linha, coluna) e trata erros com messagebox."""
        coluna = (evento.x - self.MARGEM) // self.TAMANHO_CASA
        linha = (evento.y - self.MARGEM) // self.TAMANHO_CASA
        if not dentro_do_tabuleiro(linha, coluna):
            return
        try:
            self._processar_clique(linha, coluna)
        except MovimentoInvalidoError as erro:
            messagebox.showwarning("Movimento inválido", erro.mensagem, parent=self)
        except Exception as erro:  # rede de segurança: nunca derruba o programa
            messagebox.showerror("Erro inesperado",
                                 f"Ocorreu um erro inesperado:\n{erro}", parent=self)

    def _processar_clique(self, linha, coluna):
        clicada = (linha, coluna)
        peca_clicada = self.jogo.tabuleiro.obter(linha, coluna)

        # 1) Nada selecionado: tenta selecionar a peça clicada
        if self.selecionada is None:
            self._selecionar(clicada)
            return
        # 2) Clique na própria peça selecionada: cancela a seleção
        if clicada == self.selecionada:
            self._limpar_selecao()
            self.desenhar()
            return
        # 3) Clique em outra peça do jogador da vez: troca a seleção
        if peca_clicada is not None and peca_clicada.cor == self.jogo.turno:
            self._selecionar(clicada)
            return
        # 4) Caso contrário: é uma tentativa de movimento
        self._realizar_movimento(self.selecionada, clicada)

    def _selecionar(self, posicao):
        destinos = self.jogo.movimentos_da_peca(*posicao)   # pode lançar erro
        self.selecionada = posicao
        self.destinos = destinos
        self.desenhar()

    def _limpar_selecao(self):
        self.selecionada = None
        self.destinos = []

    def _realizar_movimento(self, origem, destino):
        tabuleiro = self.jogo.tabuleiro
        peca = tabuleiro.obter(*origem)
        classe_promocao = Rainha
        # Só pergunta a promoção se o movimento for realmente legal.
        if peca is not None and tabuleiro.eh_promocao(peca, destino) \
                and destino in self.destinos:
            classe_promocao = self._perguntar_promocao(peca.cor)

        self.jogo.mover(origem, destino, classe_promocao)   # pode lançar erro

        self._limpar_selecao()
        self.desenhar()
        self.atualizar_painel()
        if not self.jogo.em_andamento:
            self.update_idletasks()
            messagebox.showinfo("Fim de jogo", self.jogo.texto_status(), parent=self)

    def _perguntar_promocao(self, cor):
        dialogo = DialogoPromocao(self, cor, self.familia_fonte)
        self.wait_window(dialogo)          # espera o jogador escolher
        return dialogo.escolha

    # ---- Botões do painel -----------------------------------------------------------
    def partida_em_curso(self):
        return len(self.jogo.historico) > 0 and self.jogo.em_andamento

    def nova_partida(self):
        if self.partida_em_curso():
            if not messagebox.askyesno(
                    "Nova partida",
                    "A partida atual será descartada.\nDeseja iniciar uma nova?",
                    parent=self):
                return
        self.jogo.reiniciar()
        self._limpar_selecao()
        self.desenhar()
        self.atualizar_painel()

    def desistir(self):
        if not self.jogo.em_andamento:
            messagebox.showinfo("Desistir", "A partida já terminou.", parent=self)
            return
        if messagebox.askyesno(
                "Desistir",
                f"As {self.jogo.turno} realmente desejam desistir da partida?",
                parent=self):
            self.jogo.desistir()
            self._limpar_selecao()
            self.desenhar()
            self.atualizar_painel()
            messagebox.showinfo("Fim de jogo", self.jogo.texto_status(), parent=self)


# =============================================================================
# APLICAÇÃO PRINCIPAL
# =============================================================================
class ChessApp(tk.Tk):
    """Janela principal: barra de menus + um contêiner que alterna entre
    a tela de menu e a tela de jogo (todas empacotadas com pack())."""

    LARGURA = 940
    ALTURA = 660

    def __init__(self):
        super().__init__()
        self.title("Xadrez \u2014 Python & Tkinter")
        self.configure(bg=COR_FUNDO)
        self.minsize(self.LARGURA, self.ALTURA)
        centralizar(self, self.LARGURA, self.ALTURA)

        self.fonte_pecas = self._escolher_fonte_pecas()
        self._criar_menu()

        # Contêiner das telas (só recebe filhos com pack)
        self.container = tk.Frame(self, bg=COR_FUNDO)
        self.container.pack(fill="both", expand=True)

        self.tela_menu = TelaMenu(self.container, ao_jogar=self.iniciar_partida,
                                  ao_sair=self.confirmar_saida,
                                  familia_fonte=self.fonte_pecas)
        self.tela_jogo = None
        self.tela_atual = None
        self.mostrar_tela(self.tela_menu)

        # Atalhos de teclado e protocolo de fechamento da janela
        self.bind("<Control-n>", lambda evento: self.iniciar_partida())
        self.bind("<Control-q>", lambda evento: self.confirmar_saida())
        self.protocol("WM_DELETE_WINDOW", self.confirmar_saida)

    # ---- Preparação -------------------------------------------------------------------
    def _escolher_fonte_pecas(self):
        """Escolhe a primeira fonte instalada que possua os símbolos de xadrez."""
        instaladas = set(tkfont.families(self))
        candidatas = ("Segoe UI Symbol", "Apple Symbols", "DejaVu Sans",
                      "Arial Unicode MS", "FreeSerif", "Symbola",
                      "Noto Sans Symbols2", "Noto Sans Symbols")
        for nome in candidatas:
            if nome in instaladas:
                return nome
        return "Arial"

    def _criar_menu(self):
        """Barra de menus: Arquivo e Ajuda."""
        barra = tk.Menu(self)

        menu_arquivo = tk.Menu(barra, tearoff=0)
        menu_arquivo.add_command(label="Nova partida", accelerator="Ctrl+N",
                                 command=self.iniciar_partida)
        menu_arquivo.add_command(label="Voltar ao menu principal",
                                 command=self.voltar_ao_menu)
        menu_arquivo.add_separator()
        menu_arquivo.add_command(label="Sair", accelerator="Ctrl+Q",
                                 command=self.confirmar_saida)
        barra.add_cascade(label="Arquivo", menu=menu_arquivo)

        menu_ajuda = tk.Menu(barra, tearoff=0)
        menu_ajuda.add_command(label="Como jogar", command=self.mostrar_como_jogar)
        menu_ajuda.add_command(label="Sobre", command=self.mostrar_sobre)
        barra.add_cascade(label="Ajuda", menu=menu_ajuda)

        self.config(menu=barra)

    # ---- Navegação entre telas ---------------------------------------------------------
    def mostrar_tela(self, tela):
        if self.tela_atual is not None and self.tela_atual is not tela:
            self.tela_atual.pack_forget()
        tela.pack(fill="both", expand=True)
        self.tela_atual = tela

    def _ajustar_tamanho(self):
        """Garante que a janela seja grande o bastante para exibir a tela atual
        por inteiro (o tamanho das fontes varia conforme o sistema operacional)."""
        self.update_idletasks()
        largura, altura = map(int, self.geometry().split("+")[0].split("x"))
        falta_l = max(0, self.container.winfo_reqwidth() - self.container.winfo_width())
        falta_a = max(0, self.container.winfo_reqheight() - self.container.winfo_height())
        if falta_l or falta_a:
            centralizar(self, largura + falta_l, altura + falta_a)

    def iniciar_partida(self):
        """Botão 'Jogar' / menu 'Nova partida'."""
        if self.tela_jogo is not None:
            self.tela_jogo.nova_partida()      # já há uma partida: reinicia (com confirmação)
            self.mostrar_tela(self.tela_jogo)
            return
        self.tela_jogo = TelaJogo(self.container, ao_voltar=self.voltar_ao_menu,
                                  familia_fonte=self.fonte_pecas)
        self.mostrar_tela(self.tela_jogo)
        self._ajustar_tamanho()

    def voltar_ao_menu(self):
        if self.tela_jogo is not None:
            if self.tela_jogo.partida_em_curso():
                if not messagebox.askyesno(
                        "Voltar ao menu",
                        "A partida atual será encerrada.\nDeseja continuar?",
                        parent=self):
                    return
            self.tela_jogo.destroy()
            self.tela_jogo = None
            self.tela_atual = None
        self.mostrar_tela(self.tela_menu)

    # ---- Diálogos ---------------------------------------------------------------------------
    def confirmar_saida(self):
        """Usada pelo botão Sair, pelo menu e pelo protocolo WM_DELETE_WINDOW."""
        if messagebox.askyesno("Sair", "Deseja realmente sair do jogo?", parent=self):
            self.destroy()

    def mostrar_sobre(self):
        JanelaSobre(self, self.fonte_pecas)

    def mostrar_como_jogar(self):
        messagebox.showinfo(
            "Como jogar",
            "1. As brancas começam. Clique numa peça sua para selecioná-la.\n"
            "2. Pontos verdes mostram onde ela pode ir; anéis verdes, capturas.\n"
            "3. Clique na casa de destino para mover.\n"
            "4. Clique de novo na peça (ou em outra sua) para trocar a seleção.\n\n"
            "Roque: mova o Rei duas casas em direção à Torre.\n"
            "En passant e promoção do peão funcionam automaticamente.\n"
            "O jogo termina em xeque-mate, empate ou desistência.",
            parent=self)


# =============================================================================
# PONTO DE ENTRADA
# =============================================================================
def main():
    app = ChessApp()
    app.mainloop()


if __name__ == "__main__":
    main()
