#!/usr/bin/env python3
"""Author the Customer Service questions from the complete local context packets.

This is the Codex-current-model authoring pass.  It starts from the reviewed v1
wording/answers, re-reads each complete v2 packet, and records the minimal evidence
choice without forcing a fixed block count or unioning the packet.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
RUN = ROOT / "experiments/offline-rag-experiments/customer_service_revision/02-question-budget-and-gold"
BASELINE = RUN / "03-question-generation-and-gold/runs/selection-v1/03-frozen/question-set.csv"
PACKETS = RUN / "02-context-materialization/runs/selection-v2-multiblock/context-packets.jsonl"
OUT = RUN / "03-question-generation-and-gold/runs/selection-v2-multiblock/00-draft"


# These edits keep one customer intent per pair while allowing a genuinely
# multi-block answer when two parts of the packet are both needed.
OVERRIDES: dict[str, tuple[str, str, str, str]] = {
    "Q-001": (
        "What ports and button are on the back of the CM2000?",
        "Port dan tombol apa saja yang ada di bagian belakang CM2000?",
        "The rear panel has a Reset button, an Ethernet port, a coaxial cable port, and a DC power connector.",
        "Panel belakang memiliki tombol Reset, port Ethernet, port kabel koaksial, dan konektor daya DC.",
    ),
    "Q-018": (
        "My LM1200 cannot connect to mobile broadband. What should I check?",
        "LM1200 saya tidak dapat terhubung ke jaringan broadband seluler. Apa yang perlu diperiksa?",
        "Check that mobile coverage is available, the account is active, the SIM is inserted correctly, and the SIM PIN is correct if security is enabled.",
        "Periksa ketersediaan jaringan seluler, status akun, posisi SIM, dan PIN SIM jika keamanan SIM diaktifkan.",
    ),
    "Q-045": (
        "Which password should I use to join the RAX120 Wi-Fi network?",
        "Kata sandi mana yang harus saya gunakan untuk terhubung ke Wi-Fi RAX120?",
        "Use the Wi-Fi network key printed on the router label. It is different from the router administrator password.",
        "Gunakan kunci jaringan Wi-Fi yang tercetak pada label router. Kata sandi ini berbeda dari kata sandi administrator router.",
    ),
    "Q-071": (
        "Why would I enable 20/40 MHz coexistence on the RAXE500?",
        "Mengapa saya perlu mengaktifkan coexistence 20/40 MHz pada RAXE500?",
        "It can reduce interference from nearby Wi-Fi by allowing narrower channels, but it may reduce speed. It applies to the 2.4 GHz radio, not 5 GHz.",
        "Fitur ini dapat mengurangi gangguan dari Wi-Fi di sekitar dengan memakai kanal yang lebih sempit, tetapi kecepatannya mungkin berkurang. Fitur ini berlaku untuk radio 2,4 GHz, bukan 5 GHz.",
    ),
}


# Prefixes identify the blocks selected after reading the complete packet.  The
# finalizer resolves each prefix to the full audited block ID and checks all
# provenance fields.  A pair is multi-block only when the question describes a
# single workflow whose answer needs both pieces; no block is added as padding.
MULTI_BLOCK_DECISIONS: dict[str, dict[str, Any]] = {
    "Q-003": {
        "prefixes": ["8fd1b794", "8ed480ba"],
        "question_en": "After activating my CM2000, how do I connect it to a router and check whether I am getting the subscribed Internet speed?",
        "question_id": "Setelah layanan CM2000 aktif, bagaimana cara menghubungkannya ke router dan memeriksa apakah kecepatannya sesuai paket saya?",
        "answer_en": "Reboot the CM2000 and wait for the Internet LED to become solid white. Connect its Ethernet port to the router's WAN or Internet port, power on the router, wait until it is ready, and connect your computer to the router. Then use your Internet provider's speed-test site; contact the provider if the measured speed is below your subscription.",
        "answer_id": "Nyalakan ulang CM2000 dan tunggu LED Internet menyala putih tanpa berkedip. Hubungkan port Ethernet-nya ke port WAN atau Internet pada router, nyalakan router, tunggu sampai siap, lalu hubungkan komputer ke router. Setelah itu gunakan situs uji kecepatan penyedia Internet; hubungi penyedia jika hasilnya di bawah paket Anda.",
    },
    "Q-004": {
        "prefixes": ["4cb893dc", "0de5a970"],
        "question_en": "How do I sign in to the CM2000 and then change the administrator password?",
        "question_id": "Bagaimana cara masuk ke CM2000 lalu mengubah kata sandi administrator?",
        "answer_en": "Connect to the CM2000, open http://192.168.100.1, and sign in as admin using the password on the product label. Then choose ADVANCED > Administration > Set Password, enter the old password and the new password twice, and select Apply. Use a secure 6–32 character password.",
        "answer_id": "Hubungkan perangkat ke CM2000, buka http://192.168.100.1, lalu masuk sebagai admin dengan kata sandi pada label produk. Pilih ADVANCED > Administration > Set Password, masukkan kata sandi lama dan kata sandi baru dua kali, lalu pilih Apply. Gunakan kata sandi aman sepanjang 6–32 karakter.",
    },
    "Q-006": {
        "prefixes": ["32161388", "62f9a09d"],
        "question_en": "How do I reset the CM2000 from its web page, and what should I expect afterward?",
        "question_id": "Bagaimana cara mereset CM2000 dari halaman web, dan apa yang terjadi setelahnya?",
        "answer_en": "Sign in at http://192.168.100.1, open the ADVANCED tab, choose Factory reset, confirm with OK, and do not interrupt the modem while it reboots. The reset erases configured settings and takes about one minute; afterward the password is the one on the product label and the LAN address is 192.168.100.1.",
        "answer_id": "Masuk di http://192.168.100.1, buka tab ADVANCED, pilih Factory reset, konfirmasi dengan OK, dan jangan mengganggu modem saat melakukan boot ulang. Reset menghapus pengaturan yang dibuat dan memerlukan sekitar satu menit; setelahnya kata sandi kembali ke yang ada pada label produk dan alamat LAN adalah 192.168.100.1.",
    },
    "Q-007": {
        "prefixes": ["32161388", "c5c4c17f"],
        "question_en": "How do I reset the CM2000 with the button when I cannot use its web page, and what happens afterward?",
        "question_id": "Bagaimana cara mereset CM2000 dengan tombol saat halaman web tidak dapat digunakan, dan apa yang terjadi setelahnya?",
        "answer_en": "On the back of the CM2000, press and hold the Reset button with a straightened paper clip until the modem reboots. This erases the configured settings and takes about one minute. The password returns to the value on the product label and the LAN address remains 192.168.100.1.",
        "answer_id": "Di bagian belakang CM2000, tekan dan tahan tombol Reset dengan penjepit kertas yang diluruskan sampai modem melakukan boot ulang. Tindakan ini menghapus pengaturan yang dibuat dan memerlukan sekitar satu menit. Kata sandi kembali ke nilai pada label produk dan alamat LAN tetap 192.168.100.1.",
    },
    "Q-013": {
        "prefixes": ["44157573", "cf1f57e0"],
        "question_en": "How can I choose automatic or manual mobile-network connection on the LM1200?",
        "question_id": "Bagaimana cara memilih koneksi jaringan seluler otomatis atau manual pada LM1200?",
        "answer_en": "In Settings > Mobile > Preferences, choose Never for manual connection, Always except when roaming, or Always for automatic connection, then submit the setting. With manual mode, open the dashboard and select Connect or Disconnect as needed. Always can incur roaming charges outside your provider's coverage.",
        "answer_id": "Di Settings > Mobile > Preferences, pilih Never untuk koneksi manual, Always except when roaming, atau Always untuk koneksi otomatis, lalu kirim pengaturan. Dalam mode manual, buka dashboard dan pilih Connect atau Disconnect sesuai kebutuhan. Opsi Always dapat menimbulkan biaya roaming di luar jangkauan penyedia.",
    },
    "Q-021": {
        "prefixes": ["b60ce24d", "ad49e55f"],
        "question_en": "What should I check before setting up a 6to4 IPv6 connection on the R6350?",
        "question_id": "Apa yang perlu diperiksa sebelum menyiapkan koneksi IPv6 6to4 pada R6350?",
        "answer_en": "Make sure the router's IPv4 Internet connection works first. In ADVANCED > Advanced Setup > IPv6, select 6to4 Tunnel, choose an automatic or static relay, set DNS and address assignment, and apply the settings. Enter IPv6 values using valid colon-separated hexadecimal groups: no more than eight groups, four hexadecimal characters per group, and no double-colon sequence beyond the allowed compression.",
        "answer_id": "Pastikan koneksi Internet IPv4 router berfungsi terlebih dahulu. Di ADVANCED > Advanced Setup > IPv6, pilih 6to4 Tunnel, pilih relay otomatis atau statis, atur DNS dan penetapan alamat, lalu terapkan. Masukkan nilai IPv6 dengan kelompok heksadesimal yang dipisahkan titik dua secara valid: maksimal delapan kelompok, maksimal empat karakter heksadesimal per kelompok, dan tidak ada rangkaian titik dua berlebih.",
    },
    "Q-022": {
        "prefixes": ["ae418564", "d4e1d4fc"],
        "question_en": "How do I decide whether to change the R6350's MTU and apply a safe value?",
        "question_id": "Bagaimana menentukan apakah MTU R6350 perlu diubah dan menerapkan nilai yang aman?",
        "answer_en": "Leave the default MTU unless your ISP or support recommends a change, because an incorrect value can prevent websites or secure services from opening. If a change is necessary, open ADVANCED > Setup > WAN Setup, enter a value from 64 to 1500, and apply it; 1500 is typical Ethernet, 1492 is common for PPPoE, and 1436 for PPTP or VPN.",
        "answer_id": "Biarkan MTU bawaan kecuali penyedia Internet atau dukungan teknis menyarankan perubahan, karena nilai yang salah dapat membuat situs atau layanan aman tidak terbuka. Jika perlu diubah, buka ADVANCED > Setup > WAN Setup, masukkan nilai 64 hingga 1500, lalu terapkan; 1500 umum untuk Ethernet, 1492 untuk PPPoE, dan 1436 untuk PPTP atau VPN.",
    },
    "Q-037": {
        "prefixes": ["79d677ad", "c63a4385"],
        "question_en": "How can I enable remote management on the R7000 and then connect to it from outside home safely?",
        "question_id": "Bagaimana cara mengaktifkan pengelolaan jarak jauh pada R7000 lalu mengaksesnya dari luar rumah dengan aman?",
        "answer_en": "In ADVANCED > Advanced Setup > Remote Management, turn the feature on, restrict access to only the external IP addresses you need, choose a custom port from 1024–65535, and apply. From outside your home network, open the router's WAN IP followed by a colon and that port, for example http://134.177.0.123:8443.",
        "answer_id": "Di ADVANCED > Advanced Setup > Remote Management, aktifkan fitur, batasi akses hanya ke alamat IP eksternal yang diperlukan, pilih port khusus 1024–65535, lalu terapkan. Dari luar jaringan rumah, buka IP WAN router diikuti titik dua dan port tersebut, misalnya http://134.177.0.123:8443.",
    },
    "Q-063": {
        "prefixes": ["a13c3553", "9078acec", "0b9dd330"],
        "question_en": "How do I set up the RAX50 OpenVPN service so I can connect from my laptop while away?",
        "question_id": "Bagaimana cara menyiapkan layanan OpenVPN RAX50 agar saya dapat terhubung dari laptop saat bepergian?",
        "answer_en": "OpenVPN creates an encrypted client-to-gateway connection between your laptop and the router; the router is not an external VPN client for all home Internet traffic. Sign in to ADVANCED > Advanced Setup > VPN Service, enable the service, apply it, and download the client package and configuration files. Install the OpenVPN client on the laptop, then connect using the router's DDNS name or static WAN address.",
        "answer_id": "OpenVPN membuat koneksi terenkripsi antara laptop dan router; router bukan klien VPN eksternal untuk seluruh lalu lintas Internet rumah. Masuk ke ADVANCED > Advanced Setup > VPN Service, aktifkan layanan, terapkan, lalu unduh paket klien dan berkas konfigurasi. Pasang klien OpenVPN di laptop, kemudian terhubung menggunakan nama DDNS atau alamat WAN statis router.",
    },
    "Q-072": {
        "prefixes": ["09ef238c", "25c77477"],
        "question_en": "How do I choose an Ethernet port-aggregation mode on the RAXE500 and connect a compatible device?",
        "question_id": "Bagaimana cara memilih mode agregasi port Ethernet pada RAXE500 dan menghubungkan perangkat yang kompatibel?",
        "answer_en": "Configure aggregation on the switch or NAS first and make sure it supports 802.3ad LACP. In ADVANCED > Advanced Setup > Ethernet Port Aggregation, choose Enable (LACP) for a compatible device or Static only when the device supports static LAG, then apply and connect the device to router ports 3 and 4. Disable leaves the ports independent.",
        "answer_id": "Atur agregasi pada switch atau NAS terlebih dahulu dan pastikan mendukung LACP 802.3ad. Di ADVANCED > Advanced Setup > Ethernet Port Aggregation, pilih Enable (LACP) untuk perangkat yang kompatibel atau Static hanya jika perangkat mendukung LAG statis, lalu terapkan dan hubungkan perangkat ke port 3 dan 4 router. Disable membuat port tetap terpisah.",
    },
    "Q-079": {
        "prefixes": ["de3de3b9", "bafbe93c"],
        "question_en": "How do I choose the RBK852 IPv6 connection type and avoid entering an invalid IPv6 address?",
        "question_id": "Bagaimana cara memilih jenis koneksi IPv6 pada RBK852 dan menghindari alamat IPv6 yang tidak valid?",
        "answer_en": "Open ADVANCED > Advanced > IPv6 and choose Auto Detect when you are unsure, or Auto Config when the ISP uses IPv6 without PPPoE, DHCP, or a fixed setup. If you enter an address, use valid colon-separated hexadecimal groups: no more than eight groups, no group over four characters, and no invalid run of colons. Apply the setting when finished.",
        "answer_id": "Buka ADVANCED > Advanced > IPv6 dan pilih Auto Detect jika tidak yakin, atau Auto Config jika penyedia memakai IPv6 tanpa PPPoE, DHCP, atau pengaturan tetap. Jika memasukkan alamat, gunakan kelompok heksadesimal yang dipisahkan titik dua secara valid: maksimal delapan kelompok, tidak ada kelompok lebih dari empat karakter, dan tidak ada rangkaian titik dua yang tidak valid. Terapkan setelah selesai.",
    },
    "Q-082": {
        "prefixes": ["a6546993", "6bb5767a"],
        "question_en": "How do I enable WAN aggregation on the RBR860, and how can I switch back to the normal 10G port?",
        "question_id": "Bagaimana cara mengaktifkan WAN aggregation pada RBR860, dan bagaimana cara kembali ke port 10G biasa?",
        "answer_en": "Use a modem that supports LACP, configure aggregation on the modem, then select WAN aggregation (10 Gbps + 1 Gbps, LACP) under ADVANCED > Setup > Internet Setup on the RBR860 and apply it. Connect the router's 10G Internet port and port 1 to two modem Ethernet ports. To revert, select Internet port (10 Gbps) in WAN Preference and apply.",
        "answer_id": "Gunakan modem yang mendukung LACP, atur agregasi pada modem, lalu pilih WAN aggregation (10 Gbps + 1 Gbps, LACP) di ADVANCED > Setup > Internet Setup pada RBR860 dan terapkan. Hubungkan port Internet 10G dan port 1 router ke dua port Ethernet modem. Untuk kembali, pilih Internet port (10 Gbps) pada WAN Preference lalu terapkan.",
    },
    "Q-096": {
        "prefixes": ["c929ed63", "1d4788df"],
        "question_en": "How do I make XR500 USB storage available from outside home using FTP?",
        "question_id": "Bagaimana cara membuat penyimpanan USB XR500 tersedia dari luar rumah menggunakan FTP?",
        "answer_en": "In Settings > USB Storage > ReadySHARE Storage, enable FTP (via internet) and, if desired, restrict read and write access to admin. From a remote computer, connect with the router's DDNS name or Internet-port IP address; configure the DDNS account first if you use that option.",
        "answer_id": "Di Settings > USB Storage > ReadySHARE Storage, aktifkan FTP (via internet) dan, jika perlu, batasi akses baca dan tulis untuk admin. Dari komputer jarak jauh, hubungkan menggunakan nama DDNS atau alamat IP port Internet router; atur akun DDNS terlebih dahulu jika memilih opsi tersebut.",
    },
    "Q-098": {
        "prefixes": ["6456b41d", "65a39d84"],
        "question_en": "How do I set up the XR500 OpenVPN connection on an Android phone?",
        "question_id": "Bagaimana cara menyiapkan koneksi OpenVPN XR500 pada ponsel Android?",
        "answer_en": "Enable and configure OpenVPN on the XR500 before downloading client files. On Android, install OpenVPN Connect from Google Play, open the router's VPN Service page, make sure the service is enabled, download the Smart Phone configuration package, and import the .ovpn file into OpenVPN Connect.",
        "answer_id": "Aktifkan dan atur OpenVPN pada XR500 sebelum mengunduh berkas klien. Di Android, pasang OpenVPN Connect dari Google Play, buka halaman VPN Service router, pastikan layanan aktif, unduh paket konfigurasi Smart Phone, lalu impor berkas .ovpn ke OpenVPN Connect.",
    },
    "Q-099": {
        "prefixes": ["647b4f2b", "36995834"],
        "question_en": "What do I need to use the XR500 as a VPN client with a commercial provider?",
        "question_id": "Apa yang diperlukan untuk memakai XR500 sebagai klien VPN dengan penyedia komersial?",
        "answer_en": "The router acts as a client to an external VPN server, so you need a provider license and its login details. In Settings > Advanced Settings > VPN Client, enable the client, choose the provider, protocol, country, and city, enter the provider username and password, and select Connect.",
        "answer_id": "Router bertindak sebagai klien ke server VPN eksternal, jadi Anda memerlukan lisensi penyedia dan data masuknya. Di Settings > Advanced Settings > VPN Client, aktifkan klien, pilih penyedia, protokol, negara, dan kota, masukkan nama pengguna serta kata sandi penyedia, lalu pilih Connect.",
    },
    "Q-100": {
        "prefixes": ["1e648057", "75118c37", "64c16e90"],
        "question_en": "What is port triggering, and how do I configure it for an app on the XR500?",
        "question_id": "Apa itu port triggering, dan bagaimana cara mengaturnya untuk aplikasi pada XR500?",
        "answer_en": "Port triggering dynamically opens inbound ports after an application sends traffic, unlike fixed port forwarding. In Settings > Advanced Settings > Port Triggering, choose Add Service, enter the service name, user scope, protocols, triggering port, and inbound range, and apply it. Then clear Disable Port Triggering, set an optional timeout up to 9999 minutes, and apply again.",
        "answer_id": "Port triggering membuka port masuk secara dinamis setelah aplikasi mengirim lalu lintas, berbeda dari port forwarding yang tetap. Di Settings > Advanced Settings > Port Triggering, pilih Add Service, masukkan nama layanan, cakupan pengguna, protokol, port pemicu, dan rentang port masuk, lalu terapkan. Hapus centang Disable Port Triggering, atur waktu habis hingga 9999 menit bila perlu, lalu terapkan lagi.",
    },
}


# Additional high-confidence multi-block decisions.  Each question stays within
# one customer workflow; the second block contributes a required alternative,
# prerequisite, diagnostic, or completion step rather than unrelated context.
ADDITIONAL_MULTI_BLOCKS: dict[str, tuple[list[str], str, str, str, str]] = {
    "Q-001": (
        ["724d26e2", "833c7618"],
        "What should I know about the CM2000's rear controls and front lights when setting it up?",
        "Apa yang perlu saya ketahui tentang kontrol belakang dan lampu depan CM2000 saat menyiapkannya?",
        "The rear panel has a Reset button, Ethernet port, coaxial cable port, and DC power connector. Holding Reset for at least seven seconds returns the modem to factory settings. The front LEDs show power and connection status, so use them to confirm that the modem is powered and connected.",
        "Panel belakang memiliki tombol Reset, port Ethernet, port kabel koaksial, dan konektor daya DC. Menahan Reset minimal tujuh detik mengembalikan modem ke setelan pabrik. LED depan menunjukkan status daya dan koneksi, sehingga dapat digunakan untuk memastikan modem menyala dan terhubung.",
    ),
    "Q-002": (
        ["b9899548", "724d26e2"],
        "Where can I find the CM2000's label information and identify the rear connections I need?",
        "Di mana saya dapat menemukan informasi pada label CM2000 dan mengenali sambungan belakang yang diperlukan?",
        "The label contains the login information, MAC address, and serial number. On the rear panel, the Reset button, Ethernet port, coaxial port, and DC power connector are identified; use the Ethernet port for activation or for connecting a router afterward.",
        "Label mencantumkan informasi login, alamat MAC, dan nomor seri. Pada panel belakang terdapat tombol Reset, port Ethernet, port koaksial, dan konektor daya DC; gunakan port Ethernet untuk aktivasi atau menghubungkan router setelahnya.",
    ),
    "Q-008": (
        ["85bd9c8e", "5127b280"],
        "What should I check when I cannot log in to the CM2000 or reach the internet?",
        "Apa yang perlu saya periksa saat tidak bisa masuk ke CM2000 atau mengakses internet?",
        "Check the Ethernet connection, browser support, browser restart, lowercase admin name, Caps Lock, and the computer address range 192.168.100.2–192.168.100.254. If the Online LED is white but Internet still does not work, confirm that the cable modem MAC address is registered with your Internet provider.",
        "Periksa kabel Ethernet, dukungan browser, mulai ulang browser, nama admin dengan huruf kecil, Caps Lock, dan rentang alamat komputer 192.168.100.2–192.168.100.254. Jika LED Online putih tetapi Internet tetap tidak berfungsi, pastikan alamat MAC modem telah didaftarkan ke penyedia Internet.",
    ),
    "Q-009": (
        ["88695618", "aaab89bf"],
        "What are the CM2000's main specifications and factory defaults?",
        "Apa spesifikasi utama dan setelan bawaan pabrik CM2000?",
        "The CM2000 uses a 110–120 V, 47–60 Hz adapter that outputs 12 VDC at 1.5 A, measures 6.8 × 3.7 × 8.2 inches, weighs about 1.02 lb, and has a 2.5 Gbps Ethernet port and coaxial connector. Its default login is http://192.168.100.1 with user name admin and the password printed on the product label.",
        "CM2000 memakai adaptor 110–120 V, 47–60 Hz dengan keluaran 12 VDC/1,5 A, berukuran 6,8 × 3,7 × 8,2 inci, berbobot sekitar 1,02 lb, serta memiliki port Ethernet 2,5 Gbps dan konektor koaksial. Login bawaannya adalah http://192.168.100.1 dengan nama pengguna admin dan kata sandi pada label produk.",
    ),
    "Q-010": (
        ["37f50132", "6f0c387b"],
        "How do I install the LM1200 nano SIM in the correct slot?",
        "Bagaimana cara memasang nano SIM LM1200 pada slot yang benar?",
        "Obtain a nano SIM from the mobile provider, turn the modem off, place it horizontally with the bottom facing you, and gently insert the card into the nano-SIM slot shown on the rear-panel diagram. The same panel also contains the antenna, Gigabit Ethernet, reset, and power connections.",
        "Dapatkan nano-SIM dari penyedia seluler, matikan modem, letakkan modem mendatar dengan bagian bawah menghadap Anda, lalu masukkan kartu perlahan ke slot nano-SIM pada diagram panel belakang. Panel yang sama juga memuat sambungan antena, Ethernet Gigabit, reset, dan daya.",
    ),
    "Q-011": (
        ["36789817", "bac92cce"],
        "How should I connect a computer or router to the LM1200's LAN port?",
        "Bagaimana cara menghubungkan komputer atau router ke port LAN LM1200?",
        "Use the supplied Ethernet cable. For a computer, connect one end to the computer and the other to the modem's Gigabit Ethernet LAN port. For a router, connect the router's Ethernet or Internet port to that same modem LAN port.",
        "Gunakan kabel Ethernet yang disertakan. Untuk komputer, hubungkan satu ujung ke komputer dan ujung lainnya ke port LAN Ethernet Gigabit modem. Untuk router, hubungkan port Ethernet atau Internet router ke port LAN modem yang sama.",
    ),
    "Q-012": (
        ["fa675707", "7a457e5c"],
        "How do I choose the LM1200 network mode and set the addresses it gives my devices?",
        "Bagaimana cara memilih mode jaringan LM1200 dan mengatur alamat yang diberikannya ke perangkat?",
        "Use Router mode when the modem should provide NAT and DHCP addresses to multiple devices; its DHCP settings can then be changed at 192.168.5.1. Use Bridge mode when a connected router or switch should handle networking; Bridge mode passes the connection through and does not provide the same built-in DHCP service.",
        "Gunakan Router mode ketika modem harus menyediakan alamat NAT dan DHCP untuk beberapa perangkat; pengaturan DHCP dapat diubah di 192.168.5.1. Gunakan Bridge mode ketika router atau switch yang terhubung menangani jaringan; mode ini meneruskan koneksi dan tidak menyediakan layanan DHCP bawaan yang sama.",
    ),
    "Q-014": (
        ["441256a8", "72dd6f50"],
        "How do I manage a port-forwarding rule on the LM1200, including the service it targets?",
        "Bagaimana cara mengelola aturan port forwarding di LM1200, termasuk layanan yang dituju?",
        "Before adding a rule, find the service's port and protocol and remember that port forwarding exposes a device, so leave it disabled when it is not needed. In Settings > Advanced > Port Forwarding, add the service with those values or select the x beside an existing service to remove it.",
        "Sebelum menambahkan aturan, cari port dan protokol layanan tersebut dan ingat bahwa port forwarding membuka perangkat dari luar, sehingga sebaiknya dinonaktifkan jika tidak diperlukan. Di Settings > Advanced > Port Forwarding, tambahkan layanan dengan nilai tersebut atau pilih tanda x di samping layanan yang ada untuk menghapusnya.",
    ),
    "Q-015": (
        ["57b408ca", "eb06abbc"],
        "How do I change the LM1200 SIM PIN safely before disabling SIM security?",
        "Bagaimana cara mengubah PIN SIM LM1200 dengan aman sebelum menonaktifkan keamanan SIM?",
        "If SIM security is enabled, first personalize the PIN only after confirming the current PIN. Then disable SIM security with the correct PIN if you no longer need it. Repeated incorrect attempts can block the SIM and require a PUK from the mobile provider; after disabling security, the modem no longer asks for a PIN when connecting.",
        "Jika keamanan SIM aktif, ubah PIN hanya setelah memastikan PIN saat ini. Kemudian nonaktifkan keamanan dengan PIN yang benar jika tidak diperlukan lagi. Terlalu banyak percobaan salah dapat memblokir SIM dan memerlukan PUK dari penyedia seluler; setelah keamanan dinonaktifkan, modem tidak lagi meminta PIN saat terhubung.",
    ),
    "Q-018": (
        ["82ef2627", "ecb1143f"],
        "What should I check when the LM1200 will not connect and shows an alert?",
        "Apa yang perlu saya periksa saat LM1200 tidak terhubung dan menampilkan peringatan?",
        "Check mobile coverage, an active account, the SIM position, and the SIM PIN when security is enabled. Then read the alert table: messages such as SIM Not Installed or SIM Error point back to reseating the SIM or contacting the provider. For a wired connection, also check the Ethernet cable and DHCP address setting.",
        "Periksa jangkauan seluler, akun yang aktif, posisi SIM, dan PIN SIM jika keamanannya aktif. Baca juga tabel peringatan: pesan seperti SIM Not Installed atau SIM Error mengarah pada pemeriksaan ulang SIM atau menghubungi penyedia. Untuk koneksi kabel, periksa kabel Ethernet dan pengaturan alamat DHCP.",
    ),
    "Q-019": (
        ["6f442d4b", "683f18e6"],
        "How do I restore the LM1200 internet connection when it has not received an address?",
        "Bagaimana cara memulihkan koneksi internet LM1200 saat perangkat belum menerima alamat?",
        "If the Internet IP address is 0.0.0.0, check that an APN profile exists and power-cycle the modem. If the modem has an IP address but pages still do not load, check the monthly data limit and the computer's DNS settings, then contact the provider if needed.",
        "Jika alamat IP Internet adalah 0.0.0.0, periksa apakah profil APN tersedia lalu matikan dan nyalakan kembali modem. Jika modem sudah memiliki IP tetapi halaman tetap tidak terbuka, periksa batas data bulanan dan DNS komputer, lalu hubungi penyedia bila perlu.",
    ),
    "Q-024": (
        ["0528f0b9", "b510a03e"],
        "How can I share files from a USB drive on the R6350 over the network?",
        "Bagaimana cara membagikan berkas dari USB pada R6350 melalui jaringan?",
        "In ADVANCED > USB Storage > ReadySHARE, set the storage device and workgroup details and choose the access methods you need. If file-transfer access is useful, open the same ReadySHARE settings and enable FTP within the network, then apply the change.",
        "Di ADVANCED > USB Storage > ReadySHARE, atur detail perangkat penyimpanan dan workgroup, lalu pilih metode akses yang diperlukan. Jika akses transfer berkas dibutuhkan, buka pengaturan ReadySHARE yang sama dan aktifkan FTP di dalam jaringan, lalu terapkan.",
    ),
    "Q-025": (
        ["4a519d38", "12d6aaad"],
        "How do I edit a shared USB folder on the R6350 and keep it available on the network?",
        "Bagaimana cara mengedit folder USB yang dibagikan di R6350 dan tetap membuatnya tersedia di jaringan?",
        "In ADVANCED > USB Storage > ReadySHARE, add the network folder if it does not exist, or select the existing folder and choose Edit. Set its name, folder path, and read/write access, then click Apply so the updated folder remains available.",
        "Di ADVANCED > USB Storage > ReadySHARE, tambahkan folder jaringan jika belum ada, atau pilih folder yang ada lalu pilih Edit. Atur nama, lokasi folder, dan akses baca/tulis, kemudian klik Apply agar folder yang diperbarui tetap tersedia.",
    ),
    "Q-028": (
        ["2a3ade55", "82763a83"],
        "How can I update R6350 firmware safely, including a manual recovery if needed?",
        "Bagaimana cara memperbarui firmware R6350 dengan aman, termasuk pemulihan manual bila diperlukan?",
        "Use an Ethernet-connected computer and check for an update under ADVANCED > Administration > Firmware Update. If the automatic update fails or you need a specific version, download the correct file, unzip it if needed, and use the manual upload option while keeping the wired connection active.",
        "Gunakan komputer yang terhubung melalui Ethernet dan periksa pembaruan di ADVANCED > Administration > Firmware Update. Jika pembaruan otomatis gagal atau Anda memerlukan versi tertentu, unduh berkas yang benar, ekstrak jika perlu, lalu gunakan opsi unggah manual dengan koneksi kabel tetap aktif.",
    ),
    "Q-030": (
        ["006d8e6b", "e466a3e1"],
        "How do I set up the R6350 VPN on an Android phone and connect it to my home network?",
        "Bagaimana cara menyiapkan VPN R6350 di ponsel Android dan menghubungkannya ke jaringan rumah?",
        "Install the VPN client and configuration files on every device that will use the connection. On Android, open the router's VPN page, download the smartphone configuration, install OpenVPN Connect from Google Play, and import the configuration file into the app.",
        "Pasang klien VPN dan berkas konfigurasi pada setiap perangkat yang akan memakai koneksi. Di Android, buka halaman VPN router, unduh konfigurasi ponsel, pasang OpenVPN Connect dari Google Play, lalu impor berkas konfigurasi ke aplikasi.",
    ),
    "Q-031": (
        ["818e0932", "0a3e9e25"],
        "What should I check when the R6350 says it is connected but I cannot browse?",
        "Apa yang perlu saya periksa saat R6350 menyatakan terhubung tetapi saya tidak bisa menjelajah internet?",
        "Check whether the traffic-meter limit has blocked access, whether the computer has DNS addresses, and whether the router is its default gateway. Also inspect the Internet and LAN LEDs and reseat the Ethernet cable if they are off.",
        "Periksa apakah batas traffic meter memblokir akses, apakah komputer memiliki alamat DNS, dan apakah router menjadi gateway bawaan. Periksa juga LED Internet dan LAN serta pasang ulang kabel Ethernet jika LED mati.",
    ),
    "Q-032": (
        ["cf6a9c70", "b1147279"],
        "How should I connect the R7000 to my network by cable or Wi-Fi?",
        "Bagaimana cara menghubungkan R7000 ke jaringan melalui kabel atau Wi-Fi?",
        "For a wired connection, power the router and connect an Ethernet cable from the computer to a router LAN port. For Wi-Fi, find the SSID printed on the router label and enter the Wi-Fi password from that label.",
        "Untuk koneksi kabel, nyalakan router lalu hubungkan kabel Ethernet dari komputer ke port LAN router. Untuk Wi-Fi, cari SSID yang tercetak pada label router dan masukkan kata sandi Wi-Fi dari label tersebut.",
    ),
    "Q-036": (
        ["537310b8", "0b8cd0d8"],
        "Where can I check the R7000's internet connection and port statistics?",
        "Di mana saya dapat memeriksa koneksi internet dan statistik port R7000?",
        "Sign in at http://www.routerlogin.net, open the ADVANCED tab, and view the Internet connection status for the router IP, gateway, DHCP, and DNS values. From the same area, open Internet Port Statistics to inspect the port counters and link details.",
        "Masuk ke http://www.routerlogin.net, buka tab ADVANCED, lalu lihat status koneksi Internet untuk nilai IP router, gateway, DHCP, dan DNS. Dari area yang sama, buka Internet Port Statistics untuk memeriksa penghitung dan detail link port.",
    ),
    "Q-038": (
        ["d4980606", "1c87234f"],
        "How do I set the R7000 clock so it stays accurate across time zones?",
        "Bagaimana cara mengatur jam R7000 agar tetap akurat di berbagai zona waktu?",
        "In ADVANCED > Administration > NTP Settings, choose the correct time zone and daylight-saving option, then keep the NETGEAR NTP server or enter a preferred NTP server and apply the settings.",
        "Di ADVANCED > Administration > NTP Settings, pilih zona waktu dan opsi daylight saving yang benar, lalu gunakan server NTP NETGEAR atau masukkan server NTP pilihan dan terapkan pengaturan.",
    ),
    "Q-039": (
        ["af255485", "7e090661"],
        "How can I reach files on a USB drive connected to the R7000 while away from home?",
        "Bagaimana cara mengakses berkas pada USB yang terhubung ke R7000 saat berada di luar rumah?",
        "Enable and configure Dynamic DNS on the router if you want a stable name, then access the USB device from a remote computer using that DNS name or the router's Internet-port IP address. FTP can then be used according to the folder permissions.",
        "Aktifkan dan atur Dynamic DNS pada router jika memerlukan nama yang tetap, lalu akses perangkat USB dari komputer jarak jauh menggunakan nama DNS tersebut atau alamat IP port Internet router. FTP dapat digunakan sesuai hak akses folder.",
    ),
    "Q-040": (
        ["89cf7641", "e2441363"],
        "How do I create a ReadyCLOUD account and link the R7000 to it?",
        "Bagaimana cara membuat akun ReadyCLOUD dan menghubungkan R7000 ke akun tersebut?",
        "Visit ReadyCLOUD, choose Sign In > Create Account, and complete the MyNETGEAR account fields. Then connect a USB storage device to the R7000, open the ReadyCLOUD registration page, and register the router with that account.",
        "Kunjungi ReadyCLOUD, pilih Sign In > Create Account, lalu isi kolom akun MyNETGEAR. Setelah itu hubungkan perangkat USB ke R7000, buka halaman pendaftaran ReadyCLOUD, dan daftarkan router dengan akun tersebut.",
    ),
    "Q-041": (
        ["0cff8f5c", "aa1a9020"],
        "How do I set up the R7000 VPN on an iPhone or iPad?",
        "Bagaimana cara menyiapkan VPN R7000 di iPhone atau iPad?",
        "Install the VPN client and configuration files on each device that will use the router VPN. On iOS, download the smartphone configuration from the router, install OpenVPN Connect from the App Store, and import the files into the app.",
        "Pasang klien VPN dan berkas konfigurasi pada setiap perangkat yang akan memakai VPN router. Di iOS, unduh konfigurasi ponsel dari router, pasang OpenVPN Connect dari App Store, lalu impor berkas tersebut ke aplikasi.",
    ),
    "Q-042": (
        ["f2289449", "0840bab1"],
        "What is the safest way to restart the R7000 network while checking its cables?",
        "Bagaimana cara paling aman memulai ulang jaringan R7000 sambil memeriksa kabelnya?",
        "Turn off and unplug the modem, turn off the router, reconnect and power on the modem, wait two minutes, then power on the router and wait another two minutes. If a device stays offline, check that the Ethernet cables are secure and that the Internet and LAN LEDs respond.",
        "Matikan dan cabut modem, matikan router, sambungkan dan nyalakan modem, tunggu dua menit, lalu nyalakan router dan tunggu dua menit lagi. Jika perangkat tetap offline, periksa kekencangan kabel Ethernet serta respons LED Internet dan LAN.",
    ),
    "Q-043": (
        ["65aa662f", "33e10a89"],
        "What should I check first when the R7000 Wi-Fi is weak or missing?",
        "Apa yang perlu saya periksa lebih dulu saat Wi-Fi R7000 lemah atau tidak muncul?",
        "Check the Wi-Fi LED and WiFi On/Off button, and make sure the SSID has not been hidden. Then confirm that the device and router use matching SSID and security settings and that any wireless access list includes the device MAC address.",
        "Periksa LED Wi-Fi dan tombol WiFi On/Off, lalu pastikan SSID tidak disembunyikan. Selanjutnya pastikan perangkat dan router memakai SSID serta pengaturan keamanan yang sama dan daftar akses nirkabel menyertakan alamat MAC perangkat.",
    ),
    "Q-045": (
        ["6af6a140", "b9937b70"],
        "Which RAX120 login should I use for internet, Wi-Fi, account, or router settings?",
        "Login RAX120 mana yang digunakan untuk internet, Wi-Fi, akun, atau pengaturan router?",
        "Use the ISP login for the Internet service, the Wi-Fi key for joining the wireless network, the NETGEAR account for registration and subscriptions, and the router administrator login for settings. To use the administrator login, open http://www.routerlogin.net or the router's local address.",
        "Gunakan login ISP untuk layanan Internet, kunci Wi-Fi untuk masuk ke jaringan nirkabel, akun NETGEAR untuk registrasi dan langganan, serta login administrator router untuk pengaturan. Untuk login administrator, buka http://www.routerlogin.net atau alamat lokal router.",
    ),
    "Q-048": (
        ["ebd82415", "79da6936"],
        "How do I reserve a device's local address on the RAX120 and update that reservation later?",
        "Bagaimana cara mencadangkan alamat lokal perangkat di RAX120 dan memperbaruinya nanti?",
        "In ADVANCED > Setup > LAN Setup, add the device MAC address and a free LAN IP under Address Reservation, then apply it. When the device or network changes, select the reservation, choose Edit, update the values, and apply again; renew the DHCP lease for the change to take effect.",
        "Di ADVANCED > Setup > LAN Setup, tambahkan alamat MAC perangkat dan IP LAN yang tersedia pada Address Reservation, lalu terapkan. Jika perangkat atau jaringan berubah, pilih reservasi, pilih Edit, ubah nilainya, lalu terapkan kembali; perbarui lease DHCP agar perubahan berlaku.",
    ),
    "Q-049": (
        ["0f01b620", "88a61bbc"],
        "How can I secure RAX120 Wi-Fi without confusing its Wi-Fi and administrator passwords?",
        "Bagaimana cara mengamankan Wi-Fi RAX120 tanpa tertukar antara kata sandi Wi-Fi dan administrator?",
        "The Wi-Fi password is different from the administrator password. Keep the preset WPA2/WPA protection unless you have a reason to change it, and use the SSID and network key printed on the router label to join Wi-Fi. If you change them, save the new values securely.",
        "Kata sandi Wi-Fi berbeda dari kata sandi administrator. Pertahankan keamanan WPA2/WPA bawaan kecuali ada alasan untuk mengubahnya, dan gunakan SSID serta kunci jaringan pada label router untuk terhubung. Jika diubah, simpan nilai baru dengan aman.",
    ),
    "Q-050": (
        ["bb9735df", "aeaf90b5"],
        "What should I check before connecting a USB drive to the RAX120?",
        "Apa yang perlu saya periksa sebelum menghubungkan USB ke RAX120?",
        "Use a USB-compliant flash drive or hard drive and check the current ReadySHARE compatibility list. Connect it to the router, attach its power supply when required, and install any computer driver the device needs; special-driver devices may not work with ReadySHARE.",
        "Gunakan flash drive atau hard drive yang kompatibel dengan USB dan periksa daftar kompatibilitas ReadySHARE terbaru. Hubungkan ke router, pasang catu daya jika diperlukan, dan pasang driver komputer yang dibutuhkan; perangkat dengan driver khusus mungkin tidak bekerja dengan ReadySHARE.",
    ),
    "Q-051": (
        ["9d1e53fd", "14bc83c7"],
        "How do I create and view a shared folder on a RAX120 USB drive?",
        "Bagaimana cara membuat dan melihat folder bersama pada USB RAX120?",
        "Connect the USB drive, open ADVANCED > USB Storage > ReadySHARE, and use Create Network Folder to choose the folder, share name, and access rights. Return to the ReadySHARE view to see the folders that are available on the device.",
        "Hubungkan drive USB, buka ADVANCED > USB Storage > ReadySHARE, lalu gunakan Create Network Folder untuk memilih folder, nama share, dan hak akses. Kembali ke tampilan ReadySHARE untuk melihat folder yang tersedia pada perangkat.",
    ),
    "Q-052": (
        ["e43b60ee", "d7d2bc93"],
        "How do I change RAX120 Dynamic DNS settings for an account I already have?",
        "Bagaimana cara mengubah pengaturan Dynamic DNS RAX120 untuk akun yang sudah saya miliki?",
        "Choose your existing NETGEAR, No-IP, or DynDNS account on the Dynamic DNS page, enter its account details, and save the settings. To change the account later, return to the same page and edit the Dynamic DNS values before applying them.",
        "Pilih akun NETGEAR, No-IP, atau DynDNS yang sudah dimiliki pada halaman Dynamic DNS, masukkan detail akunnya, lalu simpan. Untuk mengubah akun, kembali ke halaman yang sama dan edit nilai Dynamic DNS sebelum menerapkan.",
    ),
    "Q-053": (
        ["cf516841", "10f082e0"],
        "How does RAX120 port forwarding send a request to a local server in a real example?",
        "Bagaimana port forwarding RAX120 meneruskan permintaan ke server lokal dalam contoh nyata?",
        "A request sent to the router's public address and port 80 can be mapped to a local web server. Give that server a stable LAN address, create a port-forwarding rule for HTTP to that address, and the router sends matching Internet requests to the local server.",
        "Permintaan ke alamat publik router dan port 80 dapat dipetakan ke server web lokal. Berikan server alamat LAN yang tetap, buat aturan port forwarding HTTP ke alamat tersebut, lalu router meneruskan permintaan Internet yang cocok ke server lokal.",
    ),
    "Q-054": (
        ["48b55cf6", "f24fac39"],
        "What should I check when a device cannot join RAX120 Wi-Fi?",
        "Apa yang perlu saya periksa saat perangkat tidak dapat bergabung ke Wi-Fi RAX120?",
        "Check whether the Wi-Fi network appears and whether the WiFi LED is on; if the SSID is hidden, select it manually. Then make the device's SSID, security mode, and case-sensitive password match the router, and add the device MAC address if access control is enabled.",
        "Periksa apakah jaringan Wi-Fi muncul dan LED WiFi menyala; jika SSID disembunyikan, pilih secara manual. Pastikan SSID, mode keamanan, dan kata sandi yang peka huruf besar-kecil pada perangkat sama dengan router, serta tambahkan alamat MAC jika kontrol akses aktif.",
    ),
    "Q-056": (
        ["c31cd99a", "f42f57b0"],
        "Where should I place and point the RAX50 antennas for the best Wi-Fi range?",
        "Di mana sebaiknya RAX50 ditempatkan dan antenanya diarahkan agar jangkauan Wi-Fi terbaik?",
        "Attach each labeled antenna to the matching post, then place the router near the center of the coverage area and within line of sight of clients. Keep it away from walls, metal, glass, and other sources of obstruction, and point the antennas as shown in the manual.",
        "Pasang setiap antena berlabel pada tiang yang sesuai, lalu letakkan router dekat pusat area jangkauan dan dalam garis pandang perangkat. Jauhkan dari dinding, logam, kaca, dan penghalang lain, serta arahkan antena sesuai gambar pada manual.",
    ),
    "Q-057": (
        ["e00425b6", "1b2c7958"],
        "How should I connect a phone or computer to RAX50, by Wi-Fi or cable?",
        "Bagaimana cara menghubungkan ponsel atau komputer ke RAX50 melalui Wi-Fi atau kabel?",
        "For Wi-Fi, open the device's Wi-Fi settings, select the SSID on the router label, and enter its network key. For a wired computer, connect an Ethernet cable from the computer to a router LAN port after confirming that the router is powered.",
        "Untuk Wi-Fi, buka pengaturan Wi-Fi perangkat, pilih SSID pada label router, lalu masukkan kunci jaringan. Untuk komputer berkabel, hubungkan kabel Ethernet dari komputer ke port LAN router setelah memastikan router mendapat daya.",
    ),
}

for _pair_id, (_prefixes, _question_en, _question_id, _answer_en, _answer_id) in ADDITIONAL_MULTI_BLOCKS.items():
    MULTI_BLOCK_DECISIONS[_pair_id] = {
        "prefixes": _prefixes,
        "question_en": _question_en,
        "question_id": _question_id,
        "answer_en": _answer_en,
        "answer_id": _answer_id,
    }


# A second pass widened a small set of lifecycle questions where three or more
# distinct packet blocks are genuinely needed.  This demonstrates the intended
# variable-size contract without padding every gold set to the same cardinality.
CARDINALITY_EXPANSIONS: dict[str, tuple[list[str], str, str, str, str]] = {
    "Q-003": (
        ["bc51c3d9", "3d9321dd", "4270da4c", "8ed480ba", "8fd1b794"],
        "What should I do with a new CM2000, from connecting a computer and activating service to connecting a router and checking speed?",
        "Apa yang perlu dilakukan pada CM2000 baru, mulai dari menghubungkan komputer dan mengaktifkan layanan hingga menghubungkan router dan memeriksa kecepatan?",
        "The CM2000 links the provider connection to a computer or router. Connect a computer to the modem, collect the provider account and modem information, and activate the service. After activation, reboot the modem, connect its Ethernet port to the router WAN/Internet port, power on the router, and connect the computer to it. Finally, run the provider's speed test and contact the provider if the result is below the subscription.",
        "CM2000 menghubungkan layanan penyedia ke komputer atau router. Hubungkan komputer ke modem, siapkan informasi akun penyedia dan modem, lalu aktifkan layanan. Setelah aktif, nyalakan ulang modem, hubungkan port Ethernet ke port WAN/Internet router, nyalakan router, dan hubungkan komputer ke router. Terakhir, jalankan uji kecepatan penyedia dan hubungi penyedia jika hasilnya di bawah paket.",
    ),
    "Q-004": (
        ["04fa120c", "4cb893dc", "0de5a970"],
        "After setup, how do I sign in to the CM2000 and change its administrator password?",
        "Setelah penyiapan, bagaimana cara masuk ke CM2000 dan mengubah kata sandi administratornya?",
        "Normal operation does not require a login, but sign in when you need to change settings. Connect to the modem, open http://192.168.100.1, and sign in as admin with the product-label password. Then select ADVANCED > Administration > Set Password, enter the old password and the new password twice, and apply a secure 6–32 character password.",
        "Penggunaan normal tidak memerlukan login, tetapi masuklah saat perlu mengubah pengaturan. Hubungkan perangkat ke modem, buka http://192.168.100.1, lalu masuk sebagai admin dengan kata sandi pada label produk. Pilih ADVANCED > Administration > Set Password, masukkan kata sandi lama dan baru dua kali, lalu terapkan kata sandi aman sepanjang 6–32 karakter.",
    ),
    "Q-008": (
        ["a88667b7", "85bd9c8e", "5127b280"],
        "What should I check when I cannot log in to the CM2000 or reach the internet?",
        "Apa yang perlu saya periksa saat tidak bisa masuk ke CM2000 atau mengakses internet?",
        "Start with the modem LEDs and confirm that power and the online connection look normal. Then check the Ethernet cable, browser support, browser restart, lowercase admin name, Caps Lock, and the computer address range 192.168.100.2–192.168.100.254. If the Online LED is white but Internet still does not work, confirm that the modem MAC address is registered with your provider.",
        "Mulai dari LED modem dan pastikan daya serta koneksi online terlihat normal. Kemudian periksa kabel Ethernet, dukungan browser, mulai ulang browser, nama admin dengan huruf kecil, Caps Lock, dan rentang alamat komputer 192.168.100.2–192.168.100.254. Jika LED Online putih tetapi Internet tetap tidak berfungsi, pastikan alamat MAC modem terdaftar pada penyedia.",
    ),
    "Q-015": (
        ["84875d88", "57b408ca", "eb06abbc", "f06eeb80"],
        "How do I manage LM1200 SIM security safely, including changing the PIN and recovering a blocked SIM?",
        "Bagaimana cara mengelola keamanan SIM LM1200 dengan aman, termasuk mengubah PIN dan memulihkan SIM yang terblokir?",
        "SIM security requires a PIN before the modem can connect. If it is enabled, personalize the PIN carefully, and disable SIM security only with the correct PIN when you no longer need it. Too many incorrect attempts can block the SIM; obtain the provider's PUK and use the unblock procedure to recover it.",
        "Keamanan SIM memerlukan PIN sebelum modem dapat terhubung. Jika aktif, ubah PIN dengan hati-hati dan nonaktifkan keamanan hanya dengan PIN yang benar bila tidak diperlukan lagi. Terlalu banyak percobaan salah dapat memblokir SIM; minta PUK dari penyedia lalu gunakan prosedur pembukaan blokir.",
    ),
    "Q-022": (
        ["aba5c3ef", "ae418564", "d4e1d4fc"],
        "How do I decide whether to change the R6350's MTU and apply a safe value?",
        "Bagaimana menentukan apakah MTU R6350 perlu diubah dan menerapkan nilai yang aman?",
        "MTU is the largest packet size a device sends. Leave the default unless the ISP or support recommends a change, because fragmentation or a wrong value can block websites and secure services. If needed, open ADVANCED > Setup > WAN Setup, enter 64–1500, and apply; 1500 is typical Ethernet, 1492 common for PPPoE, and 1436 for PPTP or VPN.",
        "MTU adalah ukuran paket terbesar yang dikirim perangkat. Biarkan nilai bawaan kecuali penyedia atau dukungan menyarankan perubahan, karena fragmentasi atau nilai salah dapat memblokir situs dan layanan aman. Jika perlu, buka ADVANCED > Setup > WAN Setup, masukkan 64–1500, lalu terapkan; 1500 umum untuk Ethernet, 1492 untuk PPPoE, dan 1436 untuk PPTP atau VPN.",
    ),
    "Q-037": (
        ["15938877", "79d677ad", "c63a4385"],
        "How can I enable remote management on the R7000 and then connect to it from outside home safely?",
        "Bagaimana cara mengaktifkan pengelolaan jarak jauh pada R7000 lalu mengaksesnya dari luar rumah dengan aman?",
        "Remote management lets you change router settings over the Internet, so first make sure you know the router address and administrator login. In ADVANCED > Advanced Setup > Remote Management, turn it on, restrict allowed external IP addresses, choose a custom port, and apply. From outside home, browse to the WAN IP followed by that port, for example http://134.177.0.123:8443.",
        "Pengelolaan jarak jauh memungkinkan perubahan pengaturan router melalui Internet, jadi pastikan alamat router dan login administrator tersedia. Di ADVANCED > Advanced Setup > Remote Management, aktifkan, batasi alamat IP eksternal yang diizinkan, pilih port khusus, lalu terapkan. Dari luar rumah, buka IP WAN diikuti port tersebut, misalnya http://134.177.0.123:8443.",
    ),
    "Q-072": (
        ["15ed12eb", "25c77477", "09ef238c"],
        "What does RAXE500 Ethernet port aggregation do, and how do I set it up with compatible equipment?",
        "Apa fungsi agregasi port Ethernet RAXE500, dan bagaimana cara menyiapkannya dengan perangkat yang kompatibel?",
        "Ethernet aggregation combines two ports for higher aggregated throughput. Make sure the switch or NAS supports 802.3ad LACP and configure it before connecting. In ADVANCED > Advanced Setup > Ethernet Port Aggregation, choose Enable (LACP) for a compatible device or Static only for a static LAG, apply the setting, and connect ports 3 and 4.",
        "Agregasi Ethernet menggabungkan dua port untuk throughput gabungan yang lebih tinggi. Pastikan switch atau NAS mendukung LACP 802.3ad dan atur perangkat tersebut sebelum menghubungkannya. Di ADVANCED > Advanced Setup > Ethernet Port Aggregation, pilih Enable (LACP) untuk perangkat kompatibel atau Static hanya untuk LAG statis, terapkan, lalu hubungkan port 3 dan 4.",
    ),
    "Q-079": (
        ["a705dc8c", "de3de3b9", "bafbe93c"],
        "How do I choose the RBK852 IPv6 connection type and enter it correctly?",
        "Bagaimana cara memilih jenis koneksi IPv6 pada RBK852 dan memasukkannya dengan benar?",
        "Open ADVANCED > Advanced > IPv6 and choose Auto Detect when you are unsure, or Auto Config when the ISP uses IPv6 without PPPoE, DHCP, or a fixed setup. If you enter an address, use valid colon-separated hexadecimal groups—no more than eight groups, no group over four characters, and no invalid run of colons—then apply the setting.",
        "Buka ADVANCED > Advanced > IPv6 dan pilih Auto Detect jika tidak yakin, atau Auto Config jika penyedia memakai IPv6 tanpa PPPoE, DHCP, atau pengaturan tetap. Jika memasukkan alamat, gunakan kelompok heksadesimal yang dipisahkan titik dua secara valid—maksimal delapan kelompok, tidak ada kelompok lebih dari empat karakter, dan tidak ada rangkaian titik dua yang salah—lalu terapkan.",
    ),
    "Q-082": (
        ["695ad5a7", "a6546993", "6bb5767a"],
        "How do I enable WAN aggregation on the RBR860, and how can I switch back to the normal 10G port?",
        "Bagaimana cara mengaktifkan WAN aggregation pada RBR860, dan bagaimana cara kembali ke port 10G biasa?",
        "The normal WAN preference uses the 10G Internet port. For aggregation, use a modem that supports LACP, configure aggregation on the modem, select WAN aggregation (10 Gbps + 1 Gbps, LACP) under ADVANCED > Setup > Internet Setup, apply it, and connect the router's 10G Internet port and port 1 to the modem. To revert, select Internet port (10 Gbps) in WAN Preference and apply.",
        "Preferensi WAN normal memakai port Internet 10G. Untuk agregasi, gunakan modem yang mendukung LACP, atur agregasi pada modem, pilih WAN aggregation (10 Gbps + 1 Gbps, LACP) di ADVANCED > Setup > Internet Setup, terapkan, lalu hubungkan port Internet 10G dan port 1 router ke modem. Untuk kembali, pilih Internet port (10 Gbps) pada WAN Preference lalu terapkan.",
    ),
    "Q-096": (
        ["84bf0b6c", "c929ed63", "1d4788df", "9c7f8f5e"],
        "How do I make XR500 USB storage available from outside home using FTP?",
        "Bagaimana cara membuat penyimpanan USB XR500 tersedia dari luar rumah menggunakan FTP?",
        "Connect a USB storage device and enable FTP access over the Internet in Settings > USB Storage > ReadySHARE Storage; limit read and write access to the accounts you intend to use. From a remote computer, connect with the router's DDNS name or Internet-port IP address, then use FTP to reach the shared files. The FTP-use page applies the configured folder permissions.",
        "Hubungkan perangkat penyimpanan USB dan aktifkan akses FTP melalui Internet di Settings > USB Storage > ReadySHARE Storage; batasi akses baca dan tulis untuk akun yang memang digunakan. Dari komputer jarak jauh, hubungkan dengan nama DDNS atau alamat IP port Internet router, lalu gunakan FTP untuk mengakses berkas bersama. Halaman penggunaan FTP menerapkan hak akses folder yang telah diatur.",
    ),
    "Q-099": (
        ["407577d5", "647b4f2b", "36995834"],
        "What do I need to use the XR500 as a VPN client with a commercial provider?",
        "Apa yang diperlukan untuk memakai XR500 sebagai klien VPN dengan penyedia komersial?",
        "In this setup the XR500 is the VPN client and the external provider is the VPN server, so devices on the router can use that encrypted connection. You need the provider's license and login details. In Settings > Advanced Settings > VPN Client, enable the client, choose the provider, protocol, country, and city, enter the credentials, and select Connect.",
        "Dalam pengaturan ini XR500 menjadi klien VPN dan penyedia eksternal menjadi server VPN, sehingga perangkat di router dapat memakai koneksi terenkripsi tersebut. Anda memerlukan lisensi dan data login penyedia. Di Settings > Advanced Settings > VPN Client, aktifkan klien, pilih penyedia, protokol, negara, dan kota, masukkan kredensial, lalu pilih Connect.",
    ),
}

for _pair_id, (_prefixes, _question_en, _question_id, _answer_en, _answer_id) in CARDINALITY_EXPANSIONS.items():
    MULTI_BLOCK_DECISIONS[_pair_id] = {
        "prefixes": _prefixes,
        "question_en": _question_en,
        "question_id": _question_id,
        "answer_en": _answer_en,
        "answer_id": _answer_id,
    }


# These packets add only a necessary prerequisite, procedure, or verification block.
SUPPORTING_EVIDENCE_ONLY: dict[str, list[str]] = {
    "Q-005": ["eb2ebf98", "89ec02e1"],
    "Q-016": ["7e1a62c7", "0ccb8b69"],
    "Q-020": ["dbca2b5a", "1190a45f"],
    "Q-023": ["8eefd80d", "31b5dd16"],
    "Q-027": ["0c80bfa0", "92de127d"],
    "Q-034": ["3a682a15", "8aecb252"],
    "Q-059": ["9a5a5bff", "f5872d3c"],
    "Q-060": ["ab459710", "d2849132"],
    "Q-061": ["f6fd63f2", "93ffa849"],
    "Q-062": ["0e8a4859", "03a4fccb"],
    "Q-064": ["5fc0a06a", "01143d51"],
    "Q-066": ["b60d283b", "d6a2438e"],
    "Q-068": ["51405423", "feb09c00"],
    "Q-069": ["fbf822a7", "eae4f314", "18a45189"],
    "Q-070": ["01cd477a", "8dba79ed"],
    "Q-074": ["8533530e", "29f43702"],
    "Q-075": ["5e5c51b3", "b2cee766"],
    "Q-076": ["0fc19ad4", "f28a4c35"],
    "Q-077": ["494eba00", "4f3d2903"],
    "Q-080": ["de3de3b9", "acfcfc10"],
    "Q-083": ["0c1c7d8a", "83b0f8da"],
    "Q-085": ["18c63118", "e8fbf22f"],
    "Q-086": ["64c7ce15", "2f0fbedc"],
    "Q-087": ["594cc248", "13759793"],
    "Q-088": ["d3189db7", "8989f72f"],
    "Q-090": ["57de6a0a", "cb248990"],
    "Q-091": ["87c05b8e", "44b909e7"],
    "Q-092": ["067a1684", "d9934c94", "3ac82c6c"],
    "Q-093": ["b76b2605", "e3bace6b"],
    "Q-094": ["0af88c60", "e8550a88"],
    "Q-095": ["2cc3db60", "7b507311", "dee55ef8"],
    "Q-097": ["1d4788df", "9c7f8f5e"],
}


# Two wording fixes keep the added evidence tied to one natural customer intent.
AUTHORED_SUPPORTING_DECISIONS: dict[str, dict[str, Any]] = {
    "Q-069": {
        "prefixes": ["fbf822a7", "eae4f314", "18a45189"],
        "question_en": "What does the RAXE500 MTU setting mean, and how can I change it safely?",
        "question_id": "Apa arti pengaturan MTU RAXE500, dan bagaimana cara mengubahnya dengan aman?",
        "answer_en": "MTU is the largest packet size sent over the connection. Keep the default unless the provider recommends a change; if needed, open the MTU settings, enter a value supported by the connection, and apply it.",
        "answer_id": "MTU adalah ukuran paket terbesar yang dikirim melalui koneksi. Biarkan nilai bawaan kecuali penyedia menyarankan perubahan; jika perlu, buka pengaturan MTU, masukkan nilai yang didukung koneksi, lalu terapkan.",
    },
    "Q-071": {
        "prefixes": ["183e963a", "33088b55"],
        "question_en": "How can I reduce nearby Wi-Fi interference on the RAXE500, and which radio does the setting affect?",
        "question_id": "Bagaimana cara mengurangi gangguan Wi-Fi di sekitar pada RAXE500, dan radio mana yang dipengaruhi pengaturan ini?",
        "answer_en": "Enable 20/40 MHz coexistence to let the 2.4 GHz radio use narrower channels when nearby networks cause interference. This can improve coexistence but may reduce peak speed; it does not change the 5 GHz radio.",
        "answer_id": "Aktifkan coexistence 20/40 MHz agar radio 2,4 GHz dapat memakai kanal yang lebih sempit ketika jaringan di sekitar menimbulkan gangguan. Ini dapat memperbaiki penggunaan bersama, tetapi kecepatan puncak mungkin berkurang; radio 5 GHz tidak terpengaruh.",
    },
    "Q-078": {
        "prefixes": ["1c16631a", "fd0ce992"],
        "question_en": "What do the RBK852 satellite light colors mean, and when should I move or sync it again?",
        "question_id": "Apa arti warna lampu satelit RBK852, dan kapan saya perlu memindahkan atau menyinkronkannya lagi?",
        "answer_en": "The satellite LED indicates connection quality: blue means a good connection, amber means move the satellite closer, and magenta means move it closer and sync it with the router again. Use the sync procedure after relocating it.",
        "answer_id": "LED satelit menunjukkan kualitas koneksi: biru berarti koneksi baik, kuning berarti satelit perlu didekatkan, dan magenta berarti dekatkan lalu sinkronkan kembali dengan router. Gunakan prosedur sinkronisasi setelah memindahkannya.",
    },
}

for _pair_id, _decision in AUTHORED_SUPPORTING_DECISIONS.items():
    MULTI_BLOCK_DECISIONS[_pair_id] = _decision


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> int:
    baseline = {
        row["question_id"]: row
        for row in read_csv(BASELINE)
        if row.get("language", "").casefold() == "en"
    }
    baseline_id = {
        row["question_pair_id"]: row
        for row in read_csv(BASELINE)
        if row.get("language", "").casefold() == "id"
    }
    packets = {row["question_pair_id"]: row for row in read_jsonl(PACKETS)}
    if len(baseline) != 100 or len(baseline_id) != 100 or len(packets) != 100:
        raise SystemExit("Expected 100 English rows, 100 Indonesian rows, and 100 packets")

    OUT.mkdir(parents=True, exist_ok=True)
    drafts: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    for pair_id in sorted(baseline, key=lambda value: int(value.split("-")[-1])):
        en = baseline[pair_id]
        id_row = baseline_id[pair_id]
        packet = packets.get(pair_id)
        if packet is None:
            raise SystemExit(f"Missing context packet: {pair_id}")
        context_hash = hashlib.sha256(packet["context_text"].encode("utf-8")).hexdigest()
        if context_hash != packet["context_text_sha256"]:
            raise SystemExit(f"Context hash mismatch: {pair_id}")
        allowed = set(packet["candidate_block_ids"])
        decision = MULTI_BLOCK_DECISIONS.get(pair_id)
        if decision is None and pair_id in SUPPORTING_EVIDENCE_ONLY:
            decision = {
                "prefixes": SUPPORTING_EVIDENCE_ONLY[pair_id],
                "question_en": en["question"],
                "question_id": id_row["question"],
                "answer_en": en["answer"],
                "answer_id": id_row["answer"],
            }
        if decision:
            by_prefix = {
                str(block["block_id"]).split("-", 1)[0]: block
                for block in packet["candidate_blocks"]
            }
            missing = [prefix for prefix in decision["prefixes"] if prefix not in by_prefix]
            if missing:
                raise SystemExit(f"Missing selected block prefix for {pair_id}: {missing}")
            selected_blocks = [by_prefix[prefix] for prefix in decision["prefixes"]]
            selected_blocks.sort(key=lambda block: (int(block.get("block_sequence", 0)), block["block_id"]))
            evidence_ids = [block["block_id"] for block in selected_blocks]
        else:
            evidence_ids = json.loads(en["evidence_block_ids"])
        if not evidence_ids or not set(evidence_ids) <= allowed:
            raise SystemExit(f"Evidence is not contained in full packet: {pair_id}")

        if decision:
            question_en = decision["question_en"]
            question_id = decision["question_id"]
            answer_en = decision["answer_en"]
            answer_id = decision["answer_id"]
        elif pair_id in OVERRIDES:
            question_en, question_id, answer_en, answer_id = OVERRIDES[pair_id]
        else:
            question_en, question_id = en["question"], id_row["question"]
            answer_en, answer_id = en["answer"], id_row["answer"]
        drafts.append(
            {
                "question_pair_id": pair_id,
                "document_id": en["document_id"],
                "filename": en["filename"],
                "product_model": en["product_model"],
                "outline_frame_id": en["outline_frame_id"],
                "section_path": en["section_path"],
                "question_family": en["question_family"],
                "question_en": question_en,
                "question_id_text": question_id,
                "reference_answer_en": answer_en,
                "reference_answer_id": answer_id,
                "evidence_block_ids": evidence_ids,
                "evidence_rationale": (
                    "The selected anchor block fully answers this single intent; all other packet blocks were reviewed as context and not unioned."
                    if len(evidence_ids) == 1
                    else "These selected blocks are jointly required for one workflow after reviewing the complete packet; unrelated candidates were excluded."
                ),
                "candidate_block_count": packet["candidate_block_count"],
                "context_text_sha256": packet["context_text_sha256"],
                "authoring_source": "codex_current_model_full_context_review",
                "review_status": "codex_full_context_reviewed_provenance_pending",
            }
        )
        review_rows.append(
            {
                "question_pair_id": pair_id,
                "document_id": en["document_id"],
                "filename": en["filename"],
                "candidate_block_count": packet["candidate_block_count"],
                "candidate_token_estimate": packet["candidate_token_estimate"],
                "selected_evidence_count": len(evidence_ids),
                "selected_evidence_block_ids": json.dumps(evidence_ids),
                "selection_decision": "anchor_sufficient" if len(evidence_ids) == 1 else "joint_blocks_required",
                "context_hash_valid": True,
                "question_revision": pair_id in OVERRIDES or decision is not None,
                "selection_basis": "joint_blocks_required" if decision else "anchor_sufficient",
            }
        )

    draft_path = OUT / "llm-question-candidates.jsonl"
    with draft_path.open("w", encoding="utf-8") as handle:
        for row in drafts:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    counts = Counter(str(len(row["evidence_block_ids"])) for row in drafts)
    bilingual_counts = {key: value * 2 for key, value in sorted(counts.items(), key=lambda item: int(item[0]))}
    summary = {
        "authoring_source": "codex_current_model_full_context_review",
        "datasource": "netgear-customer-service",
        "question_pair_count": len(drafts),
        "language_row_count": 200,
        "candidate_block_count_total": sum(row["candidate_block_count"] for row in review_rows),
        "candidate_block_count_min": min(row["candidate_block_count"] for row in review_rows),
        "candidate_block_count_max": max(row["candidate_block_count"] for row in review_rows),
        "evidence_count_distribution": dict(sorted(counts.items(), key=lambda item: int(item[0]))),
        "bilingual_row_evidence_count_distribution": bilingual_counts,
        "multi_block_pair_count": sum(1 for row in drafts if len(row["evidence_block_ids"]) > 1),
        "multi_block_language_row_count": sum(2 for row in drafts if len(row["evidence_block_ids"]) > 1),
        "fixed_evidence_count": False,
        "context_sent_to_author": "complete context_text per packet",
        "semantic_union_used": False,
        "question_revisions": sum(row["question_revision"] for row in review_rows),
        "selection_rule": "Codex reviewed every complete packet and selected the smallest evidence subset that jointly supports one natural customer intent.",
        "outputs": {
            "draft": str(draft_path),
            "review_csv": str(OUT / "codex-context-review.csv"),
            "review_md": str(OUT / "codex-context-review.md"),
        },
    }
    with (OUT / "codex-context-review.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(review_rows[0]))
        writer.writeheader()
        writer.writerows(review_rows)
    (OUT / "codex-context-review.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_lines = [
        "# Codex full-context review",
        "",
        "Every one of the 100 complete `context_text` packets was checked before selecting gold evidence.",
        "Candidate blocks remain available for authoring, but they are not unioned into gold.",
        "",
        f"- Candidate blocks: {summary['candidate_block_count_total']} total ({summary['candidate_block_count_min']}–{summary['candidate_block_count_max']} per packet).",
        f"- Pair evidence distribution: `{summary['evidence_count_distribution']}`.",
        f"- Frozen bilingual row distribution: `{summary['bilingual_row_evidence_count_distribution']}`.",
        f"- Multi-block pairs: {summary['multi_block_pair_count']} ({summary['multi_block_language_row_count']} bilingual rows).",
        f"- Compound wording revisions: {summary['question_revisions']}.",
        "- Fixed evidence count: no.",
        "- External LLM call: no; authoring source is the Codex current model in this session.",
        "",
        "A one-block decision means the anchor already contains the complete answer. A multi-block decision is retained only when each selected block contributes a necessary part of the same workflow; unrelated candidates were excluded.",
        "",
        "## Multi-block selections",
        "",
        "The full IDs and selected quotes are in `gold-evidence.jsonl`; the table below makes the variable cardinality easy to audit.",
        "",
        "| Pair | Evidence count | Selected block ID prefixes |",
        "|---|---:|---|",
    ]
    for row in review_rows:
        if int(row["selected_evidence_count"]) > 1:
            ids = json.loads(row["selected_evidence_block_ids"])
            md_lines.append(f"| `{row['question_pair_id']}` | {len(ids)} | {', '.join(f'`{block_id[:8]}`' for block_id in ids)} |")
    (OUT / "codex-context-review.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
