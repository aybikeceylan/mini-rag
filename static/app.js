"use strict";

const ORNEK_METIN = [
  "Kahve 40 lira, çay 15 lira. Tatlı olarak kek 50 liradır.",
  "",
  "Dükkan pazartesi günleri kapalıdır. Diğer günler 09:00-18:00 açıktır.",
  "",
  "Kurucu Ayşe, dükkanı 2019 yılında Kadıköy'de açtı.",
].join("\n");

const OLLAMA_KAPALI = "Ollama kapalı. Bu bilgisayarda 127.0.0.1:11434 açık olmalı.";
const SUNUCU_YOK = "Sunucuya ulaşılamadı.";
const ISTEK_OLMADI = "İstek tamamlanamadı.";

let mesgul = false;
let eylem = 0;

function kullaniciHatasi(metin) {
  const err = new Error(metin);
  err.kullanici = true;
  return err;
}

function nesneMi(data) {
  return !!data && typeof data === "object" && !Array.isArray(data);
}

function hataGoster(metin) {
  const el = document.getElementById("hata");
  if (!metin) {
    el.textContent = "";
    el.hidden = true;
    return;
  }
  el.hidden = false;
  el.textContent = metin;
}

function durumYaz(mesajlar) {
  const kutu = document.getElementById("durum");
  kutu.replaceChildren();
  for (const metin of mesajlar) {
    const p = document.createElement("p");
    p.textContent = metin;
    kutu.append(p);
  }
}

function butonlariAyarla(kilit) {
  for (const id of ["kaydet", "sor", "temizle"]) {
    document.getElementById(id).disabled = kilit;
  }
}

function mesafeYaz(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "—";
  }
  return value.toLocaleString("tr-TR", { maximumFractionDigits: 6 });
}

function kisaAlan(ad, deger) {
  const p = document.createElement("p");
  p.className = "field";
  const name = document.createElement("span");
  name.className = "name";
  name.textContent = ad;
  p.append(name, document.createTextNode(": " + deger));
  return p;
}

function uzunAlan(ad, deger) {
  const p = document.createElement("p");
  p.className = "field block";
  const name = document.createElement("span");
  name.className = "name";
  name.textContent = ad;
  const value = document.createElement("span");
  value.className = "value";
  value.textContent = deger;
  p.append(name, value);
  return p;
}

function parcaOgesi(parca, mesafeVar) {
  const li = document.createElement("li");
  const sira = parca.sira === undefined || parca.sira === null ? "—" : String(parca.sira);
  li.append(kisaAlan("sıra", sira));
  li.append(uzunAlan("metin", typeof parca.metin === "string" ? parca.metin : ""));
  if (mesafeVar) {
    li.append(kisaAlan("mesafe (küçük olan daha yakın)", mesafeYaz(parca.mesafe)));
  }
  return li;
}

function listeyiYaz(ul, bos, parcalar, mesafeVar) {
  ul.replaceChildren();
  for (const parca of parcalar) {
    if (!nesneMi(parca)) continue;
    ul.append(parcaOgesi(parca, mesafeVar));
  }
  bos.hidden = ul.children.length > 0;
}

function cevabiYaz(metin) {
  const el = document.getElementById("cevap");
  const varMi = typeof metin === "string" && metin.trim() !== "";
  el.textContent = varMi ? metin : "Henüz cevap yok.";
  el.classList.toggle("empty", !varMi);
}

function parcalariAl(data) {
  if (!nesneMi(data) || !Array.isArray(data.parcalar)) {
    throw kullaniciHatasi(ISTEK_OLMADI);
  }
  return data.parcalar;
}

async function istek(path, options) {
  const opts = {
    method: options && options.method ? options.method : "GET",
    headers: { Accept: "application/json" },
  };
  if (options && Object.prototype.hasOwnProperty.call(options, "body")) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(options.body);
  }

  let response;
  try {
    response = await fetch(path, opts);
  } catch {
    throw kullaniciHatasi(SUNUCU_YOK);
  }

  let text = "";
  try {
    text = await response.text();
  } catch {
    throw kullaniciHatasi(SUNUCU_YOK);
  }

  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    if (nesneMi(data) && typeof data.hata === "string" && data.hata.trim() !== "") {
      throw kullaniciHatasi(data.hata);
    }
    throw kullaniciHatasi(ISTEK_OLMADI);
  }
  return data;
}

async function durumuYukle() {
  const benim = eylem;
  try {
    const data = await istek("/api/durum");
    if (!nesneMi(data) || typeof data.ollama !== "boolean") {
      throw kullaniciHatasi(ISTEK_OLMADI);
    }
    if (!data.ollama) {
      durumYaz([OLLAMA_KAPALI]);
      return;
    }
    const mesajlar = [];
    if (data.embed_model === false) mesajlar.push("nomic-embed-text modeli eksik.");
    if (data.chat_model === false) mesajlar.push("llama3.2 modeli eksik.");
    durumYaz(mesajlar);
  } catch (err) {
    if (benim !== eylem) return;
    hataGoster(err && err.kullanici ? err.message : SUNUCU_YOK);
  }
}

async function kaydet() {
  const data = await istek("/api/notlar", {
    method: "POST",
    body: { metin: document.getElementById("metin").value },
  });
  const parcalar = parcalariAl(data);
  listeyiYaz(document.getElementById("kayitli"), document.getElementById("kayit-bos"), parcalar, false);
  listeyiYaz(document.getElementById("bulunan"), document.getElementById("bulunan-bos"), [], true);
  cevabiYaz("");
}

async function sor() {
  const data = await istek("/api/sor", {
    method: "POST",
    body: { soru: document.getElementById("soru").value },
  });
  const parcalar = parcalariAl(data);
  if (typeof data.cevap !== "string") {
    throw kullaniciHatasi(ISTEK_OLMADI);
  }
  listeyiYaz(document.getElementById("bulunan"), document.getElementById("bulunan-bos"), parcalar, true);
  cevabiYaz(data.cevap);
}

async function temizle() {
  const data = await istek("/api/notlar", { method: "DELETE" });
  if (!nesneMi(data) || data.tamam !== true) {
    throw kullaniciHatasi(ISTEK_OLMADI);
  }
  document.getElementById("metin").value = "";
  listeyiYaz(document.getElementById("kayitli"), document.getElementById("kayit-bos"), [], false);
  listeyiYaz(document.getElementById("bulunan"), document.getElementById("bulunan-bos"), [], true);
  cevabiYaz("");
}

async function calistir(is) {
  if (mesgul) return;
  mesgul = true;
  eylem += 1;
  butonlariAyarla(true);
  hataGoster("");
  try {
    await is();
  } catch (err) {
    hataGoster(err && err.kullanici ? err.message : SUNUCU_YOK);
  } finally {
    mesgul = false;
    butonlariAyarla(false);
  }
}

function basla() {
  document.getElementById("ornek").addEventListener("click", () => {
    const kutu = document.getElementById("metin");
    kutu.value = ORNEK_METIN;
    kutu.focus();
  });
  document.getElementById("kaydet").addEventListener("click", () => calistir(kaydet));
  document.getElementById("temizle").addEventListener("click", () => calistir(temizle));
  document.getElementById("sor").addEventListener("click", () => calistir(sor));
  document.getElementById("soru").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      calistir(sor);
    }
  });
  durumuYukle();
}

document.addEventListener("DOMContentLoaded", basla);
