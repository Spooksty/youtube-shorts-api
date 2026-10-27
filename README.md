# YouTube Shorts automatizācija

Prototips kursam "Programmatūras izstrādes tehnoloģija". Sistēma uztaisa īsu vertikālu video no tēmas: OpenAI uzraksta skriptu, ElevenLabs to ierunā, no Pixabay (vai fal.ai) tiek paņemti vizuālie materiāli un FFmpeg visu samontē kopā ar subtitriem. Gatavo video administrators var apskatīt, labot un apstiprināt.

Komanda: Emīls Juris Gelašs, Ralfs Uvarovs, Uvis Virsnītis, Emīls Žurevičs

## Palaišana

Vajag Docker.

```
cp .env.example .env
docker compose up --build
```

Panelis: http://localhost:5173 (lietotājs `admin`, parole `admin123`)
API: http://localhost:8000/docs

Pēc `.env` izmaiņām: `docker compose up -d api worker`.
Tukša datubāze: `docker compose down -v` un izdzēst `data/`.

Konteineri:
- `db` - PostgreSQL
- `api` - FastAPI
- `worker` - fona process, kas izpilda ģenerēšanas uzdevumus (ar `api` sazinās caur datubāzi)
- `web` - React panelis

## Kas strādā

Pilnībā strādā (dati tiek saglabāti datubāzē un `data/jobs/<id>/`):

1. Kanāli, tēmas, promptu veidnes un publicēšanas grafiks
2. Video ģenerēšana - budžeta pārbaude, tēmas izvēle, skripts ar pārbaudi (līdz 3 mēģinājumiem), balss, materiāli, montāža, tehniskā pārbaude. Katrs solis ir žurnālā, katram API izsaukumam tiek saglabātas izmaksas.
3. Video pārskats - saraksts ar filtriem, atskaņošana, metadatu labošana, apstiprināšana/noraidīšana

Strādā arī pieteikšanās (bloķēšana pēc 5 kļūdām), budžeta iestatījumi, žurnāls, paziņojumi un administratoru konti.

Simulēts:
- YouTube sasaiste un augšupielāde (saglabā izdomātu kanāla un video ID)
- skatījumu statistika lapā "Statistika"

Automātiskā ģenerēšana pēc grafika pēc noklusējuma ir izslēgta, lai netērētu naudu. Ieslēdzama lapā "Budžets un kvota".

## Ārējie servisi

Visi ārējie API ir aiz adapteriem (`backend/app/integrations/`), tos var nomainīt `.env` failā. Ja atslēgas nav, tiek izmantota lokāla versija, tāpēc visu var palaist arī bez maksas kontiem:

- skripts: OpenAI, bez atslēgas - teksts no veidnēm
- balss: ElevenLabs, bez atslēgas - eSpeak NG
- materiāli: `MEDIA_PROVIDER`, pēc noklusējuma `pixabay,fal_images`; bez atslēgām - ar FFmpeg ģenerēti fona klipi

Materiāli katrai ainai: vispirms Pixabay video, ja nekas neder - fal.ai attēls, kuram montāžā pievienota kameras kustība. Pirms izmantošanas katru klipu/attēlu novērtē `gpt-4o-mini` (0-10), der tikai tie, kam vērtējums ir vismaz 7.

ElevenLabs bezmaksas kontā caur API var izmantot tikai "premade" balsis.

Lokālās versijas uzskaita aptuvenas izmaksas, lai varētu notestēt budžeta limitu. `MOCK_FAILURE_RATE` liek tām laiku pa laikam atgriezt kļūdu, lai žurnālā redzētu atkārtojumus.

## Demo

1. Kanāli -> Wild Facts Daily -> Ģenerēt video
2. Pēc ~1 min video gaida apstiprinājumu, to var nolabot un apstiprināt
3. "Space in 30s" video publicējas automātiski
4. Budžetu uzliekot zem iztērētā, jauns uzdevums tiek atlikts
5. Jaunu kanālu nevar aktivizēt, kamēr tas nav sasaistīts ar YouTube
6. Kanālam bez tēmām ģenerēšana beidzas ar kļūdu "Nav pieejamu tēmu"

## Testi

```
docker compose exec api pytest
```
