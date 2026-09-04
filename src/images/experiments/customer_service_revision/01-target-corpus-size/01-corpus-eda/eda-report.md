# EDA corpus customer service

Dibuat: `2026-08-30T19:31:13.667517+00:00`  
Datasource: `netgear-customer-service` (`077b19c1-b65c-4447-8394-d96a91d07337`)  
Manifest SHA-256: `7fdc2c78ad23bbd74fc790fb4395d8be0f97fbb4c9242d91a3f6e52d58b30b42`

## Snapshot

- Dokumen aktif: **9**
- Halaman: **1,400**
- Teks hasil parsing: **2,171,615 karakter**
- Text block parser: **1,566**
- Leaf outline kandidat untuk random pick: **1,240**
- Text block yang lolos diagnostic source: **1,566** (lookup context, bukan pool pertanyaan)

## Diagnostics halaman dan block

- Halaman kosong: **0**; halaman dengan gambar: **112**
- Halaman dengan teks tabel: **90**; teks figure: **45**
- Kuantil karakter text block: p50 **1,017**, p90 **2,422**, p95 **2,872**, p99 **3,748**, max **10,792**
- Keanggotaan cluster duplicate exact: **577**; template: **675**

## Coverage per dokumen

| Dokumen | Halaman | Byte | Bookmark | Heading | Text block | Karakter teks | Parser | Raw hash |
|---|---:|---:|---:|---:|---:|---:|---|---|
| netgear-cm2000.pdf | 26 | 2,586,464 | 29 | 28 | 29 | 26,175 | generic-outline@1.0.0 | PASS |
| netgear-lm1200.pdf | 105 | 3,987,338 | 105 | 104 | 105 | 137,125 | generic-outline@1.0.0 | PASS |
| netgear-r6350.pdf | 204 | 1,820,508 | 226 | 225 | 226 | 325,166 | generic-outline@1.0.0 | PASS |
| netgear-r7000.pdf | 186 | 4,464,523 | 213 | 212 | 213 | 277,435 | generic-outline@1.0.0 | PASS |
| netgear-rax120.pdf | 175 | 2,353,363 | 202 | 201 | 202 | 286,449 | generic-outline@1.0.0 | PASS |
| netgear-rax50.pdf | 160 | 1,329,644 | 185 | 184 | 185 | 259,678 | generic-outline@1.0.0 | PASS |
| netgear-raxe500.pdf | 169 | 3,437,401 | 192 | 191 | 192 | 268,433 | generic-outline@1.0.0 | PASS |
| netgear-rbk852.pdf | 161 | 1,527,721 | 183 | 182 | 183 | 247,213 | generic-outline@1.0.0 | PASS |
| netgear-xr500.pdf | 214 | 2,123,687 | 231 | 230 | 231 | 343,941 | generic-outline@1.0.0 | PASS |

## Analisis outline

Satu node outline merepresentasikan satu heading parser. `Leaf` adalah outline tanpa child heading dan menjadi unit kandidat untuk random pick; parent outline tetap disimpan untuk memahami hierarki dan context.

| Dokumen | Node outline | Top-level | Leaf | Kandidat outline | Kedalaman maksimum |
|---|---:|---:|---:|---:|---:|
| netgear-cm2000.pdf | 28 | 4 | 22 | 22 | 3 |
| netgear-lm1200.pdf | 104 | 10 | 84 | 84 | 3 |
| netgear-r6350.pdf | 225 | 16 | 175 | 175 | 4 |
| netgear-r7000.pdf | 212 | 15 | 168 | 168 | 4 |
| netgear-rax120.pdf | 201 | 13 | 161 | 161 | 3 |
| netgear-rax50.pdf | 184 | 13 | 148 | 148 | 3 |
| netgear-raxe500.pdf | 191 | 12 | 155 | 155 | 3 |
| netgear-rbk852.pdf | 182 | 11 | 144 | 144 | 3 |
| netgear-xr500.pdf | 230 | 18 | 183 | 183 | 3 |

### Outline tingkat atas per dokumen

Daftar ini menunjukkan cakupan besar manual sebelum melihat leaf outline. Tree lengkap dan page span setiap node berada di `outline-report.md`.

