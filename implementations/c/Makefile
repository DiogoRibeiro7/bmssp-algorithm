CC      = gcc
CFLAGS  = -Wall -Wextra -std=c11
LDFLAGS = -lm
TARGET  = bmssp

.PHONY: all release debug test clean

all: release

release: CFLAGS += -O2
release: $(TARGET)

debug: CFLAGS += -g -fsanitize=address,undefined
debug: LDFLAGS += -fsanitize=address,undefined
debug: $(TARGET)

$(TARGET): bmssp.c
	$(CC) $(CFLAGS) $< $(LDFLAGS) -o $@

test: release
	python -m pytest tests/ -v

clean:
	rm -f $(TARGET)
