CC      = gcc
CFLAGS  = -Wall -Wextra -std=c11
LDFLAGS = -lm
TARGET  = bmssp
BENCH   = benchmark

.PHONY: all release debug test bench clean

all: release

release: CFLAGS += -O2
release: $(TARGET)

debug: CFLAGS += -g -fsanitize=address,undefined
debug: LDFLAGS += -fsanitize=address,undefined
debug: $(TARGET)

$(TARGET): bmssp.c
	$(CC) $(CFLAGS) $< $(LDFLAGS) -o $@

$(BENCH): benchmark.c bmssp.c
	$(CC) $(CFLAGS) -O2 benchmark.c $(LDFLAGS) -o $@

bench: $(BENCH)
	./$(BENCH) > benchmark_results.csv

test: release
	python -m pytest tests/ -v

clean:
	rm -f $(TARGET) $(BENCH) benchmark_results.csv