| Dokumen | Outline tingkat atas |
|---|---|
| netgear-cm2000.pdf | Hardware Setup<br>Manage Your Network<br>Troubleshooting<br>Supplemental Information |
| netgear-lm1200.pdf | Introduction and Hardware Overview<br>Get Started<br>Manage the Modem LAN Settings<br>Manage the Mobile Broadband Connection<br>Secure Your Network<br>Manage the Modem and Monitor Usage and the Network<br>Frequently Asked Questions<br>Alerts and Troubleshooting<br>Default Settings and Specifications<br>Wall-Mount the Modem |
| netgear-r6350.pdf | Hardware Overview of the Router<br>Connect to the Network and Access the Router<br>Specify Your Internet Settings<br>Optimize Performance<br>Manage the Basic WiFi Network Settings<br>Control Access to the Internet<br>Share USB Storage Devices Attached to the Router<br>Use Dynamic DNS to Access USB Storage Devices Through the Internet<br>Use the Router as a Media Server<br>Manage the WAN and LAN Network Settings<br>Manage Your Router<br>Manage the Advanced WiFi Features<br>Use VPN to Access Your Network<br>Manage Port Forwarding and Port Triggering<br>Troubleshooting<br>Supplemental Information |
| netgear-r7000.pdf | Hardware Setup<br>Connect to the Network and Access the Router<br>Specify Your Internet Settings<br>Control Access to the Internet<br>Optimize Performance<br>Manage Network Settings<br>Manage Your Router<br>Share USB Storage Devices Attached to the Router<br>Use Dynamic DNS to Access USB Storage Devices Through the Internet<br>Use the Router as a Media Server<br>Share a USB Printer<br>Use VPN to Access Your Network<br>Manage Port Forwarding and Port Triggering<br>Troubleshooting<br>Supplemental Information |
| netgear-rax120.pdf | Hardware Setup<br>Connect to the network and access the router<br>Specify Your Internet Settings<br>Control Access to the Internet<br>Optimize Performance<br>Manage Network Settings<br>Manage Your Router<br>Share USB Storage Devices Attached to the Router<br>Use Dynamic DNS to Access USB Storage Devices Through the Internet<br>Use OpenVPN to Access Your Network<br>Manage port forwarding and port triggering<br>Troubleshooting<br>Supplemental Information |
| netgear-rax50.pdf | Hardware Setup<br>Connect to the Network and Access the Router<br>Specify Your Internet Settings<br>Control Access to the Internet<br>Manage Network Settings<br>Optimize Performance<br>Manage Your Router<br>Share USB Storage Devices Attached to the Router<br>Use Dynamic DNS to Access USB Storage Devices Through the Internet<br>Use OpenVPN to Access Your Network<br>Manage Port Forwarding and Port Triggering<br>Troubleshooting<br>Supplemental Information |
| netgear-raxe500.pdf | Hardware Setup<br>Connect to the network and access the router<br>Specify Your Internet Settings<br>Control Access to the Internet<br>Manage Network Settings<br>Manage Your Router<br>Share USB Storage Devices Attached to the Router<br>Use Dynamic DNS to Access USB Storage Devices Through the Internet<br>Use VPN to Access Your Network<br>Manage port forwarding and port triggering<br>Troubleshooting<br>Supplemental Information |
| netgear-rbk852.pdf | Overview<br>Connect to the Network and Access the Router<br>Specify Your Internet Settings<br>Control Access to the Internet<br>Specify WiFi Settings<br>Specify Network Settings<br>Mantain and Monitor Your Network<br>Use OpenVPN to Access Your Network<br>Customize Internet Traffic Rules for Ports<br>Troubleshooting<br>Supplemental Information |
| netgear-xr500.pdf | Hardware Setup<br>Connect to the Network and Access the Router<br>Specify Your Internet Settings<br>Customize Quality of Service Settings and Optimize Gaming<br>Monitor Devices and the Network and View Router Information<br>Control Access to the Internet<br>Manage the Router’s Network Settings<br>Manage the Router’s WiFi Settings<br>Maintain the Router<br>Share USB Storage Devices Attached to the Router<br>Use Dynamic DNS to Access USB Storage Devices Through the Internet<br>Use the Router as a Media Server<br>Share a USB Printer<br>Use OpenVPN to Access Your Network<br>Use VPN to Access An External Network<br>Manage and Customize Internet Traffic Rules for Ports<br>Troubleshooting<br>Supplemental Information |

