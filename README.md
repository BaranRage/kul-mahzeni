# Kül Mahzeni

Python ve pygame-ce ile yapılmış, kasvetli 8-bit bir roguelike. Mahzeni keşfet, bekçileri yen ve Prenses Öykü'yü kurtar.

## İndir ve çalıştır

İndirdiğin ZIP dosyasını bir klasöre çıkar. Python 3.10 veya daha yeni bir sürüm gerekir. Bu paket kaynak kod içerir; bağımsız bir Windows EXE dosyası değildir. İlk kurulumda bağımlılıkları indirmek için internet gerekir.

### Windows

Python'u kurduktan sonra oyun klasöründe terminal aç:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

Sonraki açılışlarda yalnızca son komutu çalıştır.

### Linux / macOS

Oyun klasöründe terminal aç:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

Sonraki açılışlarda yalnızca son komutu çalıştır.

`uv` yüklüyse alternatif olarak tek komutla başlatabilirsin:

```sh
uv run --no-project --with pygame-ce==2.5.8 python main.py
```

## Kontroller

| Tuş | İşlev |
| --- | --- |
| WASD / ok tuşları | Hareket ve menü seçimi |
| J / X | Saldır, seç, konuş |
| K / L / I | Yetenekler; I: ulti |
| Boşluk | Atılma |
| Esc | Duraklatma menüsü |
| M | Sesi aç / kapat |
| F11 | Tam ekran |
| R | Ölünce silah seçimine dön |

Oyun kayıtları ve ayarlar kullanıcı klasöründeki `.config/kul-mahzeni/` dizinine yazılır. Paylaşım paketi kişisel oyun kayıtları içermez.

Linux'ta Python 3.14 ve pygame-ce 2.5.8 ile kısa açılış testi yapılmıştır. Windows ve macOS üzerinde doğrulanmamıştır.
