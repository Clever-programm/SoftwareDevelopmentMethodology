"""Минимальная библиотека для рисования диаграмм на matplotlib.

Координаты задаются в миллиметрах итогового рисунка, поэтому размер шрифта
на диаграмме совпадает с размером в отчёте при вставке рисунка в натуральную ширину.
"""
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyBboxPatch, Polygon, Rectangle

plt.rcParams["font.family"] = "Arial"
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "img")
MM = 1 / 25.4


class Canvas:
    def __init__(self, w, h, fs=8, y0=0):
        self.w, self.h, self.fs = w, h, fs
        self.fig = plt.figure(figsize=(w * MM, h * MM), dpi=300)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, w)
        self.ax.set_ylim(y0, y0 + h)
        self.ax.axis("off")
        self.renderer = self.fig.canvas.get_renderer()
        self.shapes = {}

    # ------------------------------------------------------------ текст
    def text(self, x, y, s, fs=None, ha="center", va="center", z=5, **kw):
        return self.ax.text(x, y, s, fontsize=fs or self.fs, ha=ha, va=va, zorder=z,
                            linespacing=1.15, **kw)

    def measure(self, t):
        bb = t.get_window_extent(self.renderer)
        inv = self.ax.transData.inverted()
        (x0, y0), (x1, y1) = inv.transform([(bb.x0, bb.y0), (bb.x1, bb.y1)])
        return x1 - x0, y1 - y0

    def underline(self, t, dashed=False):
        tw, th = self.measure(t)
        x, y = t.get_position()
        yy = y - th / 2 - 0.35
        self.ax.plot([x - tw / 2, x + tw / 2], [yy, yy], color="k", lw=0.6, zorder=6,
                     ls=(0, (2, 1.2)) if dashed else "-")

    # ------------------------------------------------------------ фигуры ER (нотация Чена)
    def entity(self, name, x, y, label=None, weak=False, fs=None, minw=0):
        t = self.text(x, y, label or name, fs=fs or self.fs + 1, weight="bold")
        tw, th = self.measure(t)
        w, h = max(tw + 6, minw), th + 4.5
        self.ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc="white", ec="k", lw=1.1, zorder=3))
        if weak:
            self.ax.add_patch(Rectangle((x - w / 2 + 0.9, y - h / 2 + 0.9), w - 1.8, h - 1.8,
                                        fill=False, ec="k", lw=0.8, zorder=3))
        self.shapes[name] = ("rect", x, y, w / 2, h / 2)
        return name

    def rel(self, name, x, y, label=None, ident=False, fs=None):
        t = self.text(x, y, label or name, fs=fs or self.fs, style="italic")
        tw, th = self.measure(t)
        a, b = tw / 2 / 0.62 + 1.2, th / 2 / 0.38 + 0.8
        pts = [(x - a, y), (x, y + b), (x + a, y), (x, y - b)]
        self.ax.add_patch(Polygon(pts, closed=True, fc="white", ec="k", lw=1.0, zorder=3))
        if ident:
            k = 0.82
            self.ax.add_patch(Polygon([(x - a * k, y), (x, y + b * k), (x + a * k, y), (x, y - b * k)],
                                      closed=True, fill=False, ec="k", lw=0.7, zorder=3))
        self.shapes[name] = ("diamond", x, y, a, b)
        return name

    def attr(self, owner, label, dx, dy, key=False, partial=False, derived=False, multi=False, fs=None):
        ox, oy = self.shapes[owner][1], self.shapes[owner][2]
        x, y = ox + dx, oy + dy
        t = self.text(x, y, label, fs=fs or self.fs - 0.5)
        tw, th = self.measure(t)
        w, h = tw + 5.0, th + 3.2
        ls = (0, (3, 1.5)) if derived else "-"
        self.ax.add_patch(Ellipse((x, y), w, h, fc="white", ec="k", lw=0.7, ls=ls, zorder=3))
        if multi:
            self.ax.add_patch(Ellipse((x, y), w - 1.6, h - 1.4, fill=False, ec="k", lw=0.6, zorder=3))
        if key or partial:
            self.underline(t, dashed=partial)
        self.ax.plot([ox, x], [oy, y], color="k", lw=0.6, zorder=1)

    def border_point(self, name, tx, ty):
        """Точка выхода отрезка (центр фигуры -> (tx, ty)) за её границу."""
        kind, x, y, a, b = self.shapes[name]
        dx, dy = tx - x, ty - y
        if kind == "rect":
            k = min(a / abs(dx) if dx else 1e9, b / abs(dy) if dy else 1e9)
        else:
            k = 1 / (abs(dx) / a + abs(dy) / b)
        return x + dx * k, y + dy * k

    def link(self, ent, rel, card=None, offset=(0, 0), role=None, card_side=1):
        """Линия «сущность – связь» с подписью кардинальности у сущности.

        offset смещает точку крепления к сущности (для рекурсивных связей),
        card_side задаёт сторону линии, с которой ставятся подписи.
        """
        e, r = self.shapes[ent], self.shapes[rel]
        ex, ey = e[1] + offset[0], e[2] + offset[1]
        rx, ry = r[1], r[2]
        self.ax.plot([ex, rx], [ey, ry], color="k", lw=0.9, zorder=1)
        L = math.hypot(rx - ex, ry - ey)
        ux, uy = (rx - ex) / L, (ry - ey) / L
        px, py = -uy * card_side, ux * card_side
        if card:
            if offset == (0, 0):
                bx, by = self.border_point(ent, rx, ry)
            else:
                _, x, y, a, b = e
                k = min(a / abs(ux) if ux else 1e9, b / abs(uy) if uy else 1e9)
                bx, by = x + ux * k + offset[0], y + uy * k + offset[1]
            d = 2.4 if offset == (0, 0) else 2.6
            self.text(bx + ux * 2.6 + px * d, by + uy * 2.6 + py * d, card,
                      fs=self.fs, weight="bold")
        if role:
            mx, my = rx - ux * L * 0.42, ry - uy * L * 0.42
            ha = "left" if px > 0.5 else "right" if px < -0.5 else "center"
            self.text(mx + px * 1.5, my + py * 2.4, role, fs=self.fs - 1.5, style="italic", ha=ha)

    # ------------------------------------------------------------ общие блоки
    def box(self, x, y, w, h, label, fs=None, rounded=False, lw=1.0, fc="white", weight="normal", ls="-", z=3):
        if rounded:
            p = FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=2.5",
                               fc=fc, ec="k", lw=lw, zorder=z, ls=ls)
        else:
            p = Rectangle((x - w / 2, y - h / 2), w, h, fc=fc, ec="k", lw=lw, zorder=z, ls=ls)
        self.ax.add_patch(p)
        if label:
            self.text(x, y, label, fs=fs, weight=weight)

    def diamond(self, x, y, a, b, label, fs=None):
        self.ax.add_patch(Polygon([(x - a, y), (x, y + b), (x + a, y), (x, y - b)], closed=True,
                                  fc="white", ec="k", lw=1.0, zorder=3))
        self.text(x, y, label, fs=fs)

    def arrow(self, pts, lw=0.9, ls="-", head=True, color="k", z=2):
        xs, ys = zip(*pts)
        self.ax.plot(xs, ys, color=color, lw=lw, ls=ls, zorder=z, solid_joinstyle="miter")
        if head:
            self.ax.annotate("", xy=pts[-1], xytext=pts[-2], zorder=z,
                             arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, ls="-",
                                             mutation_scale=8, shrinkA=0, shrinkB=0))

    # ------------------------------------------------------------ семантическая сеть
    def node(self, name, x, y, label=None, fs=None, fc="white", bold=False):
        t = self.text(x, y, label or name, fs=fs or self.fs, weight="bold" if bold else "normal")
        tw, th = self.measure(t)
        w, h = tw + 5, th + 3.6
        self.ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                         boxstyle="round,pad=0,rounding_size=1.8",
                                         fc=fc, ec="k", lw=0.9, zorder=3))
        self.shapes[name] = ("rect", x, y, w / 2, h / 2)

    def edge(self, a, b, label=None, ls="-", lw=0.8, lpos=0.5, loff=(0, 0), fs=None, both=False):
        (_, ax_, ay, *_), (_, bx, by, *_) = self.shapes[a], self.shapes[b]
        p0 = self.border_point(a, bx, by)
        p1 = self.border_point(b, ax_, ay)
        style = "<|-|>" if both else "-|>"
        self.ax.annotate("", xy=p1, xytext=p0, zorder=2,
                         arrowprops=dict(arrowstyle=style, color="k", lw=lw, ls=ls,
                                         mutation_scale=7, shrinkA=0, shrinkB=0))
        if label:
            mx = p0[0] + (p1[0] - p0[0]) * lpos + loff[0]
            my = p0[1] + (p1[1] - p0[1]) * lpos + loff[1]
            self.text(mx, my, label, fs=fs or self.fs - 1, style="italic",
                      bbox=dict(fc="white", ec="none", pad=0.4), z=4)

    def save(self, name):
        os.makedirs(OUT_DIR, exist_ok=True)
        self.fig.savefig(os.path.join(OUT_DIR, name), dpi=300)
        plt.close(self.fig)