Daftar lengkap outline per dokumen: `/home/fairuz/Documents/TA/FR/dpo/experiments/offline-rag-experiments/customer_service_revision/01-target-corpus-size/01-corpus-eda/outline-report.md`.
Frame outline untuk random pick: `/home/fairuz/Documents/TA/FR/dpo/experiments/offline-rag-experiments/customer_service_revision/01-target-corpus-size/01-corpus-eda/question_outline_frame.csv` (SHA-256 `b759d9417c9f7c4f9fc27bc767b7c8f75530ab6e5f2945e039169a8e9c55a966`).

## Coverage struktural question-source

Pelabelan topic otomatis dinonaktifkan. Tabel ini adalah diagnostic text-block berdasarkan dokumen dan page bin relatif; ia bukan dasar random pick. Random pick menggunakan `question_outline_frame.csv`, sedangkan topic/family ditetapkan saat review anotasi pertanyaan.

| Document | P1 | P2 | P3 | P4 | P5 | Total |
|---|---:|---:|---:|---:|---:|---:|
| netgear-cm2000.pdf | 4 | 7 | 6 | 7 | 5 | 29 |
| netgear-lm1200.pdf | 19 | 16 | 18 | 26 | 26 | 105 |
| netgear-r6350.pdf | 36 | 38 | 49 | 53 | 50 | 226 |
| netgear-r7000.pdf | 35 | 40 | 44 | 46 | 48 | 213 |
| netgear-rax120.pdf | 33 | 33 | 38 | 49 | 49 | 202 |
| netgear-rax50.pdf | 32 | 30 | 35 | 42 | 46 | 185 |
| netgear-raxe500.pdf | 32 | 35 | 35 | 46 | 44 | 192 |
| netgear-rbk852.pdf | 34 | 32 | 41 | 43 | 33 | 183 |
| netgear-xr500.pdf | 36 | 40 | 50 | 50 | 55 | 231 |

## Gate

- Census berisi 9 row dan setiap row memiliki raw hash unik.
- Identitas/config parser generic-outline dan checksum artifact dicatat per dokumen.
- Cluster duplicate/template hanya diagnostics; tidak ada dokumen sumber yang dihapus.
- Source frame adalah lookup text block; random pick pertanyaan dilakukan pada leaf outline frame dan tetap memerlukan review manusia pada Langkah 2.
- Klasifikasi keyword/topic otomatis dinonaktifkan; tidak ada topic comparison/model yang diinferensikan.

## Artefak

Tabel transition: `/home/fairuz/Documents/TA/FR/dpo/experiments/offline-rag-experiments/customer_service_revision/01-target-corpus-size/01-corpus-eda/transition`  
Handoff question-source: `/home/fairuz/Documents/TA/FR/dpo/experiments/offline-rag-experiments/customer_service_revision/01-target-corpus-size/01-corpus-eda/question_source_frame.csv`  
SHA-256 frame question-source: `f1058eb82d4542c257f56689be0d40656cd4397776cd98ec9f9837ed1f8f51de`  
Analisis outline lengkap: `/home/fairuz/Documents/TA/FR/dpo/experiments/offline-rag-experiments/customer_service_revision/01-target-corpus-size/01-corpus-eda/outline-report.md`  
Frame outline question: `/home/fairuz/Documents/TA/FR/dpo/experiments/offline-rag-experiments/customer_service_revision/01-target-corpus-size/01-corpus-eda/question_outline_frame.csv` (SHA-256 `b759d9417c9f7c4f9fc27bc767b7c8f75530ab6e5f2945e039169a8e9c55a966`)  
Visual yang dipertahankan: `/home/fairuz/Documents/TA/FR/dpo/experiments/offline-rag-experiments/customer_service_revision/01-target-corpus-size/01-corpus-eda/00_corpus_pipeline_flow.png`, `/home/fairuz/Documents/TA/FR/dpo/experiments/offline-rag-experiments/customer_service_revision/01-target-corpus-size/01-corpus-eda/01_document_page_bytes.png`, dan `/home/fairuz/Documents/TA/FR/dpo/experiments/offline-rag-experiments/customer_service_revision/01-target-corpus-size/01-corpus-eda/02_outline_and_block_coverage.png`
Diagnostics parser dan redundancy tetap berada di file CSV/JSON transition; frame question-source berada di luar transition karena menjadi input Langkah 2.

Laporan ini hanya untuk Langkah 1. Tidak ada question set, profile, index, atau retrieval run yang dibuat.
