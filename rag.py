"""Tek notluk RAG: parçala, ChromaDB'ye yaz, Ollama ile cevapla."""

from pathlib import Path

import chromadb
import httpx

OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "llama3.2"
KOLEKSIYON = "notlar"
PARCA_BOY = 500
ORTUSME = 80
SURE_EMBED = 60.0
SURE_CHAT = 120.0

CHROMA_YOLU = Path(__file__).resolve().parent / "data" / "chroma"

_istemci = None
_koleksiyon = None


class OllamaError(Exception):
    """Ollama'ya ulaşılamadı ya da yanıt okunamadı."""


def _paragraflar(metin: str) -> list[str]:
    blok: list[str] = []
    paragraflar: list[str] = []
    for satir in metin.splitlines():
        if satir.strip():
            blok.append(satir)
            continue
        if blok:
            paragraf = "\n".join(blok).strip()
            if paragraf:
                paragraflar.append(paragraf)
            blok = []
    if blok:
        paragraf = "\n".join(blok).strip()
        if paragraf:
            paragraflar.append(paragraf)
    return paragraflar


def _parcala(metin: str) -> list[dict]:
    metin = metin.strip()
    if not metin:
        return []
    ham: list[str] = []
    for paragraf in _paragraflar(metin):
        if len(paragraf) <= PARCA_BOY:
            ham.append(paragraf)
            continue
        baslangic = 0
        uzunluk = len(paragraf)
        while baslangic < uzunluk:
            pencere = paragraf[baslangic : baslangic + PARCA_BOY]
            if pencere.strip():
                ham.append(pencere)
            if baslangic + PARCA_BOY >= uzunluk:
                break
            baslangic += PARCA_BOY - ORTUSME
    return [
        {"sira": sira, "metin": parca}
        for sira, parca in enumerate(parca for parca in ham if parca.strip())
    ]


def _ollama_json(yontem: str, yol: str, sure: float, govde: dict | None = None) -> dict:
    secenekler = {}
    if govde is not None:
        secenekler["json"] = govde
    try:
        # Yerel Ollama, ortamda tanımlı vekil sunucuya takılmasın.
        with httpx.Client(timeout=sure, trust_env=False) as istemci:
            yanit = istemci.request(yontem, f"{OLLAMA_URL}{yol}", **secenekler)
            yanit.raise_for_status()
            veri = yanit.json()
    except Exception as exc:
        raise OllamaError("Ollama isteği başarısız") from exc
    if not isinstance(veri, dict):
        raise OllamaError("Ollama yanıtı geçersiz")
    return veri


def _embed(girdi: str | list[str]) -> list[list[float]]:
    veri = _ollama_json(
        "POST",
        "/api/embed",
        SURE_EMBED,
        {"model": EMBED_MODEL, "input": girdi},
    )
    try:
        ham = veri["embeddings"]
    except (KeyError, TypeError) as exc:
        raise OllamaError("embed yanıtı geçersiz") from exc
    if not isinstance(ham, list) or not ham:
        raise OllamaError("embed yanıtı geçersiz")
    vektorler: list[list[float]] = []
    for vektor in ham:
        if not isinstance(vektor, list) or not vektor:
            raise OllamaError("embed yanıtı geçersiz")
        try:
            vektorler.append([float(deger) for deger in vektor])
        except (TypeError, ValueError) as exc:
            raise OllamaError("embed yanıtı geçersiz") from exc
    return vektorler


def _chroma():
    global _istemci
    if _istemci is None:
        CHROMA_YOLU.mkdir(parents=True, exist_ok=True)
        _istemci = chromadb.PersistentClient(path=str(CHROMA_YOLU))
    return _istemci


def _koleksiyon_al():
    global _koleksiyon
    if _koleksiyon is None:
        _koleksiyon = _chroma().get_or_create_collection(
            name=KOLEKSIYON,
            metadata={"hnsw:space": "cosine"},
        )
    return _koleksiyon


