"""Catálogo inicial de pinturas de las tres marcas soportadas.

Los valores hexadecimales son referencias aproximadas para mostrar y comparar
colores en pantalla; no son mediciones colorimétricas oficiales. El código de
producto se conserva cuando la marca lo publica de forma estable.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import FinishType, PaintType


@dataclass(frozen=True, slots=True)
class PaintSeed:
    brand: str
    range_name: str
    name: str
    hex: str
    code: str | None = None
    paint_type: PaintType = PaintType.BASE
    finish: FinishType = FinishType.MATTE


VALLEJO_GAME_COLOR = (
    PaintSeed("Vallejo", "Game Color", "Dead White", "#F2F0E6", "72.001"),
    PaintSeed("Vallejo", "Game Color", "Wolf Grey", "#7C8083", "72.002"),
    PaintSeed("Vallejo", "Game Color", "Pale Flesh", "#E7C6A5", "72.003"),
    PaintSeed("Vallejo", "Game Color", "Elf Skin", "#D8A57A", "72.004"),
    PaintSeed("Vallejo", "Game Color", "Sun Yellow", "#F2C300", "72.006"),
    PaintSeed("Vallejo", "Game Color", "Orange Fire", "#E86A1E", "72.008"),
    PaintSeed("Vallejo", "Game Color", "Bloody Red", "#A31621", "72.010"),
    PaintSeed("Vallejo", "Game Color", "Scarlet Red", "#C1121F", "72.012"),
    PaintSeed("Vallejo", "Game Color", "Squid Pink", "#E58AA6", "72.013", PaintType.LAYER),
    PaintSeed("Vallejo", "Game Color", "Warlord Purple", "#6A2C70", "72.014"),
    PaintSeed("Vallejo", "Game Color", "Hexed Lichen", "#4B2E83", "72.015"),
    PaintSeed("Vallejo", "Game Color", "Electric Blue", "#1E6FD9", "72.017"),
    PaintSeed("Vallejo", "Game Color", "Turquoise", "#1FA9A0", "72.018"),
    PaintSeed("Vallejo", "Game Color", "Night Blue", "#1B2A4A", "72.019"),
    PaintSeed("Vallejo", "Game Color", "Imperial Blue", "#1F3A93", "72.020"),
    PaintSeed("Vallejo", "Game Color", "Ultramarine", "#1A3D8F", "72.022"),
    PaintSeed("Vallejo", "Game Color", "Livery Green", "#5FA83D", "72.023"),
    PaintSeed("Vallejo", "Game Color", "Foul Green", "#4C7A34", "72.024"),
    PaintSeed("Vallejo", "Game Color", "Goblin Green", "#3E7A3A", "72.030"),
    PaintSeed("Vallejo", "Game Color", "Dead Flesh", "#C9B79A", "72.033", PaintType.LAYER),
    PaintSeed("Vallejo", "Game Color", "Bonewhite", "#E3D5B8", "72.034", PaintType.LAYER),
    PaintSeed("Vallejo", "Game Color", "Charred Brown", "#3A2A20", "72.045"),
    PaintSeed("Vallejo", "Game Color", "Ghost Grey", "#B8BCC0", "72.046", PaintType.LAYER),
    PaintSeed("Vallejo", "Game Color", "Black", "#111111", "72.051"),
    PaintSeed(
        "Vallejo", "Game Color", "Silver", "#C0C0C0", "72.052", PaintType.METALLIC, FinishType.SATIN
    ),
    PaintSeed(
        "Vallejo",
        "Game Color",
        "Gunmetal",
        "#5A5E62",
        "72.054",
        PaintType.METALLIC,
        FinishType.SATIN,
    ),
    PaintSeed(
        "Vallejo",
        "Game Color",
        "Polished Gold",
        "#D4AF37",
        "72.055",
        PaintType.METALLIC,
        FinishType.GLOSS,
    ),
    PaintSeed(
        "Vallejo",
        "Game Color",
        "Bright Bronze",
        "#B08D57",
        "72.057",
        PaintType.METALLIC,
        FinishType.SATIN,
    ),
    PaintSeed("Vallejo", "Game Color", "Desert Yellow", "#C2A15A", "72.063"),
    PaintSeed("Vallejo", "Game Color", "Tan", "#D2B48C", "72.066"),
)

VALLEJO_MODEL_COLOR = (
    PaintSeed("Vallejo", "Model Color", "White", "#F4F4F0", "70.951"),
    PaintSeed("Vallejo", "Model Color", "Black", "#101010", "70.950"),
    PaintSeed("Vallejo", "Model Color", "Flat Red", "#B01E28", "70.957"),
    PaintSeed("Vallejo", "Model Color", "Vermilion", "#D63A1F", "70.909"),
    PaintSeed("Vallejo", "Model Color", "Burnt Umber", "#5A3A24", "70.941"),
    PaintSeed("Vallejo", "Model Color", "English Uniform", "#6E5A3A", "70.921"),
    PaintSeed("Vallejo", "Model Color", "Russian Uniform", "#6B6F3E", "70.924"),
    PaintSeed("Vallejo", "Model Color", "German Fieldgrey", "#5C6652", "70.830"),
    PaintSeed("Vallejo", "Model Color", "US Olive Drab", "#5E5F3A", "70.887"),
    PaintSeed("Vallejo", "Model Color", "Ivory", "#E9DFC3", "70.918", PaintType.LAYER),
    PaintSeed("Vallejo", "Model Color", "Flat Flesh", "#D8A77C", "70.955"),
    PaintSeed("Vallejo", "Model Color", "Sunny Skin Tone", "#E0A878", "70.845", PaintType.LAYER),
    PaintSeed("Vallejo", "Model Color", "Dark Flesh", "#9A6A4A", "70.927"),
    PaintSeed("Vallejo", "Model Color", "Neutral Grey", "#8A8D8F", "70.992", PaintType.LAYER),
    PaintSeed("Vallejo", "Model Color", "German Grey", "#4A4E50", "70.995"),
    PaintSeed("Vallejo", "Model Color", "Dark Prussian Blue", "#1F3A5A", "70.899"),
    PaintSeed("Vallejo", "Model Color", "Sky Blue", "#6FA8C9", "70.961", PaintType.LAYER),
    PaintSeed("Vallejo", "Model Color", "Purple", "#5A2A5A", "70.959"),
    PaintSeed("Vallejo", "Model Color", "Magenta", "#A03A7A", "70.945", PaintType.LAYER),
    PaintSeed("Vallejo", "Model Color", "Intermediate Green", "#4A7A3A", "70.891"),
    PaintSeed("Vallejo", "Model Color", "Olive Grey", "#6A6A4A", "70.888"),
    PaintSeed("Vallejo", "Model Color", "Chocolate Brown", "#4A3020", "70.872"),
    PaintSeed("Vallejo", "Model Color", "Pale Sand", "#D8C8A8", "70.837", PaintType.LAYER),
    PaintSeed("Vallejo", "Model Color", "Green Grey", "#5A6A5A", "70.969", PaintType.LAYER),
)

VALLEJO_XPRESS_COLOR = (
    PaintSeed(
        "Vallejo",
        "Xpress Color",
        "Plague Green",
        "#4C6B3C",
        "72.401",
        PaintType.CONTRAST,
        FinishType.SATIN,
    ),
    PaintSeed(
        "Vallejo",
        "Xpress Color",
        "Orc Skin",
        "#5E7A4A",
        "72.402",
        PaintType.CONTRAST,
        FinishType.SATIN,
    ),
    PaintSeed(
        "Vallejo",
        "Xpress Color",
        "Blood Red",
        "#7A1F24",
        "72.403",
        PaintType.CONTRAST,
        FinishType.SATIN,
    ),
    PaintSeed(
        "Vallejo",
        "Xpress Color",
        "Ultramarine",
        "#244A8F",
        "72.404",
        PaintType.CONTRAST,
        FinishType.SATIN,
    ),
    PaintSeed(
        "Vallejo",
        "Xpress Color",
        "Desert Yellow",
        "#B99A5E",
        "72.405",
        PaintType.CONTRAST,
        FinishType.SATIN,
    ),
    PaintSeed(
        "Vallejo",
        "Xpress Color",
        "Black",
        "#1A1A1A",
        "72.406",
        PaintType.CONTRAST,
        FinishType.SATIN,
    ),
)

GSW_ACRYLIC_COLOR = (
    PaintSeed("Green Stuff World", "Acrylic Color", "Pure White", "#F5F5F0"),
    PaintSeed("Green Stuff World", "Acrylic Color", "Black", "#141414"),
    PaintSeed("Green Stuff World", "Acrylic Color", "Blood Red", "#A51C24"),
    PaintSeed("Green Stuff World", "Acrylic Color", "Ultramarine Blue", "#244A8F"),
    PaintSeed("Green Stuff World", "Acrylic Color", "Sky Blue", "#6FA8C9"),
    PaintSeed("Green Stuff World", "Acrylic Color", "Turquoise", "#1FA9A0"),
    PaintSeed("Green Stuff World", "Acrylic Color", "Goblin Green", "#3E7A3A"),
    PaintSeed("Green Stuff World", "Acrylic Color", "Yellow", "#F2C300"),
    PaintSeed("Green Stuff World", "Acrylic Color", "Orange", "#E86A1E"),
    PaintSeed("Green Stuff World", "Acrylic Color", "Purple", "#6A2C70"),
    PaintSeed("Green Stuff World", "Acrylic Color", "Flesh", "#D8A57A"),
    PaintSeed("Green Stuff World", "Acrylic Color", "Bone", "#E3D5B8", paint_type=PaintType.LAYER),
    PaintSeed("Green Stuff World", "Acrylic Color", "Leather Brown", "#6A4A2E"),
    PaintSeed("Green Stuff World", "Acrylic Color", "Grey", "#8A8D8F"),
)

GSW_INTENSITY_INK = (
    PaintSeed(
        "Green Stuff World",
        "Intensity Ink",
        "Troll Green",
        "#3E6B3A",
        paint_type=PaintType.INK,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Green Stuff World",
        "Intensity Ink",
        "Orc Green",
        "#4C7A34",
        paint_type=PaintType.INK,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Green Stuff World",
        "Intensity Ink",
        "Blood Red",
        "#7A1F24",
        paint_type=PaintType.INK,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Green Stuff World",
        "Intensity Ink",
        "Blue",
        "#1F3A6A",
        paint_type=PaintType.INK,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Green Stuff World",
        "Intensity Ink",
        "Purple",
        "#4B2E83",
        paint_type=PaintType.INK,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Green Stuff World",
        "Intensity Ink",
        "Sepia",
        "#6A4A2E",
        paint_type=PaintType.INK,
        finish=FinishType.GLOSS,
    ),
)

GSW_METALLIC_COLOR = (
    PaintSeed(
        "Green Stuff World",
        "Metallic Color",
        "Shining Silver",
        "#C8C8C8",
        paint_type=PaintType.METALLIC,
        finish=FinishType.SATIN,
    ),
    PaintSeed(
        "Green Stuff World",
        "Metallic Color",
        "Glorious Gold",
        "#D4AF37",
        paint_type=PaintType.METALLIC,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Green Stuff World",
        "Metallic Color",
        "Bright Bronze",
        "#B08D57",
        paint_type=PaintType.METALLIC,
        finish=FinishType.SATIN,
    ),
    PaintSeed(
        "Green Stuff World",
        "Metallic Color",
        "Hammered Copper",
        "#B87333",
        paint_type=PaintType.METALLIC,
        finish=FinishType.SATIN,
    ),
)

GSW_FLUOR_COLOR = (
    PaintSeed(
        "Green Stuff World",
        "Fluor Color",
        "Fluorescent Green",
        "#7CFF3A",
        paint_type=PaintType.TECHNICAL,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Green Stuff World",
        "Fluor Color",
        "Fluorescent Yellow",
        "#F2FF3A",
        paint_type=PaintType.TECHNICAL,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Green Stuff World",
        "Fluor Color",
        "Fluorescent Orange",
        "#FF7A1F",
        paint_type=PaintType.TECHNICAL,
        finish=FinishType.GLOSS,
    ),
)

CITADEL_BASE = (
    PaintSeed("Citadel", "Base", "Abaddon Black", "#111111"),
    PaintSeed("Citadel", "Base", "Corax White", "#F2F2F0"),
    PaintSeed("Citadel", "Base", "Macragge Blue", "#1F3A8F"),
    PaintSeed("Citadel", "Base", "Mephiston Red", "#A51C24"),
    PaintSeed("Citadel", "Base", "Khorne Red", "#7A1418"),
    PaintSeed("Citadel", "Base", "Waaagh! Flesh", "#3E6B3A"),
    PaintSeed("Citadel", "Base", "Castellan Green", "#3A5A34"),
    PaintSeed("Citadel", "Base", "Zandri Dust", "#B8A882"),
    PaintSeed("Citadel", "Base", "Steel Legion Drab", "#7A6A4A"),
    PaintSeed("Citadel", "Base", "Rhinox Hide", "#4A3020"),
    PaintSeed("Citadel", "Base", "Mournfang Brown", "#6A4A2E"),
    PaintSeed("Citadel", "Base", "Cadian Fleshtone", "#D8A57A"),
    PaintSeed(
        "Citadel",
        "Base",
        "Retributor Armour",
        "#D4AF37",
        paint_type=PaintType.METALLIC,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Citadel",
        "Base",
        "Leadbelcher",
        "#5A5E62",
        paint_type=PaintType.METALLIC,
        finish=FinishType.SATIN,
    ),
)

CITADEL_LAYER = (
    PaintSeed("Citadel", "Layer", "Evil Sunz Scarlet", "#C1121F", paint_type=PaintType.LAYER),
    PaintSeed("Citadel", "Layer", "Wild Rider Red", "#D63A1F", paint_type=PaintType.LAYER),
    PaintSeed("Citadel", "Layer", "Fire Dragon Bright", "#E86A1E", paint_type=PaintType.LAYER),
    PaintSeed("Citadel", "Layer", "Yriel Yellow", "#F2C300", paint_type=PaintType.LAYER),
    PaintSeed("Citadel", "Layer", "Flash Gitz Yellow", "#F2E03A", paint_type=PaintType.LAYER),
    PaintSeed("Citadel", "Layer", "Calgar Blue", "#2E5A8A", paint_type=PaintType.LAYER),
    PaintSeed("Citadel", "Layer", "Hoeth Blue", "#4A7AB8", paint_type=PaintType.LAYER),
    PaintSeed("Citadel", "Layer", "Lothern Blue", "#2A9AC9", paint_type=PaintType.LAYER),
    PaintSeed("Citadel", "Layer", "Warboss Green", "#4A7A3A", paint_type=PaintType.LAYER),
    PaintSeed("Citadel", "Layer", "Skarsnik Green", "#6A9A5A", paint_type=PaintType.LAYER),
    PaintSeed("Citadel", "Layer", "Moot Green", "#7AA83A", paint_type=PaintType.LAYER),
    PaintSeed("Citadel", "Layer", "Ushabti Bone", "#E3D5B8", paint_type=PaintType.LAYER),
    PaintSeed("Citadel", "Layer", "Screaming Skull", "#F2EAD8", paint_type=PaintType.LAYER),
    PaintSeed("Citadel", "Layer", "Administratum Grey", "#A8ACAE", paint_type=PaintType.LAYER),
    PaintSeed("Citadel", "Layer", "Dawnstone", "#8A8D8F", paint_type=PaintType.LAYER),
    PaintSeed("Citadel", "Layer", "Eshin Grey", "#5A5E61", paint_type=PaintType.LAYER),
    PaintSeed(
        "Citadel",
        "Layer",
        "Ironbreaker",
        "#8A8D8F",
        paint_type=PaintType.METALLIC,
        finish=FinishType.SATIN,
    ),
    PaintSeed(
        "Citadel",
        "Layer",
        "Stormhost Silver",
        "#C8C8C8",
        paint_type=PaintType.METALLIC,
        finish=FinishType.SATIN,
    ),
)

CITADEL_SHADE = (
    PaintSeed(
        "Citadel",
        "Shade",
        "Nuln Oil",
        "#1A1A1A",
        paint_type=PaintType.WASH,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Citadel",
        "Shade",
        "Agrax Earthshade",
        "#4A3A2A",
        paint_type=PaintType.WASH,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Citadel",
        "Shade",
        "Reikland Fleshshade",
        "#8A5A3A",
        paint_type=PaintType.WASH,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Citadel",
        "Shade",
        "Seraphim Sepia",
        "#8A6A3A",
        paint_type=PaintType.WASH,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Citadel",
        "Shade",
        "Biel-Tan Green",
        "#2E5A3A",
        paint_type=PaintType.WASH,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Citadel",
        "Shade",
        "Drakenhof Nightshade",
        "#1F3A5A",
        paint_type=PaintType.WASH,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Citadel",
        "Shade",
        "Druchii Violet",
        "#4B2E6A",
        paint_type=PaintType.WASH,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Citadel",
        "Shade",
        "Carroburg Crimson",
        "#7A2A3A",
        paint_type=PaintType.WASH,
        finish=FinishType.GLOSS,
    ),
)

CITADEL_CONTRAST = (
    PaintSeed(
        "Citadel",
        "Contrast",
        "Black Templar",
        "#1A1A1A",
        paint_type=PaintType.CONTRAST,
        finish=FinishType.SATIN,
    ),
    PaintSeed(
        "Citadel",
        "Contrast",
        "Apothecary White",
        "#D8D8D0",
        paint_type=PaintType.CONTRAST,
        finish=FinishType.SATIN,
    ),
    PaintSeed(
        "Citadel",
        "Contrast",
        "Blood Angels Red",
        "#A51C24",
        paint_type=PaintType.CONTRAST,
        finish=FinishType.SATIN,
    ),
    PaintSeed(
        "Citadel",
        "Contrast",
        "Ultramarines Blue",
        "#1F3A8F",
        paint_type=PaintType.CONTRAST,
        finish=FinishType.SATIN,
    ),
    PaintSeed(
        "Citadel",
        "Contrast",
        "Dark Angels Green",
        "#1F4D2E",
        paint_type=PaintType.CONTRAST,
        finish=FinishType.SATIN,
    ),
    PaintSeed(
        "Citadel",
        "Contrast",
        "Skeleton Horde",
        "#C2B08A",
        paint_type=PaintType.CONTRAST,
        finish=FinishType.SATIN,
    ),
    PaintSeed(
        "Citadel",
        "Contrast",
        "Snakebite Leather",
        "#8A5A2A",
        paint_type=PaintType.CONTRAST,
        finish=FinishType.SATIN,
    ),
    PaintSeed(
        "Citadel",
        "Contrast",
        "Magos Purple",
        "#5A2A6A",
        paint_type=PaintType.CONTRAST,
        finish=FinishType.SATIN,
    ),
)

CITADEL_TECHNICAL = (
    PaintSeed(
        "Citadel",
        "Technical",
        "Blood for the Blood God",
        "#7A1418",
        paint_type=PaintType.TECHNICAL,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Citadel",
        "Technical",
        "Nurgle's Rot",
        "#7A9A3A",
        paint_type=PaintType.TECHNICAL,
        finish=FinishType.GLOSS,
    ),
    PaintSeed(
        "Citadel",
        "Technical",
        "Typhus Corrosion",
        "#4A4A3A",
        paint_type=PaintType.TECHNICAL,
        finish=FinishType.MATTE,
    ),
    PaintSeed(
        "Citadel",
        "Technical",
        "Ryza Rust",
        "#C26A2A",
        paint_type=PaintType.TECHNICAL,
        finish=FinishType.MATTE,
    ),
)

CITADEL_DRY = (
    PaintSeed(
        "Citadel", "Dry", "Terminatus Stone", "#B8A882", paint_type=PaintType.LAYER
    ),
    PaintSeed(
        "Citadel",
        "Dry",
        "Necron Compound",
        "#A8ACAE",
        paint_type=PaintType.LAYER,
        finish=FinishType.SATIN,
    ),
    PaintSeed(
        "Citadel",
        "Dry",
        "Golden Griffon",
        "#C2A25A",
        paint_type=PaintType.LAYER,
        finish=FinishType.SATIN,
    ),
)

CATALOG: tuple[PaintSeed, ...] = (
    VALLEJO_GAME_COLOR
    + VALLEJO_MODEL_COLOR
    + VALLEJO_XPRESS_COLOR
    + GSW_ACRYLIC_COLOR
    + GSW_INTENSITY_INK
    + GSW_METALLIC_COLOR
    + GSW_FLUOR_COLOR
    + CITADEL_BASE
    + CITADEL_LAYER
    + CITADEL_SHADE
    + CITADEL_CONTRAST
    + CITADEL_TECHNICAL
    + CITADEL_DRY
)

BRANDS: tuple[str, ...] = ("Vallejo", "Green Stuff World", "Citadel")
