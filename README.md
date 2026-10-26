# mini-rag

Tek sayfalık not sorusu. Yazdığın metin parçalanır, ChromaDB'ye kaydolur. Sorduğun soruya en yakın parçalar bulunur ve cevabı bilgisayarındaki Ollama yazar.

Sayfa dört adım gösterir: metni yaz, parçaları gör, soruyu yaz, bulunan parçaları ve cevabı gör. Her kayıt bir öncekinin yerine geçer.

## Çalıştırma

Ollama yalnızca bu bilgisayarda dinler (`127.0.0.1:11434`). Modeller: `nomic-embed-text` (vektör), `llama3.2` (cevap).

```bash
cd /Users/aybike/Projects/mini-rag
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

Tarayıcıda aç: http://127.0.0.1:8000

Ollama kapalıysa sayfa bunu düz bir cümleyle söyler.
