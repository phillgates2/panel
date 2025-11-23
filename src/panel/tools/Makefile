CC=gcc
CFLAGS=-O2 -Wall -Wextra -std=gnu11
PREFIX=/opt/panel/bin

all: panel-wrapper

panel-wrapper: panel_wrapper.c
	$(CC) $(CFLAGS) -o panel-wrapper panel_wrapper.c

install: panel-wrapper
	mkdir -p $(PREFIX)
	cp panel-wrapper $(PREFIX)/panel-wrapper
	chown root:root $(PREFIX)/panel-wrapper
	chmod 750 $(PREFIX)/panel-wrapper

clean:
	rm -f panel-wrapper
