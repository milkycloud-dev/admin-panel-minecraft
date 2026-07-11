<div align="center">
  <img src="icon.png" alt="Minecraft Admin Panel" width="128"/>
  
  # Minecraft Admin Panel
  **Профессиональное решение для администрирования серверов Minecraft**
  
  [![Release](https://img.shields.io/github/v/release/milkycloud-dev/admin-panel-minecraft?style=for-the-badge&color=0078D4)](https://github.com/milkycloud-dev/admin-panel-minecraft/releases)
  [![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-brightgreen?style=for-the-badge)](https://github.com/milkycloud-dev/admin-panel-minecraft/releases)
  [![UI](https://img.shields.io/badge/UI-Flet_Framework-blue?style=for-the-badge)](https://flet.dev)

  *[Read in English](README.md)*
</div>

---

**Minecraft Admin Panel** — это десктопное приложение, разработанное для оптимизации и автоматизации процессов управления серверами Minecraft. Архитектура приложения построена на базе фреймворка **Flet** (Flutter), что обеспечивает кроссплатформенность, высокую скорость отклика и современный пользовательский интерфейс.

## Ключевые возможности

- **Автоматизация деплоя модификаций:** Прямая интеграция по протоколу SFTP обеспечивает синхронизацию файлов (удаление устаревших и загрузку новых версий модов) в автоматическом режиме.
- **Интегрированная консоль RCON:** Безопасное дистанционное управление сервером через встроенный терминал с поддержкой истории команд и подсветкой синтаксиса системных логов.
- **Модуль резервного копирования:** Локальное архивирование данных средствами 7-Zip с поддержкой динамических исключений директорий (например, `world` или `logs`) для минимизации нагрузки на накопитель.
- **Оптимизированная сборка:** Бинарные файлы для сред Windows и Linux проходят стадию экстремального сжатия алгоритмом UPX, обеспечивая высокую портативность и минимальный размер исполняемого файла.
- **Система доставки обновлений:** Интегрированный модуль автоматической верификации версий обеспечивает бесшовное обновление приложения напрямую из репозитория GitHub.

## Зашифрованный manifest лаунчера (V2.1)

С V2.1 панель собирает ОДИН зашифрованный `/cloud/manifest.json` (AES-256-GCM + Ed25519)
вместо открытого `client/index.json`. Кнопка «Собрать Manifest» пересобирает список модов
на сервере, затем шифрует и подписывает файл ЛОКАЛЬНО (приватный ключ не покидает машину).

Ключи: **Настройки → Ключи manifest (V2.1)** — пути к двум локальным base64-файлам
(`manifest_sym.key`, `ed25519_private.key`). Значения ключей в репозиторий не кладутся.

Локальная проверка сборки без загрузки:

```bash
python manifest_builder.py --index path/to/index.json --metadata cloud_manifest_metadata.json --out /tmp/manifest.json --sym-key-file /path/manifest_sym.key --priv-key-file /path/ed25519_private.key
```

## Зеркало GitHub → fallback-сервер

GitHub — источник правды; сервер — запасной канал. При старте панель проверяет, кнопка
«Синхр. GH→сервер» дозаливаёт:

- raw: `settings.json`, `news.json`, `cloud/manifest.json`
  (мосты `manifest.json` / `new/` на сервере со ссылками на `/cloud/exe-mirror`);
- релизные exe/AppImage → `/cloud/exe-mirror`.

Игровые архивы/моды/Java живут в `/cloud/` на сервере и с GitHub не зеркалятся.

## Развертывание и настройка

Приложение поставляется в виде скомпилированного исполняемого файла, не требующего установки. Все конфигурационные данные сохраняются локально в файле `admin_settings.json`, который генерируется автоматически при первом запуске.

### Требования к инфраструктуре
- Операционная система: Windows 10/11 (64-bit) или современные дистрибутивы Linux.
- Наличие установленного архиватора 7-Zip (рекомендуется добавить в системную переменную `PATH`) для корректной работы модуля резервного копирования.
- Доступность SSH/SFTP на целевом сервере для синхронизации файлов.

### Инструкция по сборке из исходного кода

Для самостоятельной компиляции исполняемого файла необходима установленная среда Python 3.11+.

1. Клонируйте репозиторий:
```bash
git clone https://github.com/milkycloud-dev/admin-panel-minecraft.git
cd admin-panel-minecraft
```

2. Установите необходимые зависимости:
```bash
pip install -r requirements.txt
```

3. Выполните сборку с использованием `flet pack`. Для оптимизации размера рекомендуется исключить неиспользуемые модули:
```bash
flet pack main.py --name AdminPanel-Windows --icon "icon.png" --add-data "icon.png;." -y --exclude-module numpy --exclude-module pandas --exclude-module PIL --exclude-module tkinter
```
После завершения процесса компиляции готовый бинарный файл будет доступен в директории `dist`.

## Технологический стек
- **Ядро:** Python 3.11+
- **Интерфейс:** Flet Framework (Flutter)
- **Сетевое взаимодействие:** Paramiko (SFTP/SSH)
- **Компиляция:** PyInstaller & UPX
- **Шифрование:** Blake3 (верификация целостности обновлений)

---
<div align="center">
  <i>Решение для эффективного управления инфраструктурой Minecraft.</i>
</div>
