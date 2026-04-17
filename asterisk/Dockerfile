FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# archive.ubuntu.com / security.ubuntu.com часто недоступен с VPS в РФ.
# Перенаправляем на mirror.yandex.ru — полный Ubuntu-архив (включая universe).
RUN set -eux; \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i \
          -e 's|http://archive.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' \
          -e 's|http://security.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' \
          /etc/apt/sources.list; \
    fi; \
    if [ -f /etc/apt/sources.list.d/ubuntu.sources ]; then \
        sed -i \
          -e 's|http://archive.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' \
          -e 's|http://security.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' \
          /etc/apt/sources.list.d/ubuntu.sources; \
    fi; \
    apt-get update && apt-get install -y --no-install-recommends \
        asterisk \
        asterisk-config \
        asterisk-modules \
        asterisk-core-sounds-en \
        gettext-base \
        uuid-runtime \
        procps \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY etc/ /etc/asterisk-template/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5060/udp 10000-10100/udp

CMD ["/entrypoint.sh"]
