"""HTTP katmanı. Parçalama ve Ollama rag.py içindedir."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import rag

KOK = Path(__file__).resolve().parent
OLLAMA_HATA = "Ollama kapalı. Bu bilgisayarda 127.0.0.1:11434 açık olmalı."

app = FastAPI()


class MetinGovdesi(BaseModel):
    metin: str


class SoruGovdesi(BaseModel):
    soru: str


def _ollama_yaniti():
    return JSONResponse(status_code=503, content={"hata": OLLAMA_HATA})


@app.get("/")
def anasayfa():
    return FileResponse(KOK / "static" / "index.html")


@app.post("/api/notlar")
def notu_kaydet(govde: MetinGovdesi):
    if not govde.metin.strip():
        return JSONResponse(status_code=400, content={"hata": "Metin boş."})
    try:
        parcalar = rag.save(govde.metin)
    except rag.OllamaError:
        return _ollama_yaniti()
    return {"parca_sayisi": len(parcalar), "parcalar": parcalar}


@app.post("/api/sor")
def soruyu_yanitla(govde: SoruGovdesi):
    if not govde.soru.strip():
        return JSONResponse(status_code=400, content={"hata": "Soru boş."})
    try:
        parcalar = rag.search(govde.soru, k=3)
    except rag.OllamaError:
        return _ollama_yaniti()
    if not parcalar:
        return JSONResponse(status_code=400, content={"hata": "Önce bir metin kaydet."})
    try:
        cevap = rag.answer(govde.soru, parcalar)
    except rag.OllamaError:
        return _ollama_yaniti()
    return {"cevap": cevap, "parcalar": parcalar}


@app.get("/api/durum")
def durumu_getir():
    return rag.durum()


@app.delete("/api/notlar")
def notu_sil():
    rag.clear()
    return {"tamam": True}


app.mount("/static", StaticFiles(directory=KOK / "static"), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
