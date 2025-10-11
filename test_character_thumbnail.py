#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def create_test_thumbnail_with_character():
    """サムネイルにキャラクター画像を合成するテスト"""

    # 設定
    thumbnail_width = 1280
    thumbnail_height = 720
    bg_color = "#193d5a"

    # キャラクター画像パス (ユーザーがアップロードした画像を使用)
    character_image_path = Path("assets/春日部つむぎ立ち絵_公式_v2.0/春日部つむぎ立ち絵_公式_v2.0.png")

    # 出力パス
    output_path = Path("output/test_character_thumbnail.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. ベースサムネイル作成
    thumbnail = Image.new("RGB", (thumbnail_width, thumbnail_height), color=bg_color)
    draw = ImageDraw.Draw(thumbnail)

    # アクセントバーを追加
    accent_color = "#EF476F"
    draw.rectangle([(0, 0), (12, thumbnail_height)], fill=accent_color)

    # タイトルテキストを追加
    title_text = "金融ニュース速報"
    try:
        font = ImageFont.truetype("/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf", 96)
        subtitle_font = ImageFont.truetype("/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf", 56)
    except:
        font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()

    draw.text((100, 80), title_text, font=font, fill="#FFFFFF")
    draw.text((100, 200), "最新の経済トレンドを解説", font=subtitle_font, fill="#FFD166")

    # 2. キャラクター画像を読み込んで合成
    if character_image_path.exists():
        character = Image.open(character_image_path).convert("RGBA")

        # キャラクターサイズ調整（サムネイル高さの80%に設定）
        target_height = int(thumbnail_height * 0.85)
        aspect_ratio = character.width / character.height
        target_width = int(target_height * aspect_ratio)

        character_resized = character.resize(
            (target_width, target_height),
            Image.Resampling.LANCZOS
        )

        # 配置位置を計算（右下に配置）
        char_x = thumbnail_width - target_width - 20
        char_y = thumbnail_height - target_height

        # RGBAモードに変換して合成
        thumbnail_rgba = thumbnail.convert("RGBA")

        # アルファチャンネルを使って透過部分を保持しながら合成
        thumbnail_rgba.paste(character_resized, (char_x, char_y), character_resized)

        # RGB に戻す
        thumbnail = thumbnail_rgba.convert("RGB")

        print(f"✓ キャラクター画像を合成しました")
        print(f"  - 元サイズ: {character.size}")
        print(f"  - リサイズ後: {character_resized.size}")
        print(f"  - 配置位置: ({char_x}, {char_y})")
    else:
        print(f"⚠ キャラクター画像が見つかりません: {character_image_path}")

    # 3. ロゴアイコンを追加（既存の機能）
    icon_path = Path("assets/icon2510youtuber-mini.png")
    if icon_path.exists():
        icon = Image.open(icon_path).convert("RGBA")
        icon_size = 100
        icon = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)

        icon_x = thumbnail_width - icon_size - 40
        icon_y = thumbnail_height - icon_size - 40

        thumbnail_rgba = thumbnail.convert("RGBA")
        thumbnail_rgba.paste(icon, (icon_x, icon_y), icon)
        thumbnail = thumbnail_rgba.convert("RGB")

        print(f"✓ ロゴアイコンを追加しました")

    # 4. 保存
    thumbnail.save(output_path, format="PNG", quality=95)
    print(f"\n✓ サムネイルを保存しました: {output_path}")
    print(f"  サイズ: {thumbnail.size}")

    return output_path


if __name__ == "__main__":
    result = create_test_thumbnail_with_character()
    print(f"\n完成したサムネイルを確認してください:")
    print(f"  {result.absolute()}")