def _koleksiyonu_yenile():
    global _koleksiyon
    istemci = _chroma()
    _koleksiyon = None
    try:
        istemci.delete_collection(KOLEKSIYON)
    except Exception as exc:
        ileti = str(exc).lower()
        yok = type(exc).__name__ == "NotFoundError" or "does not exist" in ileti or "not found" in ileti
        if not yok:
            raise
    _koleksiyon = istemci.create_collection(
        name=KOLEKSIYON,
        metadata={"hnsw:space": "cosine"},
    )
    return _koleksiyon


def save(metin: str) -> list[dict]:
    parcalar = _parcala(metin)
    if parcalar:
        vektorler = _embed([parca["metin"] for parca in parcalar])
        if len(vektorler) != len(parcalar):
            raise OllamaError("embed sayısı uyuşmuyor")
    else:
        vektorler = []
    kol = _koleksiyonu_yenile()
    if parcalar:
        kol.add(
            ids=[str(parca["sira"]) for parca in parcalar],
            documents=[parca["metin"] for parca in parcalar],
            embeddings=vektorler,
            metadatas=[{"sira": parca["sira"]} for parca in parcalar],
        )
    return parcalar


def search(soru: str, k: int = 3) -> list[dict]:
    kol = _koleksiyon_al()
    adet = kol.count()
    if adet == 0 or k <= 0:
        return []
    vektor = _embed(soru)[0]
    sonuc = kol.query(
        query_embeddings=[vektor],
        n_results=min(k, adet),
        include=["documents", "metadatas", "distances"],
    )
    belgeler = (sonuc.get("documents") or [[]])[0] or []
    metalar = (sonuc.get("metadatas") or [[]])[0] or []
    mesafeler = (sonuc.get("distances") or [[]])[0] or []
    cikti = []
    for belge, meta, mesafe in zip(belgeler, metalar, mesafeler):
        cikti.append(
            {
                "sira": int(meta["sira"]),
                "metin": belge if isinstance(belge, str) else str(belge),
                "mesafe": round(float(mesafe), 4),
            }
        )
    return cikti


def answer(soru: str, parcalar: list[dict]) -> str:
    sistem = (
        "Yalnızca verilen parçalardaki bilgiyle cevap ver. "
        "Parçalar sorunun cevabını içermiyorsa tam olarak şu yanıtı yaz: Bu metinde yok. "
        "Dışarıdan bilgi ekleme."
    )
    satirlar = [f"[{parca['sira']}] {parca['metin']}" for parca in parcalar]
    satirlar.append(f"Soru: {soru}")
    veri = _ollama_json(
        "POST",
        "/api/chat",
        SURE_CHAT,
        {
            "model": CHAT_MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": sistem},
                {"role": "user", "content": "\n\n".join(satirlar)},
            ],
        },
    )
    try:
        icerik = veri["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise OllamaError("chat yanıtı geçersiz") from exc
    if not isinstance(icerik, str):
        raise OllamaError("chat yanıtı geçersiz")
    return icerik


def durum() -> dict:
    bos = {"ollama": False, "embed_model": False, "chat_model": False}
    try:
        with httpx.Client(timeout=SURE_EMBED, trust_env=False) as istemci:
            yanit = istemci.get(f"{OLLAMA_URL}/api/tags")
            yanit.raise_for_status()
            veri = yanit.json()
        adlar = set()
        for model in veri.get("models") or []:
            if not isinstance(model, dict):
                continue
            ad = model.get("name")
            if not isinstance(ad, str) or not ad:
                continue
            adlar.add(ad.split(":", 1)[0])
        return {
            "ollama": True,
            "embed_model": EMBED_MODEL in adlar,
            "chat_model": CHAT_MODEL in adlar,
        }
    except Exception:
        return bos


def clear() -> None:
    _koleksiyonu_yenile()
