"""Image -> structured visual attributes -> text embeddings.

OpenAI has no image-embedding endpoint, so an image's "embedding" is the embedding of a
fixed-schema description written by a vision model. Two texts are embedded per image:
  style_text  - palette, materials, textures, era, mood, aesthetic. No shape or part details,
                so that chairs don't match chairs regardless of style. Used for visual fit.
  search_text - what the item is plus its style, used for retrieval
Catalog products are captioned as the single product for sale (category hint given);
board pins are captioned for the overall style of the scene, since on a mood board the
whole image is the inspiration. Captions are cached by file hash + mode.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from visioncart import config
from visioncart.llm import LLMClient, file_sha


CAPTION_VERSION = "v2"  # bump when the prompt or schema changes; invalidates cached captions
STYLE_TEXT_VERSION = "s2"  # bump when style_text() changes; forces board re-sync


class ImageAttributes(BaseModel):
    item_description: str = Field(description="What the main product is, in 5-12 words.")
    palette: list[str] = Field(description="3-6 dominant colours of the product itself, named precisely "
                                           "(e.g. 'oxblood', 'sage', 'burnt sienna'), never just 'neutral'.")
    materials: list[str] = Field(description="Specific materials (e.g. 'boucle', 'burl walnut', 'raw terracotta').")
    textures: list[str] = Field(description="Surface qualities (e.g. 'crackle glaze', 'nubby', 'high-gloss').")
    signature_details: list[str] = Field(description="3-6 concrete design details that set this product apart: "
                                                     "motifs, patterns, trims, hardware, finishes, construction.")
    silhouette: str = Field(description="Shape / cut / form in a short phrase.")
    era_influences: list[str] = Field(description="Specific design eras or movements it draws on.")
    mood: list[str] = Field(description="3-5 specific adjectives for the feeling it gives.")
    aesthetic_tags: list[str] = Field(description="The most specific aesthetic names this would be filed under.")
    water_resistant: bool = Field(description="True only if clearly built for wet weather.")
    warmth: Literal["light", "medium", "warm"]
    style_summary: str = Field(description="One sentence on what makes this product's style distinctive. "
                                           "Do not say what the object is.")


CAPTION_SYSTEM = (
    "You describe product images for a visual style-matching system that must tell closely related "
    "aesthetics apart. Describe ONLY the main product being sold; ignore the background, room, "
    "props, other furniture, and any model wearing it. Be concrete and visual. Prefer precise, "
    "distinguishing vocabulary over generic words such as 'modern', 'minimal', 'elegant', "
    "'stylish', 'contemporary', 'neutral' or 'classic' unless nothing more specific applies."
)
CAPTION_PROMPT = "Describe the main product's visual attributes."

SCENE_SYSTEM = (
    "You describe inspiration pins from a user's mood board for a visual style-matching system that "
    "must tell closely related aesthetics apart. Capture the overall aesthetic of the WHOLE image "
    "(room, outfit or object): its palette, materials, textures, motifs, era and mood. Do not focus "
    "on a single object. Prefer precise, distinguishing vocabulary over generic words such as "
    "'modern', 'minimal', 'elegant', 'stylish', 'contemporary', 'neutral' or 'classic'."
)
SCENE_PROMPT = "Describe this pin's overall visual style. item_description: summarise what the scene shows."


def style_text(a: ImageAttributes) -> str:
    return "; ".join([
        "palette: " + ", ".join(a.palette),
        "materials: " + ", ".join(a.materials),
        "textures: " + ", ".join(a.textures),
        "era: " + ", ".join(a.era_influences),
        "mood: " + ", ".join(a.mood),
        "aesthetic: " + ", ".join(a.aesthetic_tags),
        a.style_summary,
    ])


def search_text(name: str, category: str, a: ImageAttributes) -> str:
    return f"{name}. {category}. {a.item_description}. {style_text(a)}"


def style_terms(a: ImageAttributes) -> list[str]:
    """Lower-cased style vocabulary for an item; the unit that feedback learns over."""
    terms = a.palette + a.materials + a.textures + a.signature_details + a.mood + a.aesthetic_tags + a.era_influences
    return sorted({t.strip().lower() for t in terms if t.strip()})


async def caption_image(llm: LLMClient, path: str | Path, product_hint: str | None = None,
                        cache_dir: Path = config.CACHE_DIR / "captions" / CAPTION_VERSION) -> ImageAttributes:
    """With `product_hint` (a catalog category, never a style), describe only that product so
    lifestyle photos don't get the room described. Without it, the image is a board pin and is
    described for the style of the whole scene."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    if product_hint:
        suffix = f"-{hashlib.sha1(product_hint.encode()).hexdigest()[:8]}"
        system = CAPTION_SYSTEM
        prompt = (f"{CAPTION_PROMPT} The product for sale is a {product_hint}. If the photo shows a room "
                  f"or outfit, describe only the {product_hint}.")
    else:
        suffix, system, prompt = "-scene", SCENE_SYSTEM, SCENE_PROMPT
    cached = cache_dir / f"{file_sha(path)}{suffix}.json"
    if cached.exists():
        return ImageAttributes.model_validate(json.loads(cached.read_text()))
    attrs = await llm.parse(ImageAttributes, system, prompt, images=[path])
    cached.write_text(attrs.model_dump_json())
    return attrs
