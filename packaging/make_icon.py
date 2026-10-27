"""Генерирует исходную иконку приложения (1024x1024 PNG) без внешних ассетов.

    python packaging/make_icon.py            # -> packaging/icon.png
    npx @tauri-apps/cli@2 icon packaging/icon.png   # -> tauri/src-tauri/icons/*

Иконка используется установщиком Inno Setup (packaging/cutline.iss) и Tauri.
"""

import os

from PIL import Image, ImageDraw

SIZE = 1024
BG_TOP = (30, 34, 46)
BG_BOTTOM = (18, 20, 28)
ACCENT = (86, 156, 214)


def _background() -> Image.Image:
    """Вертикальный градиент + скруглённые углы."""
    gradient = Image.new('RGB', (1, SIZE))
    for y in range(SIZE):
        t = y / (SIZE - 1)
        gradient.putpixel((0, y), tuple(
            round(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3)
        ))
    image = gradient.resize((SIZE, SIZE))

    mask = Image.new('L', (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=180, fill=255)
    rounded = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    rounded.paste(image, (0, 0), mask)
    return rounded


def _wave(draw: ImageDraw.ImageDraw):
    """Символ «звуковая волна» вместо буквы: читается на любом размере."""
    bars = [(0.30, 0.34), (0.42, 0.52), (0.54, 0.72), (0.66, 0.44)]
    width = 52
    for x_ratio, height_ratio in bars:
        x = SIZE * x_ratio
        half = SIZE * height_ratio / 2
        draw.rounded_rectangle(
            [x - width / 2, SIZE / 2 - half, x + width / 2, SIZE / 2 + half],
            radius=width / 2,
            fill=ACCENT,
        )
    # Точка справа: «остаток» записи после удаления тишины
    draw.ellipse([SIZE * 0.76, SIZE * 0.46, SIZE * 0.76 + 56, SIZE * 0.46 + 56], fill=ACCENT)


def main():
    image = _background()
    _wave(ImageDraw.Draw(image))
    output = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.png')
    image.save(output)
    # .ico нужен установщику Inno Setup и Tauri (если icon.ico ещё не сгенерирован)
    image.save(os.path.join(os.path.dirname(output), 'icon.ico'),
               sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f'Готово: {output} + icon.ico')


if __name__ == '__main__':
    main()
