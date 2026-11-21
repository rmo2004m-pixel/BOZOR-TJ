# BoZor TJ

## 1. Запуск сервера
    ADMIN_KEY='длинный-секретный-ключ' PORT=8000 python3 server.py
Поставьте перед ним Caddy/Nginx с HTTPS (Let's Encrypt). Для Caddy: `your-domain.tj { reverse_proxy localhost:8000 }`
Автозапуск: systemd-сервис. Копия базы: ежедневно копируйте `shop.db` (cron).

## 2. APK (самый быстрый путь)
1. Откройте https://www.pwabuilder.com, вставьте https://ВАШ-ДОМЕН, выберите Android, скачайте APK/AAB.

## 3. APK через Capacitor (свой контроль)
Нужны Node.js и Android Studio.
1. В `capacitor.config.json` замените YOUR-DOMAIN.tj на ваш домен (и в www/index.html).
2. `npm init -y && npm i @capacitor/core @capacitor/cli @capacitor/android`
3. `npx cap add android && npx cap sync`
4. `npx cap open android` → Build > Build APK(s) (для Google Play: Build > Generate Signed Bundle).

## Что исправлено
Отмена заказа с возвратом остатков; ограничение запросов (заказы, вход админа, отслеживание); защитные заголовки; удаление товара; новые заказы сверху; лимиты длины полей; иконки PWA.
Оплата по-прежнему проверяется вручную (номер 555444551).
