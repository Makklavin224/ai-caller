FROM debian:12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        asterisk \
        asterisk-core-sounds-en \
        gettext-base \
        uuid-runtime \
        procps \
    && rm -rf /var/lib/apt/lists/*

COPY etc/ /etc/asterisk-template/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5060/udp 10000-10100/udp

CMD ["/entrypoint.sh"]
